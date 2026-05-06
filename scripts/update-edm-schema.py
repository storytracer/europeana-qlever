# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml", "rdflib", "pyyaml"]
# ///
"""Generate LinkML EDM base schema from the official Europeana metis-schema.

Parses the XSD files (property-per-class definitions with cardinality) and the
OWL ontology (descriptions, domain/range, property types) from the europeana/
metis-schema GitHub repository, and produces a LinkML YAML schema at
``src/europeana_qlever/schema/edm.yaml``.

External ontology files (DC, DCTERMS, SKOS, FOAF, etc.) are fetched to provide
descriptions for non-EDM properties. All ontology files are cached in the
``ontologies/`` directory. Use ``--no-external-descriptions`` to skip
incorporating external descriptions into the schema.

The script is idempotent — re-run it whenever Europeana publishes a new EDM
version to regenerate the schema.

Usage:
    uv run scripts/generate-edm-schema.py
    uv run scripts/generate-edm-schema.py --no-external-descriptions
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import textwrap
from collections import defaultdict
from pathlib import Path

import yaml
from lxml import etree
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DC, DCTERMS, OWL, RDF, RDFS, SKOS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_URL = "https://github.com/europeana/metis-schema.git"
XSD_SUBDIR = "src/main/resources/schema_xsds"
OWL_FILE = "src/main/resources/rdf_examples/edm.owl"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_PATH = PROJECT_ROOT / "src" / "europeana_qlever" / "schema" / "edm.yaml"

EDM = Namespace("http://www.europeana.eu/schemas/edm/")

# XSD namespace
XS = "http://www.w3.org/2001/XMLSchema"

# Namespace URI → prefix mapping (must match edm_parquet.yaml prefixes)
PREFIXES: dict[str, str] = {
    "linkml": "https://w3id.org/linkml/",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ore": "http://www.openarchives.org/ore/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "rdaGr2": "http://rdvocab.info/ElementsGr2/",
    "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
    "wgs84_pos": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "svcs": "http://rdfs.org/sioc/services#",
    "doap": "http://usefulinc.com/ns/doap#",
    "cc": "http://creativecommons.org/ns#",
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "dqv": "http://www.w3.org/ns/dqv#",
    "schema": "https://schema.org/",
}

# Reverse: URI → prefix
_URI_TO_PREFIX = {v: k for k, v in PREFIXES.items() if k != "linkml"}

# XSD type name → LinkML range mapping
_XSD_TYPE_TO_RANGE: dict[str, str] = {
    "rdf:ResourceType": "uri",
    "rdf:LiteralType": "string",
    "rdf:ResourceOrLiteralType": "string",
    "rdf:LongType": "integer",
    "rdf:IntegerType": "integer",
    "rdf:NonNegativeIntegerType": "integer",
    "rdf:NonNegativeIntegerWithoutDataTypeType": "integer",
    "rdf:DoubleType": "float",
    "rdf:HexBinaryType": "string",
    "rdf:StringType": "string",
    "string": "string",
    "boolean": "boolean",
    "edm:EdmType": "EdmType",
    "edm:CountryCodes": "string",
    "edm:LanguageCodes": "string",
    "edm:UGCType": "string",
    "edm:ColorSpaceType": "string",
    "ebucore:OrientationType": "string",
}

# Class definitions: maps XSD type name → (LinkML class name, class_uri CURIE)
CLASS_DEFS: dict[str, tuple[str, str]] = {
    # EDM-EXTERNAL-MAIN.xsd / CONTEXTS.xsd
    "edm:ProvidedCHOType": ("ProvidedCHO", "edm:ProvidedCHO"),
    "edm:AgentType": ("Agent", "edm:Agent"),
    "edm:PlaceType": ("Place", "edm:Place"),
    "edm:TimeSpanType": ("TimeSpan", "edm:TimeSpan"),
    "edm:WebResourceType": ("WebResource", "edm:WebResource"),
    "edm:PersistentIdentifierType": ("PersistentIdentifier", "edm:PersistentIdentifier"),
    "edm:PersistentIdentifierSchemeType": ("PersistentIdentifierScheme", "edm:PersistentIdentifierScheme"),
}

# Inline classes (defined as elements, not complexType names)
ELEMENT_CLASS_DEFS: dict[str, tuple[str, str]] = {
    "ore:Aggregation": ("Aggregation", "ore:Aggregation"),
    "ore:Proxy": ("Proxy", "ore:Proxy"),
    "skos:Concept": ("Concept", "skos:Concept"),
    "svcs:Service": ("Service", "svcs:Service"),
    "cc:License": ("License", "cc:License"),
}

# Ontology cache directory (project root)
ONTOLOGIES_DIR = PROJECT_ROOT / "ontologies"
METIS_SCHEMA_DIR = ONTOLOGIES_DIR / "metis-schema"

# External ontology sources: prefix → (URL, rdflib format, filename)
EXTERNAL_ONTOLOGIES: dict[str, tuple[str, str, str]] = {
    "dc": ("http://purl.org/dc/elements/1.1/", "xml", "dc.rdf"),
    "dcterms": ("http://purl.org/dc/terms/", "xml", "dcterms.rdf"),
    "skos": ("https://www.w3.org/2009/08/skos-reference/skos.rdf", "xml", "skos.rdf"),
    "foaf": ("http://xmlns.com/foaf/0.1/index.rdf", "xml", "foaf.rdf"),
    "wgs84_pos": ("http://www.w3.org/2003/01/geo/wgs84_pos", "xml", "wgs84_pos.rdf"),
    "ore": ("http://www.openarchives.org/ore/terms/", "xml", "ore.rdf"),
    # ebucore: ontology not available as downloadable RDF — use hardcoded fallbacks
    "cc": ("https://creativecommons.org/schema.rdf", "xml", "cc.rdf"),
    "odrl": ("https://www.w3.org/ns/odrl/2/ODRL22.ttl", "turtle", "odrl.ttl"),
    "dqv": ("https://www.w3.org/ns/dqv.ttl", "turtle", "dqv.ttl"),
    "doap": (
        "https://raw.githubusercontent.com/ewilderj/doap/master/schema/doap.rdf",
        "xml",
        "doap.rdf",
    ),
    "svcs": ("http://rdfs.org/sioc/services", "xml", "svcs.rdf"),
}

# Hardcoded fallback descriptions for namespaces without fetchable ontologies
FALLBACK_DESCRIPTIONS: dict[str, str] = {
    # rdaGr2 — namespace retired, no RDF endpoint
    "http://rdvocab.info/ElementsGr2/biographicalInformation":
        "An account of the life of the person.",
    "http://rdvocab.info/ElementsGr2/dateOfBirth":
        "The date of birth of the person.",
    "http://rdvocab.info/ElementsGr2/dateOfDeath":
        "The date of death of the person.",
    "http://rdvocab.info/ElementsGr2/dateOfEstablishment":
        "The date of establishment of the corporate body.",
    "http://rdvocab.info/ElementsGr2/dateOfTermination":
        "The date of termination of the corporate body.",
    "http://rdvocab.info/ElementsGr2/gender":
        "The gender with which a person identifies.",
    "http://rdvocab.info/ElementsGr2/placeOfBirth":
        "The town, city, province, state, and/or country in which a person was born.",
    "http://rdvocab.info/ElementsGr2/placeOfDeath":
        "The town, city, province, state, and/or country in which a person died.",
    "http://rdvocab.info/ElementsGr2/professionOrOccupation":
        "A profession or occupation in which the person works or has worked.",
    # ebucore — ontology not available as downloadable RDF
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#audioChannelNumber":
        "The total number of audio channels contained in the media resource.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#bitRate":
        "The bit rate of the media resource, expressed in bits per second.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#duration":
        "The duration of the media resource, typically expressed as a time value.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#fileByteSize":
        "The file size of the media resource in bytes.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#frameRate":
        "The frame rate of the video resource, expressed in frames per second.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#hasMimeType":
        "The MIME type of the media resource (e.g. image/jpeg, audio/mp3, video/mp4).",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#height":
        "The height of the media resource in pixels.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#orientation":
        "The orientation of the image or video resource (e.g. landscape, portrait).",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#sampleRate":
        "The audio sample rate of the media resource in Hz.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#sampleSize":
        "The audio sample size (bit depth) of the media resource in bits.",
    "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#width":
        "The width of the media resource in pixels.",
    # cc
    "http://creativecommons.org/ns#deprecatedOn":
        "The date on which the license was deprecated.",
    # edm properties not in the OWL ontology (newer additions)
    "http://www.europeana.eu/schemas/edm/intermediateProvider":
        "The name or identifier of an intermediate organization that acts between the data "
        "provider and Europeana in the aggregation chain.",
    "http://www.europeana.eu/schemas/edm/pid":
        "A persistent identifier (PID) assigned to the resource, such as a DOI, Handle, or ARK.",
    "http://www.europeana.eu/schemas/edm/equivalentPID":
        "A persistent identifier that is considered equivalent to another PID for the same resource.",
    "http://www.europeana.eu/schemas/edm/hasURL":
        "The URL associated with a persistent identifier, providing access to the identified resource.",
    "http://www.europeana.eu/schemas/edm/replacesPID":
        "A persistent identifier that this PID replaces, indicating a superseded identifier.",
    "http://www.europeana.eu/schemas/edm/codecName":
        "The name of the codec used to encode the media resource (e.g. H.264, VP9, FLAC).",
    "http://www.europeana.eu/schemas/edm/componentColor":
        "A dominant colour component detected in the digital representation of the object, "
        "expressed as a hex RGB value.",
    "http://www.europeana.eu/schemas/edm/hasColorSpace":
        "The colour space of the digital representation (e.g. sRGB, Adobe RGB, CMYK).",
    "http://www.europeana.eu/schemas/edm/intendedUsage":
        "The intended usage context for a web resource, such as thumbnail or full resolution.",
    "http://www.europeana.eu/schemas/edm/pointCount":
        "The number of points in a 3D point cloud representation of the object.",
    "http://www.europeana.eu/schemas/edm/polygonCount":
        "The number of polygons in a 3D mesh representation of the object.",
    "http://www.europeana.eu/schemas/edm/spatialResolution":
        "The spatial resolution of the digital representation, typically in DPI or PPI.",
    "http://www.europeana.eu/schemas/edm/vertexCount":
        "The number of vertices in a 3D mesh representation of the object.",
    # owl — well-known properties
    "http://www.w3.org/2002/07/owl#sameAs":
        "The property that determines that two given individuals are equal. "
        "This is used to link an entity to its equivalent in another dataset or authority file.",
    # rdf
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
        "The subject is an instance of a class. States that the resource is a member of the given class.",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#value":
        "Idiomatic property used for structured values. The principal value of a structured resource.",
    # rdfs
    "http://www.w3.org/2000/01/rdf-schema#seeAlso":
        "A resource that provides further information about the subject resource.",
    # schema.org — avoid parsing 3MB TTL for one property
    "https://schema.org/digitalSourceType":
        "The type of digital source used to create the digital object. "
        "Indicates whether the content is digitised from an analogue original, born-digital, "
        "or created through other digital processes.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _curie(uri_or_ref: str) -> str | None:
    """Convert a full namespace URI element ref to a CURIE like 'dc:title'."""
    s = str(uri_or_ref)
    for uri, pfx in sorted(_URI_TO_PREFIX.items(), key=lambda x: -len(x[0])):
        if s.startswith(uri):
            return f"{pfx}:{s[len(uri):]}"
    return None


def _to_slot_name(curie: str) -> str:
    """Convert a CURIE like 'dc:title' to a snake_case slot name."""
    pfx, local = curie.split(":", 1)
    # Convert camelCase to snake_case
    result = []
    for i, ch in enumerate(local):
        if ch.isupper() and i > 0 and not local[i - 1].isupper():
            result.append("_")
        result.append(ch.lower())
    name = "".join(result)
    # Prefix with namespace to avoid collisions
    return f"{pfx}_{name}"


def _element_ref_to_curie(ref: str) -> str | None:
    """Parse an XSD element ref like 'dc:title' into a CURIE."""
    if ":" in ref:
        return ref
    return None


# ---------------------------------------------------------------------------
# XSD parsing
# ---------------------------------------------------------------------------


def _parse_xsd_element(
    el: etree._Element, ns_map: dict[str, str]
) -> dict | None:
    """Parse a single <element> inside a complexType sequence.

    Returns a dict with keys: ref (CURIE), min_occurs, max_occurs, xsd_type.
    """
    ref = el.get("ref")
    name = el.get("name")
    if ref is None and name is None:
        return None

    curie = ref if ref else None
    if curie is None and name:
        # Local element (e.g. <element name="pid" type="rdf:LiteralType"/>)
        # Determine namespace from context
        target_ns = el.getroottree().getroot().get("targetNamespace", "")
        prefix = _URI_TO_PREFIX.get(target_ns, "")
        curie = f"{prefix}:{name}" if prefix else name

    min_occ = el.get("minOccurs", "0")
    max_occ = el.get("maxOccurs", "1")
    xsd_type = el.get("type")

    return {
        "ref": curie,
        "min_occurs": int(min_occ) if min_occ != "unbounded" else 0,
        "max_occurs": max_occ,
        "xsd_type": xsd_type,
    }


def _collect_elements(
    node: etree._Element, parent_max: str = "1"
) -> list[dict]:
    """Recursively collect all <element> defs from sequences/choices.

    *parent_max* propagates the maxOccurs of a parent sequence/choice
    down to child elements, so that ``<sequence maxOccurs="unbounded">
    <choice><element ref="dc:title"/></choice></sequence>`` correctly
    marks dc:title as multivalued.
    """
    results = []
    for child in node:
        if not isinstance(child.tag, str):
            continue  # Skip comments, PIs
        tag = etree.QName(child.tag).localname
        if tag == "element":
            parsed = _parse_xsd_element(child, {})
            if parsed:
                # Inherit parent maxOccurs if the element itself says "1"
                if parsed["max_occurs"] == "1" and parent_max == "unbounded":
                    parsed["max_occurs"] = "unbounded"
                results.append(parsed)
        elif tag in ("sequence", "choice", "extension", "complexContent", "all"):
            # Propagate maxOccurs from this container
            container_max = child.get("maxOccurs", parent_max)
            results.extend(_collect_elements(child, container_max))
    return results


def _parse_complex_type(ct: etree._Element) -> list[dict]:
    """Parse a complexType element and return its property elements."""
    return _collect_elements(ct)


def _clean_xsd_doc(text: str) -> str:
    """Clean up XSD documentation text: collapse whitespace, strip type suffixes."""
    import re
    # Collapse whitespace
    text = " ".join(text.split())
    # Strip trailing "Type: String" etc. (not useful in LinkML context)
    text = re.sub(r"\s*Type:\s*\w+\s*$", "", text)
    return text.strip()


def parse_xsd_docs(xsd_dir: Path) -> dict[str, dict]:
    """Extract documentation from XSD element annotations.

    Scans all XSD files for global ``<element>`` declarations that contain
    ``<annotation><documentation>`` and returns
    ``{full_uri: {"description": ...}}``.
    """
    _SKIP = {"EDM-INTERNAL-MAIN.xsd", "EDM-INTERNAL.xsd", "ENRICHMENT.xsd"}
    info: dict[str, dict] = {}

    for xsd_path in sorted(xsd_dir.glob("*.xsd")):
        if xsd_path.name in _SKIP:
            continue
        try:
            tree = etree.parse(str(xsd_path))
        except etree.XMLSyntaxError:
            continue

        root = tree.getroot()
        target_ns = root.get("targetNamespace", "")

        for el in root.findall(f"{{{XS}}}element"):
            name = el.get("name")
            if not name:
                continue

            # Extract documentation
            ann = el.find(f"{{{XS}}}annotation")
            if ann is None:
                # Check inside inline complexType
                ct = el.find(f"{{{XS}}}complexType")
                if ct is not None:
                    ann = ct.find(f"{{{XS}}}annotation")
            if ann is None:
                continue
            doc = ann.find(f"{{{XS}}}documentation")
            if doc is None:
                continue
            # Use tostring(method="text") to capture full content including
            # child elements (e.g. inline XML examples like <title>...</title>)
            raw = etree.tostring(doc, method="text", encoding="unicode")
            if not raw or not raw.strip():
                continue

            desc = _clean_xsd_doc(raw)
            if desc:
                full_uri = f"{target_ns}{name}"
                info[full_uri] = {"description": desc}

    return info


def _resolve_element_type(
    ref: str, xsd_files: dict[str, etree._Element]
) -> str | None:
    """Look up the XSD type of a global element declaration."""
    prefix, local = ref.split(":", 1) if ":" in ref else ("", ref)
    ns_uri = PREFIXES.get(prefix, "")

    for _fname, root in xsd_files.items():
        target_ns = root.get("targetNamespace", "")
        if target_ns == ns_uri or (not ns_uri and not target_ns):
            # Find <element name="local" type="..."/>
            for el in root.findall(f"{{{XS}}}element"):
                if el.get("name") == local:
                    return el.get("type")
    return None


def _find_complex_type(
    qualified_name: str, xsd_files: dict[str, etree._Element]
) -> etree._Element | None:
    """Find a named complexType across all XSD files.

    *qualified_name* can be 'edm:EuropeanaType', 'rdf:AboutType', etc.
    """
    prefix, local = qualified_name.split(":", 1) if ":" in qualified_name else ("", qualified_name)
    ns_uri = PREFIXES.get(prefix, "")

    for _fname, root in xsd_files.items():
        target_ns = root.get("targetNamespace", "")
        if target_ns == ns_uri:
            for ct in root.findall(f"{{{XS}}}complexType"):
                if ct.get("name") == local:
                    return ct
    return None


def _resolve_base_chain(
    ct: etree._Element, xsd_files: dict[str, etree._Element]
) -> list[dict]:
    """Recursively follow XSD extension base= to collect inherited properties.

    Returns all properties from the base type chain (parent first, child last).
    """
    all_props = []

    # Find <complexContent><extension base="...">
    for cc in ct.findall(f"{{{XS}}}complexContent"):
        for ext in cc.findall(f"{{{XS}}}extension"):
            base = ext.get("base")
            if base and base != "rdf:AboutType":
                # Recurse into the base type
                base_ct = _find_complex_type(base, xsd_files)
                if base_ct is not None:
                    all_props.extend(_resolve_base_chain(base_ct, xsd_files))

    # Then collect this type's own elements
    all_props.extend(_collect_elements(ct))

    return all_props


def parse_all_xsds(xsd_dir: Path) -> dict[str, list[dict]]:
    """Parse all XSD files and return class_name → [property_defs].

    Returns a dict mapping LinkML class names to lists of property dicts.
    Follows XSD extension base= chains to include inherited properties.
    """
    # Skip internal-only XSD files — we want the external (public) schema
    _SKIP = {"EDM-INTERNAL-MAIN.xsd", "EDM-INTERNAL.xsd", "ENRICHMENT.xsd"}

    xsd_files: dict[str, etree._Element] = {}
    for xsd_path in sorted(xsd_dir.glob("*.xsd")):
        if xsd_path.name in _SKIP:
            continue
        try:
            tree = etree.parse(str(xsd_path))
            xsd_files[xsd_path.name] = tree.getroot()
        except etree.XMLSyntaxError:
            continue

    classes: dict[str, list[dict]] = {}

    # 1. Named complexTypes (AgentType, PlaceType, etc.)
    for _fname, root in xsd_files.items():
        for ct in root.findall(f"{{{XS}}}complexType"):
            type_name = ct.get("name")
            if not type_name:
                continue

            target_ns = root.get("targetNamespace", "")
            prefix = _URI_TO_PREFIX.get(target_ns, "")
            qualified = f"{prefix}:{type_name}" if prefix else type_name

            if qualified in CLASS_DEFS:
                cls_name, _cls_uri = CLASS_DEFS[qualified]
                # Follow the full extension chain
                props = _resolve_base_chain(ct, xsd_files)
                for prop in props:
                    if prop["xsd_type"] is None and prop["ref"]:
                        prop["xsd_type"] = _resolve_element_type(
                            prop["ref"], xsd_files
                        )
                classes[cls_name] = props

    # 2. Element-defined classes (ore:Aggregation, skos:Concept, etc.)
    for _fname, root in xsd_files.items():
        target_ns = root.get("targetNamespace", "")
        prefix = _URI_TO_PREFIX.get(target_ns, "")
        for el in root.findall(f"{{{XS}}}element"):
            el_name = el.get("name")
            qualified = f"{prefix}:{el_name}" if prefix else el_name
            if qualified in ELEMENT_CLASS_DEFS:
                cls_name, _cls_uri = ELEMENT_CLASS_DEFS[qualified]
                # Check for inline complexType first
                ct = el.find(f"{{{XS}}}complexType")
                if ct is None:
                    # Check for type= attribute pointing to a named complexType
                    type_ref = el.get("type")
                    if type_ref:
                        ct = _find_complex_type(type_ref, xsd_files)
                if ct is not None:
                    props = _resolve_base_chain(ct, xsd_files)
                    for prop in props:
                        if prop["xsd_type"] is None and prop["ref"]:
                            prop["xsd_type"] = _resolve_element_type(
                                prop["ref"], xsd_files
                            )
                    classes[cls_name] = props

    return classes


# ---------------------------------------------------------------------------
# OWL parsing
# ---------------------------------------------------------------------------


def parse_owl(owl_path: Path) -> dict[str, dict]:
    """Parse the EDM OWL file for labels and descriptions.

    Returns {property_uri: {"label": ..., "description": ...}}.
    """
    g = Graph()
    g.parse(str(owl_path), format="xml")

    info: dict[str, dict] = {}

    # Collect class info
    for s in g.subjects(RDF.type, OWL.Class):
        uri = str(s)
        label = str(g.value(s, RDFS.label, default=""))
        defn = str(g.value(s, SKOS.definition, default=""))
        if label or defn:
            info[uri] = {"label": label, "description": defn.strip()}

    # Collect property info (owl:ObjectProperty, owl:DatatypeProperty, rdf:Property)
    for prop_type in (OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property):
        for s in g.subjects(RDF.type, prop_type):
            uri = str(s)
            label = str(g.value(s, RDFS.label, default=""))
            defn = str(g.value(s, SKOS.definition, default=""))
            domain = g.value(s, RDFS.domain)
            range_ = g.value(s, RDFS.range)
            info[uri] = {
                "label": label,
                "description": defn.strip(),
                "domain": str(domain) if domain else None,
                "range": str(range_) if range_ else None,
                "is_object_property": prop_type == OWL.ObjectProperty,
            }

    return info


# ---------------------------------------------------------------------------
# External ontology descriptions
# ---------------------------------------------------------------------------


def _best_description(g: Graph, subject, predicates: list) -> str:
    """Get the best description for a subject, preferring English."""
    for pred in predicates:
        values = list(g.objects(subject, pred))
        if not values:
            continue
        # Prefer English
        for v in values:
            if hasattr(v, "language") and v.language == "en":
                return str(v).strip()
        # Fall back to untagged
        for v in values:
            if hasattr(v, "language") and v.language is None:
                return str(v).strip()
        # Fall back to first
        return str(values[0]).strip()
    return ""


def _fetch_ontology(url: str, dest: Path, accept: str = "application/rdf+xml") -> bool:
    """Download an ontology file via curl if not already cached."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        subprocess.run(
            ["curl", "-sL", "-o", str(dest), "-H", f"Accept: {accept}", url],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return dest.exists() and dest.stat().st_size > 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"    WARNING: Failed to fetch {url}: {e}")
        return False


def fetch_external_ontologies(ontologies_dir: Path) -> dict[str, dict]:
    """Fetch external ontology files and extract property descriptions.

    Downloads RDF/OWL/TTL files for non-EDM namespaces and parses
    rdfs:comment, skos:definition, and dcterms:description.

    Returns {property_uri: {"description": ...}}.
    """
    ontologies_dir.mkdir(parents=True, exist_ok=True)
    info: dict[str, dict] = {}

    # Apply hardcoded fallbacks first (lowest priority)
    for uri, desc in FALLBACK_DESCRIPTIONS.items():
        info[uri] = {"description": desc}

    # Description predicates in priority order
    desc_predicates = [RDFS.comment, SKOS.definition, DCTERMS.description, DC.description]

    for prefix, (url, fmt, filename) in EXTERNAL_ONTOLOGIES.items():
        cache_path = ontologies_dir / filename
        accept = "text/turtle" if fmt == "turtle" else "application/rdf+xml"
        print(f"  Fetching {prefix} ontology from {url}...")
        if not _fetch_ontology(url, cache_path, accept):
            continue

        try:
            g = Graph()
            g.parse(str(cache_path), format=fmt)

            ns_uri = PREFIXES.get(prefix, "")
            count = 0
            for s in g.subjects():
                uri = str(s)
                if not uri.startswith(ns_uri):
                    continue
                desc = _best_description(g, s, desc_predicates)
                if desc:
                    # Only fill gaps — don't overwrite existing descriptions
                    if uri not in info or not info[uri].get("description"):
                        info[uri] = {"description": desc}
                        count += 1
            print(f"    Found {count} descriptions for {prefix}")
        except Exception as e:
            print(f"    WARNING: Could not parse {filename}: {e}")

    return info


# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------


def _prop_to_slot(
    prop: dict, owl_info: dict[str, dict]
) -> tuple[str, dict] | None:
    """Convert a parsed XSD property to a LinkML slot definition."""
    ref = prop["ref"]
    if not ref or ":" not in ref:
        return None

    curie = ref
    slot_name = _to_slot_name(curie)

    # Determine range from XSD type
    xsd_type = prop.get("xsd_type") or ""
    linkml_range = _XSD_TYPE_TO_RANGE.get(xsd_type, "string")

    # Cardinality
    max_occ = prop["max_occurs"]
    multivalued = max_occ == "unbounded" or (
        isinstance(max_occ, str) and max_occ.isdigit() and int(max_occ) > 1
    )
    required = prop["min_occurs"] >= 1

    slot_def: dict = {
        "slot_uri": curie,
        "range": linkml_range,
    }
    if multivalued:
        slot_def["multivalued"] = True
    if required:
        slot_def["required"] = True

    # Add description from OWL
    prefix, local = curie.split(":", 1)
    ns_uri = PREFIXES.get(prefix, "")
    full_uri = f"{ns_uri}{local}"
    if full_uri in owl_info:
        desc = owl_info[full_uri].get("description", "")
        if desc:
            slot_def["description"] = desc

    return slot_name, slot_def


def generate_schema(
    xsd_classes: dict[str, list[dict]], owl_info: dict[str, dict]
) -> dict:
    """Build the LinkML schema dict."""
    # Merge CLASS_DEFS and ELEMENT_CLASS_DEFS for URI lookup
    all_class_uris = {}
    for qualified, (cls_name, cls_uri) in CLASS_DEFS.items():
        all_class_uris[cls_name] = cls_uri
    for qualified, (cls_name, cls_uri) in ELEMENT_CLASS_DEFS.items():
        all_class_uris[cls_name] = cls_uri

    classes: dict[str, dict] = {}

    # Desired class order
    class_order = [
        "ProvidedCHO", "Proxy", "Aggregation", "WebResource",
        "Agent", "Place", "Concept", "TimeSpan",
        "Service", "License",
        "PersistentIdentifier", "PersistentIdentifierScheme",
    ]

    for cls_name in class_order:
        if cls_name not in xsd_classes:
            continue

        cls_uri = all_class_uris.get(cls_name, "")
        props = xsd_classes[cls_name]

        # Get class description from OWL
        ns_uri = ""
        if ":" in cls_uri:
            pfx, local = cls_uri.split(":", 1)
            ns_uri = PREFIXES.get(pfx, "")
        full_cls_uri = f"{ns_uri}{cls_uri.split(':', 1)[1]}" if ":" in cls_uri else ""
        cls_desc = ""
        if full_cls_uri in owl_info:
            cls_desc = owl_info[full_cls_uri].get("description", "")
        cls_def: dict = {"class_uri": cls_uri}
        if cls_desc:
            cls_def["description"] = cls_desc

        # Build attributes
        attrs: dict[str, dict] = {}
        seen_refs: set[str] = set()
        for prop in props:
            if prop["ref"] in seen_refs:
                continue
            seen_refs.add(prop["ref"])

            result = _prop_to_slot(prop, owl_info)
            if result:
                slot_name, slot_def = result
                attrs[slot_name] = slot_def

        if attrs:
            cls_def["attributes"] = attrs

        classes[cls_name] = cls_def

    # Build enums
    enums = {
        "EdmType": {
            "description": "The Europeana material type classification",
            "permissible_values": {
                v: {} for v in ["IMAGE", "TEXT", "SOUND", "VIDEO", "3D"]
            },
        },
    }

    schema = {
        "id": "https://europeana.eu/schemas/edm",
        "name": "edm",
        "title": "Europeana Data Model",
        "description": (
            "Complete EDM schema generated from the official Europeana "
            "metis-schema repository (XSD + OWL). Covers all EDM classes, "
            "properties, cardinality constraints, and enum types. "
            "Source: https://github.com/europeana/metis-schema"
        ),
        "version": "5.2.4",
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
        "prefixes": {k: v for k, v in PREFIXES.items() if k != "linkml"},
        "default_range": "string",
        "imports": ["linkml:types"],
        "enums": enums,
        "classes": classes,
    }

    return schema


# ---------------------------------------------------------------------------
# YAML output
# ---------------------------------------------------------------------------


class _LiteralStr(str):
    """Tag for YAML literal block scalars."""


def _literal_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    if len(data) > 100:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def _write_yaml(schema: dict, path: Path) -> None:
    """Write schema dict to YAML with a readable header comment."""
    yaml.add_representer(str, _literal_representer)

    header = textwrap.dedent("""\
        # =============================================================================
        # Europeana Data Model (EDM) — LinkML Base Schema
        # =============================================================================
        # GENERATED FILE — do not edit manually.
        # Regenerate with: uv run scripts/generate-edm-schema.py
        #
        # Source: https://github.com/europeana/metis-schema
        # EDM version: 5.2.4
        # =============================================================================

    """)

    content = yaml.dump(
        schema,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )

    path.write_text(header + content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _ensure_metis_schema() -> Path:
    """Clone metis-schema to /tmp and copy XSD/OWL files to ontologies/.

    Returns the metis-schema directory under ontologies/.
    """
    import sys

    dest = METIS_SCHEMA_DIR
    xsd_dest = dest / XSD_SUBDIR
    owl_dest = dest / OWL_FILE

    # If already copied, reuse
    if xsd_dest.is_dir() and owl_dest.is_file():
        print(f"Using cached metis-schema at {dest}")
        return dest

    # Clone to /tmp first
    cached = Path("/tmp/metis-schema")
    if not (cached.is_dir() and (cached / XSD_SUBDIR).is_dir()):
        print(f"Cloning {REPO_URL} to /tmp...")
        if cached.exists():
            shutil.rmtree(cached)
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(cached)],
            check=True,
            capture_output=True,
        )

    src_xsd = cached / XSD_SUBDIR
    src_owl = cached / OWL_FILE
    if not src_xsd.is_dir():
        print(f"ERROR: XSD directory not found at {src_xsd}", file=sys.stderr)
        sys.exit(1)
    if not src_owl.is_file():
        print(f"ERROR: OWL file not found at {src_owl}", file=sys.stderr)
        sys.exit(1)

    # Copy needed files to ontologies/metis-schema/
    print(f"Copying metis-schema files to {dest}...")
    dest.mkdir(parents=True, exist_ok=True)
    if xsd_dest.exists():
        shutil.rmtree(xsd_dest)
    xsd_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(src_xsd), str(xsd_dest))
    owl_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src_owl), str(owl_dest))

    return dest


def main() -> None:
    import sys

    parser = argparse.ArgumentParser(
        description="Generate LinkML EDM base schema from metis-schema.",
    )
    parser.add_argument(
        "--no-external-descriptions",
        action="store_true",
        help="Skip incorporating external ontology descriptions into the schema. "
        "Ontologies are still downloaded to ontologies/.",
    )
    args = parser.parse_args()

    # Ensure metis-schema files are in ontologies/
    metis_dir = _ensure_metis_schema()
    xsd_dir = metis_dir / XSD_SUBDIR
    owl_path = metis_dir / OWL_FILE

    # Parse sources
    print("Parsing XSD files...")
    xsd_classes = parse_all_xsds(xsd_dir)
    print(f"  Found {len(xsd_classes)} classes: {', '.join(xsd_classes)}")
    for cls_name, props in xsd_classes.items():
        print(f"    {cls_name}: {len(props)} properties")

    print("Parsing XSD documentation annotations...")
    xsd_docs = parse_xsd_docs(xsd_dir)
    print(f"  Found {len(xsd_docs)} element descriptions from XSD annotations")

    print("Parsing EDM OWL ontology...")
    owl_info = parse_owl(owl_path)
    print(f"  Found {len(owl_info)} class/property descriptions")

    # Fetch external ontologies (always downloaded, descriptions optional)
    external_dir = ONTOLOGIES_DIR / "external"
    print("Fetching external ontologies...")
    external_info = fetch_external_ontologies(external_dir)
    print(f"  Found {len(external_info)} external descriptions total")

    # Build merged description index.
    # Priority (highest first): EDM OWL > XSD docs > external ontologies > hardcoded fallbacks
    # EDM OWL descriptions are curated and specific to EDM semantics.
    # XSD docs come from metis-schema and are EDM-contextualised with examples.
    # External ontologies provide generic definitions from upstream vocabularies.
    # Hardcoded fallbacks cover namespaces without fetchable sources.
    if not args.no_external_descriptions:
        # Merge in priority order: XSD docs first, then external fills remaining gaps.
        # EDM OWL (already in owl_info) is never overwritten.
        for uri, data in xsd_docs.items():
            desc = data.get("description", "")
            if not desc:
                continue
            if uri not in owl_info:
                owl_info[uri] = data
            elif not owl_info[uri].get("description"):
                owl_info[uri]["description"] = desc

        for uri, data in external_info.items():
            if uri not in owl_info:
                owl_info[uri] = data
            elif not owl_info[uri].get("description"):
                owl_info[uri]["description"] = data.get("description", "")

        print("  Merged XSD + external descriptions into schema")
    else:
        print("  Skipping external descriptions (--no-external-descriptions)")

    # Generate schema
    print("Generating LinkML schema...")
    schema = generate_schema(xsd_classes, owl_info)

    # Count total attributes and description coverage
    total_attrs = 0
    with_desc = 0
    for c in schema.get("classes", {}).values():
        for a in c.get("attributes", {}).values():
            total_attrs += 1
            if a.get("description"):
                with_desc += 1
    print(f"  {len(schema['classes'])} classes, {total_attrs} attributes total")
    print(f"  {with_desc}/{total_attrs} attributes have descriptions ({100 * with_desc // total_attrs}%)")

    # Write output
    _write_yaml(schema, OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
