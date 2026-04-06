# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml", "rdflib", "pyyaml"]
# ///
"""Generate LinkML EDM base schema from the official Europeana metis-schema.

Parses the XSD files (property-per-class definitions with cardinality) and the
OWL ontology (descriptions, domain/range, property types) from the europeana/
metis-schema GitHub repository, and produces a LinkML YAML schema at
``src/europeana_qlever/schema/edm.yaml``.

The script is idempotent — re-run it whenever Europeana publishes a new EDM
version to regenerate the schema.

Usage:
    uv run scripts/generate-edm-schema.py
"""

from __future__ import annotations

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
            # Truncate very long descriptions
            if len(desc) > 300:
                desc = desc[:297] + "..."
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
            if cls_desc and len(cls_desc) > 300:
                cls_desc = cls_desc[:297] + "..."

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


def main() -> None:
    import sys

    # Clone metis-schema
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / "metis-schema"
        # Check if already cloned in /tmp
        cached = Path("/tmp/metis-schema")
        if cached.is_dir() and (cached / XSD_SUBDIR).is_dir():
            repo_dir = cached
            print(f"Using cached metis-schema at {repo_dir}")
        else:
            print(f"Cloning {REPO_URL}...")
            subprocess.run(
                ["git", "clone", "--depth", "1", REPO_URL, str(repo_dir)],
                check=True,
                capture_output=True,
            )

        xsd_dir = repo_dir / XSD_SUBDIR
        owl_path = repo_dir / OWL_FILE

        if not xsd_dir.is_dir():
            print(f"ERROR: XSD directory not found at {xsd_dir}", file=sys.stderr)
            sys.exit(1)
        if not owl_path.is_file():
            print(f"ERROR: OWL file not found at {owl_path}", file=sys.stderr)
            sys.exit(1)

        # Parse sources
        print("Parsing XSD files...")
        xsd_classes = parse_all_xsds(xsd_dir)
        print(f"  Found {len(xsd_classes)} classes: {', '.join(xsd_classes)}")
        for cls_name, props in xsd_classes.items():
            print(f"    {cls_name}: {len(props)} properties")

        print("Parsing OWL ontology...")
        owl_info = parse_owl(owl_path)
        print(f"  Found {len(owl_info)} class/property descriptions")

        # Generate schema
        print("Generating LinkML schema...")
        schema = generate_schema(xsd_classes, owl_info)

        # Count total attributes
        total_attrs = sum(
            len(c.get("attributes", {}))
            for c in schema.get("classes", {}).values()
        )
        print(f"  {len(schema['classes'])} classes, {total_attrs} attributes total")

        # Write output
        _write_yaml(schema, OUTPUT_PATH)
        print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
