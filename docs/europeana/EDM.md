# Europeana Knowledge Base

Europeana aggregates metadata and digital objects from over 4,000 cultural heritage institutions (CHIs) across Europe — libraries, museums, archives, galleries, and audiovisual collections. This document is a synthesized reference covering the Europeana Data Model (EDM), mapping and publishing guidelines, APIs, data processing, persistent identifiers, IIIF support, copyright, and operational tooling.

---

## 1. Terminology

| Term | Definition |
|---|---|
| **Cultural Heritage Object (CHO)** | The original physical or born-digital object that is the focus of a metadata description |
| **ProvidedCHO** | The CHO for which a data provider submits a description to Europeana. There is an exact match between ProvidedCHOs and searchable items |
| **Web Resource** | A digital representation of the CHO (e.g., a scan, photograph, audio recording) |
| **Aggregation** | A set of related resources about one CHO from one provider — groups the ProvidedCHO, WebResources, and contextual entities |
| **Record** | Shorthand for a complete metadata description (ProvidedCHO + WebResource(s) + Aggregation + contextual classes) |
| **Class** | A group of things sharing common properties |
| **Property** | An element expressing a relationship between two resources |
| **Literal** | A string value, optionally with an ISO 639 language tag via `xml:lang` |
| **Reference (Ref)** | A URI reference to another resource |
| **Data Provider** | The organisation that provides data about CHOs to an aggregator |
| **Provider** | The organisation providing data directly to Europeana (typically an aggregator) |
| **Aggregator** | An organisation that collects data from multiple CHIs and submits it to Europeana |

---

## 2. Europeana Data Model (EDM)

EDM is a linked-data framework based on RDF that enables interoperability across cultural heritage domains. It separates the description of the original object from its digital representations and the aggregation context.

### 2.1 Datatypes

| Type | Description |
|---|---|
| Literal | String value with optional language tag (IETF BCP 47) |
| Literal (Datatype) | Value conforming to a specific datatype (e.g., `xsd:date`) |
| Reference | URI reference to another resource |
| Reference (Class) | URI reference to a resource of a specific class |

### 2.2 Core Classes

**edm:ProvidedCHO** — Represents the cultural heritage object itself. Properties describe the original object (creator, date, subject), not the digital representation. Exception: `edm:type` refers to the digital media type.

**edm:WebResource** — A digital representation of the CHO, available via URL. Multiple WebResources per CHO are possible, linked through the Aggregation. Properties describe the digital resource (format, resolution, rights).

**ore:Aggregation** — Groups all resources from a single provider about one CHO. Carries the data supply chain (dataProvider → intermediateProvider → provider) and the rights statement.

**edm:EuropeanaAggregation** (Internal only) — Created at ingestion time. Contains Europeana-generated information: landing page, preview, country, language, dataset name, quality annotations.

**ore:Proxy** (Internal only) — Allows distinct provider-specific and Europeana-specific descriptions to coexist for the same CHO. The provider proxy carries the original metadata; the Europeana proxy (`edm:europeanaProxy=true`) carries enrichments, normalized dates, and quality annotations.

### 2.3 Contextual Classes

| Class | Purpose | Key Properties |
|---|---|---|
| **edm:Agent** | People or groups who performed intentional actions | `skos:prefLabel`, `skos:altLabel`, `edm:begin`, `edm:end`, `rdaGr2:dateOfBirth/Death`, `rdaGr2:placeOfBirth/Death`, `rdaGr2:professionOrOccupation`, `rdaGr2:gender`, `owl:sameAs` |
| **edm:Place** | Spatial locations | `skos:prefLabel`, `wgs84_pos:lat`, `wgs84_pos:long`, `wgs84_pos:alt`, `dcterms:isPartOf`, `owl:sameAs` |
| **edm:TimeSpan** | Periods of time with beginning, end, and duration | `skos:prefLabel`, `edm:begin`, `edm:end`, `skos:notation` (EDTF), `owl:sameAs` |
| **skos:Concept** | Units of thought from controlled vocabularies | `skos:prefLabel`, `skos:altLabel`, `skos:broader`, `skos:narrower`, `skos:exactMatch`, `skos:inScheme`, `owl:sameAs` |
| **foaf:Organization** | Providing organisations (added during ingestion from Zoho CRM + Wikidata) | `skos:prefLabel`, `edm:acronym`, `edm:country`, `edm:language`, `edm:europeanaRole`, `edm:heritageDomain`, `foaf:logo`, `owl:sameAs` |
| **cc:License** | Copyright license for a web resource | `odrl:inheritFrom` (mandatory), `cc:deprecatedOn` |

### 2.4 Auxiliary Classes

| Class | Scope | Purpose |
|---|---|---|
| **as:Delete** | Internal | Record deletion events |
| **dqv:QualityAnnotation** | Internal | Data quality per Europeana Publishing Framework (content/metadata tiers) |
| **svcs:Service** | External/Internal | Declares a service consuming a resource (used for IIIF, oEmbed) |
| **edm:FullTextResource** | Internal | Machine-readable full-text content (e.g., OCR output), subclass of `edm:WebResource` |
| **edm:Event** | External/Internal | Change of states in cultural/social/physical systems (under construction) |
| **edm:PersistentIdentifier** | External/Internal | Metadata record about a PID |
| **edm:PersistentIdentifierScheme** | External/Internal | PID scheme definition (subclass of `skos:ConceptScheme`) |
| **edm:Aggregator** | Internal | Organisation in aggregator role (subclass of `foaf:Organization`) |

### 2.5 Namespaces

| Prefix | URI |
|---|---|
| `dc` | `http://purl.org/dc/elements/1.1/` |
| `dcterms` | `http://purl.org/dc/terms/` |
| `edm` | `http://www.europeana.eu/schemas/edm/` |
| `ore` | `http://www.openarchives.org/ore/terms/` |
| `skos` | `http://www.w3.org/2004/02/skos/core#` |
| `foaf` | `http://xmlns.com/foaf/0.1/` |
| `owl` | `http://www.w3.org/2002/07/owl#` |
| `rdf` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| `rdfs` | `https://www.w3.org/TR/rdf-schema/#` |
| `rdaGr2` | `http://rdvocab.info/ElementsGr2/` |
| `ebucore` | `https://www.ebu.ch/metadata/ontologies/ebucore/ebucore#` |
| `dqv` | `http://www.w3.org/ns/dqv#` |
| `odrl` | `http://www.w3.org/ns/odrl/2/` |
| `svcs` | `http://rdfs.org/sioc/services#` |
| `doap` | `http://usefulinc.com/ns/doap#` |
| `dcat` | `http://www.w3.org/ns/dcat#` |
| `vcard` | `http://www.w3.org/2006/vcard/ns#` |
| `wgs84` | `http://www.w3.org/2003/01/geo/wgs84_pos#` |
| `cc` | `http://creativecommons.org/ns#` |

### 2.6 EDM Controlled Vocabularies

- **Europeana material type** (`edm:type`): TEXT, IMAGE, VIDEO, SOUND, 3D (upper-case, case-sensitive)
- **Metadata tiers**: metadataTierA, metadataTierB, metadataTierC (URIs under `http://www.europeana.eu/schemas/epf/`)
- **Content tiers**: contentTier1 through contentTier4
- **3D intended usage** (hierarchical): Knowledge (Research, Education), Infotainment (Tourism, Gaming, Exhibition), Creativity (Design, Art), Curation (Maintenance, Restoration, Documentation) — URIs under `http://data.europeana.eu/vocabulary/usageArea/`
- **3D model type**: 3DMesh, 3DPointCloud, BIM, parametricModel — URIs under `http://data.europeana.eu/vocabulary/modelType/`
- **Relation to physical reality** (IPTC): digitalCapture, dataDrivenMedia, digitalCreation — URIs under `https://cv.iptc.org/newscodes/digitalsourcetype/`
- **Heritage domains** (16 values): Cross domain, Documentary, Bibliographic, Audiovisual, Film, Audio, Imagery, Photographic, Museum, Fashion, Musical, Archeological, Architectural, Natural, Scientific, Intangible heritage

### 2.7 EDM Profiles

EDM profiles are refinements and extensions for specific domains:

**Technical Metadata Profile** — Properties on `edm:WebResource` for media characterization:

| Property | Range | Used For |
|---|---|---|
| `ebucore:hasMimeType` | IANA MIME type | All |
| `ebucore:fileByteSize` | `xsd:long` | All |
| `ebucore:width` / `ebucore:height` | `xsd:integer` | Image, Video |
| `ebucore:duration` | milliseconds | Sound, Video |
| `ebucore:bitRate` | `xsd:nonNegativeInteger` | Sound, Video |
| `ebucore:sampleRate` / `ebucore:sampleSize` | `xsd:integer` | Sound |
| `ebucore:frameRate` | `xsd:double` | Video |
| `ebucore:audioChannelNumber` | `xsd:nonNegativeInteger` | Sound |
| `ebucore:orientation` | string | Image |
| `edm:spatialResolution` | DPI | Text (PDFs) |
| `edm:hasColorSpace` | "grayscale" or "sRGB" | Image |
| `edm:componentColor` | hex (CSS3 palette, max 6) | Image |
| `edm:codecName` | string | Video |

**3D Content Profile** — Additional `edm:WebResource` properties: `edm:intendedUsage`, `schema:digitalSourceType`, `edm:vertexCount`, `edm:polygonCount`, `edm:pointCount`, `dc:type` (from 3D model type vocabulary).

**IIIF to EDM Profile** — Uses `svcs:Service` class with `dcterms:conformsTo` = `http://iiif.io/api/image` and `doap:implements` for compliance level. WebResources linked via `svcs:has_service`; manifests via `dcterms:isReferencedBy`.

**Persistent Identifiers Profile** — `edm:pid` property on ProvidedCHO/WebResource/Agent/Place/Concept/TimeSpan/Proxy. `edm:PersistentIdentifier` class carries canonical form (`rdf:value`), scheme (`skos:inScheme`), URL form (`edm:hasURL`), equivalents (`edm:equivalentPID`), and superseded PIDs (`edm:replacesPID`).

**Organisation Profile** — Extends `foaf:Organization` with `edm:Aggregator` subclass and `vcard:Address`. Uses Europeana Entity Collection URIs (`http://data.europeana.eu/organisation/{ID}`).

**Sound Profile** — Adaptations for audio/audio-related objects. Emerged from Europeana Sounds project (2014).

**Events Profile** (under construction) — `edm:Event` class with `edm:happenedAt` (Place), `edm:occurredAt` (TimeSpan), `edm:wasPresentAt` (reverse).

### 2.8 SPARQL Query Model

Descriptive metadata is **not** stored directly on the `edm:ProvidedCHO`. A query like `?item dc:title ?t` returns zero results. Instead, metadata flows through **proxies** and **aggregations**:

```
edm:ProvidedCHO ←ore:proxyFor── ore:Proxy (provider)     → dc:*, dcterms:* (original metadata)
edm:ProvidedCHO ←ore:proxyFor── ore:Proxy (Europeana)    → edm:type, edm:year, enriched entity URIs
edm:ProvidedCHO ←edm:aggregatedCHO── ore:Aggregation     → edm:rights, edm:dataProvider, URLs
edm:ProvidedCHO ←edm:aggregatedCHO── EuropeanaAggregation → edm:country, edm:completeness, edm:datasetName
ore:Aggregation  ──edm:hasView──→ edm:WebResource         → ebucore:hasMimeType, width, height
```

#### 2.8.1 Core SPARQL Patterns

**Provider Proxy** — original descriptive metadata (dc:title, dc:creator, dc:subject as literals):
```sparql
?proxy ore:proxyFor ?item .
FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" . }
```

**Europeana Proxy** — normalised fields (edm:type, edm:year) and enriched entity URIs:
```sparql
?eProxy ore:proxyFor ?item .
?eProxy edm:europeanaProxy "true" .
```

**Aggregation** — rights statement, data supply chain, digital object URLs:
```sparql
?agg edm:aggregatedCHO ?item .
```

**Europeana Aggregation** — country, completeness, dataset name (internal):
```sparql
?eAgg edm:aggregatedCHO ?item .
?eAgg a edm:EuropeanaAggregation .
```

**Web Resource** — technical metadata (MIME type, dimensions, file size):
```sparql
?agg edm:aggregatedCHO ?item .
?agg edm:hasView ?wr .
```

#### 2.8.2 Provider Proxy vs Europeana Proxy

Each item has **two** proxies. The Europeana enrichment pipeline copies certain provider values and adds entity URIs.

| Aspect | Provider Proxy | Europeana Proxy |
|---|---|---|
| **Filter** | `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }` | `?eProxy edm:europeanaProxy "true"` |
| **dc:title, dc:description** | Original literals (language-tagged) | — |
| **dc:creator, dc:contributor** | Original literals (strings) | Enriched entity URIs (`edm:Agent`) |
| **dc:subject** | Original literals (strings) | Enriched entity URIs (`skos:Concept`) |
| **dcterms:spatial** | Original literals (strings) | Enriched entity URIs (`edm:Place`) |
| **edm:type** | — | `"IMAGE"`, `"TEXT"`, `"SOUND"`, `"VIDEO"`, `"3D"` |
| **edm:year** | — | Normalised year strings (e.g., `"1765"`) |
| **dc:date, dcterms:created, etc.** | Original date strings | — |

**Key rule:** When using an entity URI (e.g., from `search_entity`), query the **Europeana proxy**. When searching text in titles or descriptions, query the **provider proxy**.

#### 2.8.3 Aggregation vs EuropeanaAggregation

These are different objects with different properties. Do NOT confuse them:

| Property | ore:Aggregation | edm:EuropeanaAggregation |
|---|---|---|
| `edm:rights` | **Authoritative rights URI** | Has a copy, but incomplete — never use |
| `edm:dataProvider` | Data provider name (literal) | Has a copy |
| `edm:provider` | Provider name (literal) | Has a copy |
| `edm:isShownBy` / `edm:isShownAt` | Digital object URLs | — |
| `edm:country` | — | **Country (literal)** |
| `edm:completeness` | — | **Completeness score** |
| `edm:datasetName` | — | **Dataset identifier** |
| `edm:landingPage` | — | Europeana portal URL |
| `edm:preview` | — | Thumbnail URL |

**Always use `ore:Aggregation` for `edm:rights` queries.**

#### 2.8.4 Common Query Examples

**Count all items:**
```sparql
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {
  ?item a edm:ProvidedCHO .
}
```

**Count items by type** (uses Europeana proxy):
```sparql
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT ?type (COUNT(DISTINCT ?item) AS ?count) WHERE {
  ?eProxy ore:proxyFor ?item .
  ?eProxy edm:europeanaProxy "true" .
  ?eProxy edm:type ?type .
} GROUP BY ?type ORDER BY DESC(?count)
```

**Text search on title** (uses provider proxy):
```sparql
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT ?item ?title WHERE {
  ?proxy ore:proxyFor ?item .
  FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" . }
  ?proxy dc:title ?title .
  FILTER(CONTAINS(LCASE(STR(?title)), "mona lisa"))
} LIMIT 100
```

**Filter by country** (uses EuropeanaAggregation):
```sparql
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {
  ?eAgg edm:aggregatedCHO ?item .
  ?eAgg a edm:EuropeanaAggregation .
  ?eAgg edm:country "Netherlands" .
}
```

**Find items by entity URI** (uses Europeana proxy):
```sparql
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {
  ?eProxy ore:proxyFor ?item .
  ?eProxy edm:europeanaProxy "true" .
  ?eProxy dc:creator <http://data.europeana.eu/agent/base/59832> .
}
```

**Filter by year range** (edm:year is a string — cast to integer):
```sparql
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {
  ?eProxy ore:proxyFor ?item .
  ?eProxy edm:europeanaProxy "true" .
  ?eProxy edm:year ?year .
  FILTER(xsd:integer(?year) >= 1800 && xsd:integer(?year) <= 1900)
}
```

**Filter by open reuse level** (uses Aggregation):
```sparql
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
SELECT (COUNT(DISTINCT ?item) AS ?count) WHERE {
  ?agg edm:aggregatedCHO ?item .
  ?agg edm:rights ?rights .
  FILTER(
    STRSTARTS(STR(?rights), "http://creativecommons.org/publicdomain/") ||
    STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/") ||
    STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by-sa/")
  )
}
```

#### 2.8.5 Performance Notes

- **Always `COUNT(DISTINCT ?item)`** — items have multiple proxies and entity links, so bare `COUNT` over-counts.
- **Never use nested `BIND`/`IF` for classification** over the full 66M-item dataset (e.g., classifying reuse levels). It will time out. Run **separate `COUNT` queries** per category instead.
- **Use `LIMIT`** for exploratory queries. Without it, a `SELECT *` can return billions of rows.
- **Use `STR(?uri)`** when comparing URI values with `STRSTARTS` or `CONTAINS`.

#### 2.8.6 Schema Cross-Reference

The LinkML schema at `src/europeana_qlever/schema/edm.yaml` contains machine-readable definitions for all 12 EDM classes and 242 attributes, generated from the Europeana `metis-schema` XSD and OWL ontology sources. It is the authoritative source for property ranges, cardinality, and descriptions used by the query generator.

---

## 3. EDM Mapping Guidelines

### 3.1 General Mapping Rules

1. Provide as many properties as possible; mandatory ones are required
2. Provide properties in documented order
3. If the same contextual entity applies to multiple ProvidedCHOs, repeat it for each
4. Values are either reference or literal; most properties allow either — provide only one form to avoid duplication
5. Properties linking to contextual resources via URIs are recommended for enrichment
6. Use `xml:lang` wherever appropriate; not allowed on `rdf:resource` attributes
7. Use the most precise property available (e.g., `dcterms:spatial` over `dc:coverage`)
8. All classes/resources must have identifiers (`rdf:about`)
9. Do NOT use HTML markup in property values
10. Ensure mandatory/alternative mandatory properties are present
11. `dc:type` and `edm:type` should have different values
12. When providing a URI to a dereferenceable LOD resource (e.g., Getty AAT, GeoNames), there is no need to create a contextual class — Europeana will fetch the data

### 3.2 edm:ProvidedCHO Properties

**Mandatory groups:**
- `dc:title` OR `dc:description` (at least one)
- `dc:subject` OR `dc:type` OR `dcterms:spatial` OR `dcterms:temporal` (at least one)
- `dc:language` (mandatory if `edm:type` = TEXT; recommend `zxx` for no linguistic content)
- `edm:type` (exactly one: TEXT, IMAGE, VIDEO, SOUND, or 3D)

**Full property list:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `dc:contributor` | Literal/Ref | 0..n | Use authority URIs |
| `dc:coverage` | Literal/Ref | 0..n | Prefer `dcterms:spatial`/`temporal` |
| `dc:creator` | Literal/Ref | 0..n | Use authority URIs |
| `dc:date` | Literal/Ref | 0..n | ISO 8601 recommended; distinguish from `dcterms:temporal`/`created`/`issued` |
| `dc:description` | Literal/Ref | 0..n | Required if no `dc:title` |
| `dc:format` | Literal/Ref | 0..n | Format of CHO or file format for born-digital |
| `dc:identifier` | Literal | 0..n | Identifier of the original CHO |
| `dc:language` | Literal | 0..n | ISO 639 two/three-letter codes |
| `dc:publisher` | Literal/Ref | 0..n | |
| `dc:relation` | Literal/Ref | 0..n | |
| `dc:rights` | Literal/Ref | 0..n | Rights holder (not the controlled `edm:rights`) |
| `dc:source` | Literal/Ref | 0..n | Source of original CHO |
| `dc:subject` | Literal/Ref | 0..n | |
| `dc:title` | Literal | 0..n | Exact translations via `xml:lang` |
| `dc:type` | Literal/Ref | 0..n | Nature/genre; should differ from `edm:type` |
| `dcterms:alternative` | Literal | 0..n | Alternative titles |
| `dcterms:conformsTo` | Literal/Ref | 0..n | |
| `dcterms:created` | Literal/Ref | 0..n | ISO 8601 |
| `dcterms:extent` | Literal/Ref | 0..n | Size or duration |
| `dcterms:hasFormat` | Literal/Ref | 0..n | |
| `dcterms:hasPart` | Literal/Ref | 0..n | |
| `dcterms:hasVersion` | Literal/Ref | 0..n | |
| `dcterms:isFormatOf` | Literal/Ref | 0..n | |
| `dcterms:isPartOf` | Literal/Ref | 0..n | Supports hierarchy display |
| `dcterms:isReferencedBy` | Literal/Ref | 0..n | |
| `dcterms:isReplacedBy` | Literal/Ref | 0..n | |
| `dcterms:isRequiredBy` | Literal/Ref | 0..n | |
| `dcterms:issued` | Literal/Ref | 0..n | ISO 8601 |
| `dcterms:isVersionOf` | Literal/Ref | 0..n | |
| `dcterms:medium` | Literal/Ref | 0..n | |
| `dcterms:provenance` | Literal/Ref | 0..n | |
| `dcterms:references` | Literal/Ref | 0..n | |
| `dcterms:replaces` | Literal/Ref | 0..n | |
| `dcterms:requires` | Literal/Ref | 0..n | |
| `dcterms:spatial` | Literal/Ref | 0..n | What the CHO represents in space (not where it is held) |
| `dcterms:tableOfContents` | Literal | 0..n | |
| `dcterms:temporal` | Literal/Ref | 0..n | What the CHO depicts in time |
| `edm:currentLocation` | Literal/Ref | 0..1 | Where CHO is currently held; distinct from `dcterms:spatial` |
| `edm:hasMet` | Ref | 0..n | |
| `edm:hasType` | Literal/Ref | 0..n | Type from controlled vocabulary |
| `edm:incorporates` | Ref | 0..n | |
| `edm:isDerivativeOf` | Ref | 0..n | |
| `edm:isNextInSequence` | Ref | 0..n | For hierarchy/sequence display |
| `edm:isRelatedTo` | Literal/Ref | 0..n | |
| `edm:isRepresentationOf` | Ref | 0..1 | |
| `edm:isSimilarTo` | Ref | 0..n | |
| `edm:isSuccessorOf` | Ref | 0..n | |
| `edm:realizes` | Ref | 0..n | Physical thing carries information resource |
| `edm:type` | Literal | 1..1 | TEXT, IMAGE, VIDEO, SOUND, or 3D |
| `owl:sameAs` | Ref | 0..n | Linked data URI for the object |

### 3.3 ore:Proxy Properties

The ore:Proxy class carries descriptive metadata on behalf of an `edm:ProvidedCHO`. Each item has two proxies: the **provider proxy** (original metadata) and the **Europeana proxy** (enrichments). Properties marked **EP only** appear exclusively on the Europeana proxy.

**Structural properties:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `ore:proxyFor` | Ref | 1..1 | URI of the ProvidedCHO this proxy describes |
| `ore:proxyIn` | Ref | 1..n | URI of the Aggregation this proxy belongs to |
| `edm:europeanaProxy` | Literal | 0..1 | `"true"` for Europeana proxy; absent for provider proxy |
| `edm:type` | Literal | 1..1 | **EP only.** TEXT, IMAGE, VIDEO, SOUND, or 3D |
| `edm:year` | Literal | 0..n | **EP only.** Normalised year strings |

**Descriptive properties** (same set as ProvidedCHO — the proxy carries them):

The provider proxy carries all the DC and DCTerms properties listed in Section 3.2 (dc:title, dc:creator, dc:subject, dc:date, dc:description, dc:format, dc:identifier, dc:language, dc:publisher, dcterms:spatial, dcterms:temporal, dcterms:created, etc.). All are multivalued literals, often language-tagged.

**Enriched entity URI properties** (on the Europeana proxy, in addition to provider proxy literals):

| Property | Enriched Range | Notes |
|---|---|---|
| `dc:creator` | Ref (`edm:Agent`) | Entity URI alongside provider literal |
| `dc:contributor` | Ref (`edm:Agent`) | Entity URI alongside provider literal |
| `dc:subject` | Ref (`skos:Concept`) | Entity URI alongside provider literal |
| `dcterms:spatial` | Ref (`edm:Place`) | Entity URI alongside provider literal |

Additional proxy properties: `edm:hasMet`, `edm:hasType`, `edm:incorporates`, `edm:isDerivativeOf`, `edm:isNextInSequence`, `edm:isRelatedTo`, `edm:isRepresentationOf`, `edm:isSimilarTo`, `edm:isSuccessorOf`, `edm:realizes`, `edm:currentLocation`, `edm:userTag`, `edm:pid`, `owl:sameAs`, `ore:lineage`.

### 3.4 edm:WebResource Properties

No mandatory properties. Recommended: `edm:rights`.

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `dc:creator` | Literal/Ref | 0..n | Creator of the digital resource |
| `dc:description` | Literal/Ref | 0..n | |
| `dc:format` | Literal/Ref | 0..n | |
| `dc:rights` | Literal/Ref | 0..n | Rights holder (not controlled `edm:rights`) |
| `dc:source` | Literal/Ref | 0..n | |
| `dc:type` | Literal/Ref | 0..n | |
| `dcterms:conformsTo` | Literal/Ref | 0..n | |
| `dcterms:created` | Literal/Ref | 0..n | |
| `dcterms:extent` | Literal/Ref | 0..n | |
| `dcterms:hasPart` | Ref | 0..n | |
| `dcterms:isFormatOf` | Literal/Ref | 0..n | |
| `dcterms:isPartOf` | Ref | 0..n | |
| `dcterms:isReferencedBy` | Literal/Ref | 0..n | Used for IIIF manifest URIs |
| `dcterms:issued` | Literal/Ref | 0..n | |
| `edm:isNextInSequence` | Ref | 0..n | |
| `edm:rights` | Ref | 0..1 | URI from controlled list; overrides Aggregation-level rights |
| `owl:sameAs` | Ref | 0..n | |

### 3.5 ore:Aggregation Properties

**Mandatory:** `edm:aggregatedCHO`, `edm:dataProvider`, `edm:isShownAt` OR `edm:isShownBy` (at least one; both recommended), `edm:provider`, `edm:rights`.

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `edm:aggregatedCHO` | Ref | 1..1 | URI of the ProvidedCHO |
| `edm:dataProvider` | Literal/Ref | 1..1 | Organisation providing data to aggregator |
| `edm:hasView` | Ref | 0..n | Additional digital representations |
| `edm:isShownAt` | Ref | 0..1 | URL to object in full information context on provider site; strongly recommended |
| `edm:isShownBy` | Ref | 0..1 | URL to best-resolution digital object; Europeana generates previews from direct image links |
| `edm:object` | Ref | 0..1 | URL for generating portal previews; must be an image even for sound objects. **IMAGE objects without `edm:isShownBy` nor `edm:object` will not be published** |
| `edm:provider` | Literal/Ref | 1..1 | Organisation providing data directly to Europeana |
| `edm:rights` | Ref | 1..1 | Rights statement URI from controlled list; must start with `http` not `https`; applies by default to all web resources |
| `edm:intermediateProvider` | Literal/Ref | 0..n | Must be distinct from dataProvider and provider |
| `edm:ugc` | Literal | 0..1 | Value "true" for user-generated content |
| `dc:rights` | Literal/Ref | 0..n | Legacy; prefer on WebResource or ProvidedCHO |

**Rights override logic:** The item page displays `edm:rights` from the WebResource corresponding to the selected `edm:isShownBy` or `edm:hasView`. If none is present, it falls back to `edm:rights` from the Aggregation.

### 3.6 edm:EuropeanaAggregation Properties

Created at ingestion time (internal only). A subclass of `ore:Aggregation` carrying Europeana-generated information. Identified by `?eAgg a edm:EuropeanaAggregation`.

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `edm:aggregatedCHO` | Ref | 1..1 | URI of the ProvidedCHO (inherited) |
| `edm:country` | Literal | 1..1 | Country of the data provider (e.g., `"Netherlands"`) |
| `edm:language` | Literal | 1..1 | Language of the data provider (BCP 47) |
| `edm:completeness` | Literal | 0..1 | Metadata completeness score (integer as string) |
| `edm:datasetName` | Literal | 0..1 | Europeana dataset identifier |
| `edm:landingPage` | Ref | 0..1 | Europeana portal URL for the item |
| `edm:preview` | Ref | 0..1 | Thumbnail URL generated by Europeana |
| `edm:dataProvider` | Literal/Ref | 1..1 | Copy of data provider (inherited) |
| `edm:provider` | Literal/Ref | 1..1 | Copy of provider (inherited) |
| `edm:rights` | Ref | 0..1 | Copy of rights — **do not use for rights queries** (incomplete; use `ore:Aggregation` instead) |
| `dqv:hasQualityAnnotation` | Ref | 0..n | Quality tier annotations |

### 3.7 Contextual Class Properties

**edm:Agent:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `skos:prefLabel` | Literal | 0..1 per lang | Recommended; multiple language variants strongly recommended |
| `skos:altLabel` | Literal | 0..n | Recommended |
| `skos:note` | Literal | 0..n | |
| `dc:date` | Literal/Ref | 0..n | Use only if not birth/death/establishment/termination |
| `dc:identifier` | Literal | 0..n | |
| `dcterms:hasPart` / `dcterms:isPartOf` | Ref | 0..n | Corporate bodies only |
| `edm:begin` / `edm:end` | Literal | 0..1 | ISO 8601 |
| `edm:hasMet` / `edm:isRelatedTo` | Ref | 0..n | |
| `foaf:name` | Literal | 0..n | |
| `rdaGr2:biographicalInformation` | Literal | 0..n | |
| `rdaGr2:dateOfBirth` / `dateOfDeath` | Literal | 0..1 | Person only |
| `rdaGr2:dateOfEstablishment` / `dateOfTermination` | Literal | 0..1 | Corporate body only |
| `rdaGr2:gender` | Literal | 0..1 | Person only |
| `rdaGr2:placeOfBirth` / `placeOfDeath` | Literal/Ref | 0..1 | Person only |
| `rdaGr2:professionOrOccupation` | Literal/Ref | 0..n | Person only |
| `owl:sameAs` | Ref | 0..n | |

Note: `rdaGr2` properties have newer RDA equivalents (e.g., `rdaGr2:dateOfBirth` → `rdau:P60599`).

**edm:Place:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `skos:prefLabel` | Literal | 0..1 per lang | Multiple languages recommended |
| `skos:altLabel` | Literal | 0..n | |
| `wgs84_pos:lat` / `long` | Float | 0..1 | Recommended; decimal degrees |
| `wgs84_pos:alt` | Float | 0..1 | Metres above reference |
| `dcterms:hasPart` / `isPartOf` | Ref | 0..n | |
| `edm:isNextInSequence` | Ref | 0..n | E.g., archaeological layers |
| `owl:sameAs` | Ref | 0..n | |

**edm:TimeSpan:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `skos:prefLabel` | Literal | 0..1 per lang | |
| `skos:altLabel` | Literal | 0..n | |
| `edm:begin` / `edm:end` | Literal | 0..1 | Recommended together; EDTF/ISO 8601 |
| `skos:notation` | String | 0..1 | May use `rdf:datatype` for EDTF |
| `dcterms:hasPart` / `isPartOf` | Ref | 0..n | |
| `edm:isNextInSequence` | Ref | 0..n | |
| `owl:sameAs` | Ref | 0..n | |

**skos:Concept:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `skos:prefLabel` | Literal | 0..1 per lang | Recommended; multiple translations |
| `skos:altLabel` | Literal | 0..n | Recommended; not for translations of prefLabel |
| `skos:broader` / `narrower` / `related` | Ref | 0..n | Within same scheme |
| `skos:broadMatch` / `narrowMatch` / `relatedMatch` | Ref | 0..n | Cross-scheme |
| `skos:exactMatch` / `closeMatch` | Ref | 0..n | Cross-scheme |
| `skos:notation` | String | 0..n | |
| `skos:inScheme` | Ref | 0..n | |

**cc:License:**

| Property | Value Type | Card. | Notes |
|---|---|---|---|
| `odrl:inheritFrom` | Ref | 1..1 | Base rights statement from Europeana-controlled list |
| `cc:deprecatedOn` | Literal (XML date) | 0..1 | Expiry date |

### 3.8 Temporal Metadata Recommendations

Europeana normalizes dates using Extended Date/Time Format (EDTF) level 1 and ISO 8601 extended format. Normalized values are stored in the Europeana proxy; originals remain in the provider proxy.

**14 normalizable date patterns:** `YYYY-MM-DD`, `DD-MM-YYYY` (with separator variations), `DD month_name YYYY` (24 EU languages), `month_name YYYY`, date ranges with separators, century (Roman numerals), year-era, abbreviated ranges (e.g., 1770-80), negative years (up to 9 digits), DCMI Period (`name=; start=; end=`), formatted timestamps.

**Uncertain/approximate:** `?` for uncertain, `ca.`/`circa`/`c.` for approximate, `?/date` or `date/?` for unknown range bounds.

**Recommendations:**
- Use the most specific metadata element (e.g., `dcterms:created` over `dc:date`)
- Avoid providing the same date as both literal and TimeSpan reference
- Only Gregorian calendar supported
- Judge whether a period should be TimeSpan, Concept, or both

### 3.9 Identifier Requirements

Four types of identifiers used in EDM:
1. **HTTP URI referencing external LOD resource** (dereferenceable) — preferred
2. **HTTP URI referencing internal resource** (not dereferenceable, but globally unique)
3. **Local non-dereferenceable URI** (e.g., `urn:` scheme)
4. **Non-dereferenceable identifier** (e.g., inventory number) — least preferred

Every resource must have a unique identifier in `rdf:about`. Linking between resources uses `rdf:resource` attributes.

### 3.10 XML Schema and Validation

The EDM XML Schema enables automatic validation. Available at `http://www.europeana.eu/schemas/edm/EDM.xsd` and on GitHub (`europeana/metis-schema`). Includes Schematron rules for constraints beyond XSD capabilities (e.g., mandatory alternatives). Validation can be performed in Oxygen XML Editor.

### 3.11 Known Data Anomalies

Common anomalies detected in Europeana data, grouped by category:

**Identifier issues:** Same rdf:about for different CHOs (from different providers); provider URI resolving to different content than expected; CHO identifier used for WebResource or vice versa; different providers describing same CHO with different identifiers.

**Descriptive metadata issues:** Metadata describing the digital resource rather than the CHO; dc:creator referring to the photographer rather than the original artist; dates referring to digitisation rather than creation; language codes for metadata language rather than CHO language.

**Structural issues:** Multiple edm:type values; edm:isShownBy pointing to HTML page rather than media file; rights statements contradicting each other across properties; WebResource rights more restrictive than Aggregation rights without justification.

---

## 4. Publishing Framework

The Europeana Publishing Framework (EPF) defines quality tiers for both content and metadata. Higher tiers unlock greater visibility, reuse potential, and inclusion in partnerships.

### 4.1 Content Tiers

| Tier | Role | Benefit |
|---|---|---|
| **1** | Europeana as search engine | Findability, web traffic referrals to provider site |
| **2** | Europeana as showcase | Good-quality display on Europeana; thematic collections |
| **3** | Distribution platform (non-commercial reuse) | Partnerships (Historiana, CLARIN); apps and services |
| **4** | Free reuse platform | Creative industries, Wikimedia, hackathons, #OpenCollections |

#### Content Tier Requirements by Type

**IMAGE:**

| Tier | Resolution | Rights |
|---|---|---|
| 1 | ≥ 0.1 MP (≥ 300×350); thumbnail available | Any |
| 2 | ≥ 0.42 MP (~800×533); thumbnail available | Any |
| 3 | ≥ 0.95 MP (~1200×800); thumbnail available | Open or restricted |
| 4 | ≥ 0.95 MP; thumbnail available | Open only |

**TEXT:**

| Tier | Requirement | Rights |
|---|---|---|
| 1 | Image ≥ 0.1 MP OR working `edm:isShownAt` | Any |
| 2 | PDF or image ≥ 0.42 MP | Any |
| 3 | PDF or image ≥ 0.95 MP | Open or restricted |
| 4 | PDF or image ≥ 0.95 MP | Open only |

**SOUND:**

| Tier | Requirement | Rights |
|---|---|---|
| 1 | Working `edm:isShownAt` | Any |
| 2 | Direct link to audio file OR embeddable media; HTML5-playable | Any |
| 3 | Same as Tier 2 | Open or restricted |
| 4 | Same as Tier 2 | Open only |

**VIDEO:**

| Tier | Requirement | Rights |
|---|---|---|
| 1 | Video available OR working `edm:isShownAt` | Any |
| 2 | Vertical resolution ≥ 480px OR embeddable media; HTML5-playable | Any |
| 3 | Same as Tier 2 | Open or restricted |
| 4 | Same as Tier 2 | Open only |

**3D:**

| Tier | Requirement | Rights |
|---|---|---|
| 1 | Working `edm:isShownAt` with 3D viewer; thumbnail available | Any |
| 2 | Tier 1 + oEmbed-compliant viewer + `edm:intendedUsage` | Any |
| 3 | Tier 2 + direct link to supported 3D file + `dc:type` + technical metadata | Open or restricted |
| 4 | Same as Tier 3 | Open only |

**Important:** If content quality is too low for Tiers 3-4, the rights statement is not considered. Only sufficiently high-quality content benefits from open rights.

#### Rights Statements for Tiers

**Tier 3 (restricted reuse — 7 statements):** CC BY-NC, CC BY-ND, CC BY-NC-ND, CC BY-NC-SA, NoC-NC, NoC-OKLR, InC-EDU

**Tier 4 (open/free reuse — 4 statements):** CC BY, CC BY-SA, CC0, PDM (Public Domain Mark)

### 4.2 Metadata Tiers

Three criteria assessed on a scale A–C. Overall tier = lowest of the three.

| Criterion | Tier A | Tier B | Tier C |
|---|---|---|---|
| **Language** | ≥25% of relevant ProvidedCHO properties have ≥1 language-qualified value | ≥50% | ≥75% |
| **Enabling elements** | ≥1 element from 1 Discovery scenario group | ≥3 distinct elements from ≥2 groups | ≥4 distinct elements from ≥2 groups |
| **Contextual classes** | None required | ≥1 class with min required elements, or LOD link | ≥2 classes with min required elements, or LOD links |

**Language qualification:** Either a literal value with `xml:lang`, or a URI link to a contextual entity with at least one language-qualified `skos:prefLabel`. 22 relevant ProvidedCHO properties are assessed.

**Four Discovery scenario groups:**
1. Browse by date/time-span
2. Browse by subjects and types
3. Browse by agents
4. Browse by places

**Minimum required elements per contextual class (for Tier B/C):**
- **edm:TimeSpan:** `skos:prefLabel` + begin or end date
- **skos:Concept:** `skos:prefLabel` + one of broader/narrower/related/exactMatch/closeMatch/note
- **edm:Agent:** `skos:prefLabel` + one of dateOfBirth/Death, placeOfBirth/Death, professionOrOccupation, gender, biographicalInformation
- **edm:Place:** `skos:prefLabel` + `wgs84:lat` + `wgs84:long`

**Note:** Europeana's own automatic enrichments do NOT count for tier classification. Only provider-submitted or dereferenced data counts.

### 4.3 Licenses and Rights Statements

Every digital object must have a rights statement in `edm:rights` (on ore:Aggregation and/or edm:WebResource) or via `cc:License` class with `odrl:inheritFrom`. URIs must start with `http` (not `https`). Values in `dc:rights`, `edm:rights`, and `odrl:inheritFrom` must not contradict each other.

**Creative Commons Licenses:**
Pattern: `http://creativecommons.org/licenses/{type}/{version}/`
- Types: by, by-sa, by-nd, by-nc, by-nc-sa, by-nc-nd
- Versions: 1.0 through 4.0 (4.0 is international, no country ports)

**Rights Statements (RightsStatements.org):**
Pattern: `http://rightsstatements.org/vocab/{id}/1.0/`
- **InC** — In Copyright
- **InC-EDU** — In Copyright, Educational Use Permitted
- **InC-EU-OW** — In Copyright, EU Orphan Work (must be registered in EU Orphan Works Database)
- **NoC-NC** — No Copyright, Non-Commercial Use Only (must supply contract; set expiry via `cc:deprecatedOn`)
- **NoC-OKLR** — No Copyright, Other Known Legal Restrictions
- **CNE** — Copyright Not Evaluated (consult Europeana before using)

**Public Domain Tools:**
- `http://creativecommons.org/publicdomain/zero/1.0/` — CC0
- `http://creativecommons.org/publicdomain/mark/1.0/` — Public Domain Mark

**Europeana's approach to accuracy:** Data providers are responsible for compliance. Europeana takes a "clean hands" approach with manual review during ingestion and post-publication analysis. Public Domain works in analog form should remain Public Domain when digitised (per Europeana Public Domain Charter).

### 4.4 Rights Classification for SPARQL

For SPARQL queries, rights URIs in `edm:rights` (on `ore:Aggregation`) are classified into three reuse levels. The authoritative implementation is in `src/europeana_qlever/rights.py`.

**Open** — free reuse (CC public domain tools and permissive licenses):
- `http://creativecommons.org/publicdomain/zero/1.0/` (CC0)
- `http://creativecommons.org/publicdomain/mark/1.0/` (Public Domain Mark)
- `http://creativecommons.org/licenses/by/` (CC BY, any version/port)
- `http://creativecommons.org/licenses/by-sa/` (CC BY-SA, any version/port)

SPARQL detection: `STRSTARTS(STR(?rights), "http://creativecommons.org/publicdomain/")` or `STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/")` or `STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by-sa/")`.

**Restricted** — limited reuse (CC licenses with NC or ND clauses, plus select RightsStatements.org):
- CC licenses whose URI contains `-nc` or `-nd` (e.g., `by-nc`, `by-nd`, `by-nc-sa`, `by-nc-nd`)
- `http://rightsstatements.org/vocab/NoC-NC/1.0/` (No Copyright, Non-Commercial)
- `http://rightsstatements.org/vocab/NoC-OKLR/1.0/` (No Copyright, Other Known Legal Restrictions)
- `http://rightsstatements.org/vocab/InC-EDU/1.0/` (In Copyright, Educational Use)

SPARQL detection: `CONTAINS(STR(?rights), "-nc") || CONTAINS(STR(?rights), "-nd")` plus exact matches for the three RightsStatements.org URIs.

**Prohibited** — no reuse permitted (everything else):
- `http://rightsstatements.org/vocab/InC/1.0/` (In Copyright)
- `http://rightsstatements.org/vocab/InC-OW-EU/1.0/` (In Copyright, EU Orphan Work)
- `http://rightsstatements.org/vocab/CNE/1.0/` (Copyright Not Evaluated)
- `http://rightsstatements.org/vocab/NKC/1.0/` (No Known Copyright)
- `http://rightsstatements.org/vocab/UND/1.0/` (Undetermined)

**Important:** Always use `STR(?rights)` when matching, since `edm:rights` is a URI. There are ~580 valid rights URIs across all CC versions and country ports; the `STRSTARTS`/`CONTAINS` approach correctly classifies all of them.

### 4.5 Digital Objects vs Non-Digital Objects

**Digital objects:** A digital representation of cultural/scientific heritage, or a born-digital original. A 300-page book is one object, not 300. Audio/video snippets generally not adequate.

**Non-digital objects:** Objects without digital representation; value resides in metadata. Included only exceptionally, with hierarchical metadata containing explicit `hasPart`/`isPartOf` relations with digital objects.

### 4.6 Media Policy

**Processed media links:** `edm:object`, `edm:isShownBy`, `edm:hasView` (multiple), `edm:isShownAt` (checked for resolvability but no thumbnail generated).

**Media retrieval requirements:**
- Valid URL (IETF RFC 3986/3987), HTTPS recommended
- Must resolve directly to media resource (not HTML page)
- Maximum 3 redirects; download within 20 minutes
- Valid IANA MIME type
- Large PDFs: optimize for Fast Web View

**Thumbnail generation:** Two sizes: max 200px and max 400px width. Generated from `edm:object` (priority), then `edm:isShownBy`, then first `edm:hasView`.

**CORS:** Provider servers must support Cross-Origin Resource Sharing. Essential for IIIF.

**Embedding:** Requires valid oEmbed endpoint registered in Europeana's internal registry.

**Supported media formats:**

*Browser-supported (painted on IIIF canvas):*
- Image: JPEG, PNG, GIF, BMP, SVG, WebP
- Video: MP4, WebM, M4V, QuickTime, MPEG, DASH, OGG
- Sound: MP4, MPEG, FLAC, WAV, Vorbis, OGG, AIFF

*Specialized (thumbnail + rendering):*
- Image: JPEG2000, JP2, TIFF, PSD, DjVu
- Text: PDF, plain text, RTF, EPUB
- Video: FLV, WMV, AVI, MKV
- Sound: WMA, AMR
- 3D (under development): LAS/LAZ, E57, DXF, OBJ, DAE, STL, IGES, STEP, VRML, X3D, glTF, USD

---

## 5. Europeana APIs

### 5.1 Access and Authentication

**API key types (since 28 May 2025):**
- **Personal keys:** One per account; lower rate limits; for experimentation
- **Project keys:** Per-service; higher limits; requires approval (1-5 working days)

Registration requires a Europeana account at `https://pro.europeana.eu/pages/get-api`.

**Authentication methods:**
1. `X-Api-Key` header (preferred)
2. `wskey` query parameter (deprecated, being phased out)
3. `Authorization: Bearer [JWT]` for write access (restricted to partners)

**Auth service (OIDC):** `https://auth.europeana.eu/auth/realms/europeana/`. Supports client credentials, user credentials, authorization code, and refresh token grants.

### 5.2 Search API

**Endpoint:** `GET https://api.europeana.eu/record/v2/search.json`

**Key parameters:**

| Parameter | Description |
|---|---|
| `query` | Required. Search terms (Lucene syntax) |
| `qf` | Query refinement (repeatable) |
| `reusability` | Filter: open/restricted/permission |
| `media` | Boolean: has resolvable media |
| `thumbnail` | Boolean: has thumbnail |
| `sort` | score, timestamp_created/update, europeana_id, COMPLETENESS, is_fulltext, has_thumbnails, has_media, random |
| `rows` | Results per page (max 100, default 12) |
| `start` | Offset for basic pagination (limited to first 1000) |
| `cursor` | Cursor-based pagination (set `*` to start, follow `nextCursor`; no limit) |
| `profile` | Response richness: minimal, standard, rich, facets, breadcrumbs, params, portal |
| `colourpalette` | Filter by hex colour in images |
| `theme` | Thematic collection: archaeology, art, fashion, industrial, manuscript, map, migration, music, nature, newspaper, photography, sport, ww1 |

**Query syntax:** Apache Lucene via Solr eDismax. Supports phrase search (`"Mona Lisa"`), field search (`who:Vermeer`), boolean (AND/OR/NOT), wildcards (`*`, `?`, `~`), ranges (`[a TO z]`), geographic bounding boxes, date math (NOW, NOW+1DAY).

**Aggregated search fields:** `title` (dc:title + dcterms:alternative), `subject` (dc:coverage + dc:subject + dcterms:spatial + dcterms:temporal), `what`, `when`, `where`, `who`, `text` (combines nearly all descriptive fields).

**Media-specific fields:** MEDIA, MIME_TYPE, IMAGE_SIZE (small/medium/large/extra_large), IMAGE_COLOUR, IMAGE_GREYSCALE, COLOURPALETTE, IMAGE_ASPECTRATIO, VIDEO_HD, VIDEO_DURATION, SOUND_HQ, SOUND_DURATION, TEXT_FULLTEXT.

**Reusability values:**
- **open:** PDM, CC0, CC BY, CC BY-SA
- **restricted:** CC BY-NC, CC BY-NC-SA, CC BY-NC-ND, CC BY-ND, InC-EDU, NoC-NC, NoC-OKLR
- **permission:** InC, InC-OW-EU, CNE

**Faceting:** Default facets include TYPE, LANGUAGE, COUNTRY, DATA_PROVIDER, PROVIDER, RIGHTS, YEAR, COLOURPALETTE, MIME_TYPE, REUSABILITY, IMAGE_SIZE, and more. Custom facets via `facet` parameter. Limits via `f.[FACET].facet.limit/offset`.

**Pagination:** Basic (start parameter, limited to first 1000 results) and Cursor-based (set cursor=* to start, follow nextCursor values, no limit).

**OpenSearch RSS:** `GET https://api.europeana.eu/record/opensearch.rss?searchTerms=TERMS`

### 5.3 Record API

**Endpoint:** `GET https://api.europeana.eu/record/v2/[RECORD_ID].[FORMAT]`

Record ID format: `/DATASET_ID/LOCAL_ID`. Formats: `.json` (Europeana schema), `.jsonld` (JSON-LD/RDF), `.rdf` (RDF/XML per EDM XSD).

Response includes the full EDM record: aggregations, proxies, web resources (with technical metadata), contextual entities (agents, concepts, places, timespans), licenses, services, quality annotations.

### 5.4 Entity API

**Endpoint:** `GET https://api.europeana.eu/entity/[TYPE]/[ID]`

Entity types: agent, place, concept, timespan, organization. URIs: `http://data.europeana.eu/[TYPE]/[ID]`.

**Operations:**
- **Retrieve:** `GET /entity/{type}/{id}` — JSON-LD or RDF/XML; profiles: "internal" (full + admin) or "external" (default)
- **Resolve:** `GET /entity/resolve?uri={URI}` — Returns 301 with Europeana URI via `owl:sameAs`/`skos:exactMatch` lookup
- **Search:** `GET /entity/search?query={query}` — Parameters: type, scope (europeana), lang, page, pageSize (max 100), sort, facet

### 5.5 Annotation API

Based on W3C Web Annotation Data Model. Console: `https://api.europeana.eu/console/annotation`.

**Supported motivations:** linking, tagging, describing, transcribing, subtitling.

**Application scenarios:** Object links (to external resources), semantic tagging (controlled vocabularies), simple tagging (free-text), geo-tagging, transcription/subtitling.

Write access requires partnership agreement and bearer tokens.

### 5.6 IIIF APIs

No API key required. Console: `https://api.europeana.eu/console/iiif`.

**Manifest retrieval:** `GET https://iiif.europeana.eu/presentation/[RECORD_ID]/manifest`
- Default: v2.1; v3 via Accept header or `format` parameter
- Supports Presentation API v2/v3, Content Search API v1, Image API (provider-supplied), and Fulltext API

**Manifest structure:** Canvases with painting annotations for each web resource. Content type determines rendering: browser-supported formats are painted directly; specialized formats show thumbnail + rendering link; unsupported formats generate no canvas.

**Full-text search:** Across all items via Search API parameters; within single item via IIIF Content Search API service in manifest.

### 5.7 SPARQL API

**Endpoint:** `https://sparql.europeana.eu/` — Powered by Virtuoso. No API key required. Supports federated queries with VIAF, Iconclass, Getty AAT, GeoNames, Wikidata, DBPedia.

### 5.8 Other APIs

**Recommendation API:** ML-based similarity using vector embeddings.
- `GET /recommend/record/[ID]` — Similar items
- `GET /recommend/entity/[TYPE]/[ID]` — Related entity items
- `GET /recommend/set/[ID]` — Related set items

**User Set API:** Supports galleries, favorites, curated entity collections. Beta since April 2025. Search, retrieve, create/update sets and items. Console: `https://api.europeana.eu/console/set`.

**Thumbnail API:**
- v3: `GET /thumbnail/v3/[SIZE]/[HASH].[FORMAT]` — Returns 404 if not found
- v2: `GET /thumbnail/v2/url.json?url=[URL]&size=[SIZE]&type=[TYPE]` — Always returns an image (default fallback)
- Sizes: 200 or 400px width

### 5.9 Bulk Data Access

**FTP:** `ftp://download.europeana.eu/dataset/` — Anonymous login. ZIP files in RDF-XML and Turtle, regenerated weekly. MD5 checksums available.

**Newspapers bulk download:** Datasets with metadata (EDM XML), ALTO full-text, page/issue-level full-text. Metadata is CC0; full-text is Public Domain Mark. Files range 4MB–278GB.

**OAI-PMH:** `https://api.europeana.eu/oai/record/` — Supports Identify, GetRecord, ListIdentifiers, ListMetadataFormats, ListRecords, ListSets with resumption tokens. Records in EDM RDF/XML. Recommend re-harvest every 6 months.

### 5.10 Fair Use Policy

Rate limits apply; 429 responses indicate limit reached. For bulk data, use FTP/OAI-PMH. Strategy: identify datasets via Search API `edm_datasetName` facet, then download in bulk.

### 5.11 Libraries

- **Python:** PyEuropeana (`pip install pyeuropeana`)
- **Java:** REPOX (metadata management, OAI-PMH), Entity API library by AIT
- **Node.js:** `npm install europeana` (unofficial)
- **Browser:** "Open in IIIF viewer" extension for Firefox/Chrome

---

## 6. Data Processing and Enrichment

### 6.1 Ingestion Pipeline (Metis)

The Metis workflow has 9 steps: Harvest → Transformation to EDM → Validation External → Transformation → Validation Internal → Normalisation → Enrichment → Media Processing → Publish.

### 6.2 Semantic Enrichment

**Two types of enrichment during ingestion:**

**Dereferencing:** When providers include URIs from supported LOD vocabularies, Europeana fetches multilingual/semantic data and maps it to EDM contextual classes via SKOS. Configuration files on GitHub (`europeana/metis-vocabularies`). Europeana does not overwrite provider-submitted contextual classes.

**Automatic enrichment:** Europeana matches metadata values to controlled terms from the Europeana Entity Collection (agents, places, concepts, timespans, organizations).

Enrichments are stored in the Europeana proxy (`europeanaProxy=true`), keeping source metadata intact.

### 6.3 Automatic Enrichment Process

**Three matching cases:**
1. **Plain literal:** Text value matches `skos:prefLabel`/`skos:altLabel` in an entity (case-insensitive, language-aware)
2. **Coreference URI:** URI in source matches `owl:sameAs`/`skos:exactMatch` in an entity
3. **Coreferences in entity data:** URI in provided contextual class matches entity co-references

**Source-to-target mapping:**
- Agent: `dc:creator`, `dc:contributor` → agent entity with labels and `owl:sameAs`
- Place: `dcterms:spatial`, `dc:coverage` → place entity
- Time: `dc:date`, `dcterms:temporal`, `dcterms:created`, `dcterms:issued` → timespan entity
- Concept: `dc:subject`, `dc:type`, `dc:format`, `dcterms:medium` → concept entity

### 6.4 Organisation Enrichment

Source fields: `edm:dataProvider`, `edm:intermediateProvider`, `edm:provider`.

**Key difference from other enrichments:** The source value is **replaced** with the Europeana entity URI (not retained alongside). Supports matching by name (original language, English, or acronym from CRM) and by URI (`owl:sameAs` from Wikidata, VIAF, ULAN, GND, ISNI, ARK, ROR).

### 6.5 Supporting New Vocabularies

Seven-step process:
1. Data provider submits request via Jira
2. Metadata coordinator reviews against criteria: supports content negotiation to RDF/XML, openly licensed (CC BY/CC BY-SA/CC0), good structure, high semantic relationships, multilingual coverage
3. Operations team consulted
4. RDF/XML data profile checked
5. Contextual mapping (crosswalk) created between vocabulary and EDM contextual class
6. XSL stylesheet created for transformation
7. Aggregation Systems team adds XSL to Metis and publishes on GitHub

### 6.6 Metis Sandbox

Online testing tool at `https://metis-sandbox.europeana.eu/`. Simulates ingestion, shows how records would appear on Europeana, provides quality insights.

**Key features:**
- Maximum 1,000 records per dataset; step size for sampling larger sets
- Three upload methods: ZIP file, HTTP(S), OAI-PMH
- Optional XSL transformation to EDM
- Full 9-step Metis workflow simulation
- Tier statistics (content, metadata, language, enabling elements, contextual classes)
- Problem pattern analysis
- DE-BIAS project integration for contentious term detection
- Datasets cleaned up after one month
- Preview portal: `https://metis-preview-portal.eanadev.org/en`

---

## 7. IIIF at Europeana

### 7.1 IIIF in EDM Pattern (6 Steps)

1. **Identify link type** (MUST): Use `edm:isShownBy`, or `edm:hasView` if `isShownBy` already present
2. **Supply IIIF URI** (SHOULD): WebResource identifier with IIIF parameters (region/size/rotation/quality.format). Use highest resolution. In IIIF v3, "max" replaces "full". URI must be a media view, NOT a manifest
3. **Flag as IIIF-compliant** (MUST): `svcs:has_service` on WebResource connecting to `svcs:Service` with `dcterms:conformsTo` = `http://iiif.io/api/image`
4. **Service identifier** (MUST): Must be the IIIF base URI per spec
5. **Provide manifest** (MAY): Via `dcterms:isReferencedBy` on WebResource; Europeana supports Presentation API v2 and v3
6. **Implementation level** (MAY): Via `doap:implements` on Service (e.g., `http://iiif.io/api/image/2/level2.json`)

**Two cases:**
- **Case 1 (manifest available):** Full IIIF experience; provider manifest used by Europeana's Mirador v3 viewer
- **Case 2 (no manifest):** Europeana generates manifest automatically from EDM

**Example XML (Case 1):**
```xml
<ore:Aggregation>
  <edm:isShownBy rdf:resource="https://iiif.example.org/image/full/full/0/default.jpg"/>
</ore:Aggregation>
<edm:WebResource rdf:about="https://iiif.example.org/image/full/full/0/default.jpg">
  <dcterms:isReferencedBy rdf:resource="https://example.org/manifest"/>
  <svcs:has_service rdf:resource="https://iiif.example.org/image"/>
</edm:WebResource>
<svcs:Service rdf:about="https://iiif.example.org/image">
  <dcterms:conformsTo rdf:resource="http://iiif.io/api/image"/>
  <doap:implements rdf:resource="http://iiif.io/api/image/2/level2.json"/>
</svcs:Service>
```

**CORS required** for Europeana to display IIIF images.

### 7.2 EDM to IIIF Mapping

Key mappings from EDM fields to IIIF manifest fields:

| EDM Property | IIIF v3 | IIIF v2.1 |
|---|---|---|
| `dc:title` | label | label |
| `dc:description` | summary | description |
| `edm:rights` | rights | license |
| `edm:isShownBy` | Canvas body | Canvas resource |
| `edm:hasView` | Additional Canvases | Additional Canvases |
| `ebucore:width`/`height` | Canvas dimensions | Canvas dimensions |
| `ebucore:duration` | Canvas duration | Canvas duration |
| `svcs:hasService` | Image Service | Image Service |
| `dcterms:isReferencedBy` | Provider manifest reference | Provider manifest reference |

### 7.3 Embeddable Resources (oEmbed)

For content from platforms like Sketchfab, YouTube, Vimeo, SoundCloud, EUscreen. Uses oEmbed standard.

1. WebResource URI must be the oEmbed URL (endpoint + resource URL)
2. Connect WebResource to `svcs:Service` via `svcs:has_service`; add `dcterms:conformsTo` = `https://oembed.com/`
3. Provide thumbnail via `edm:object` (embeddable resource must NOT be used as `edm:object`)
4. Optionally include direct media alongside; link with `dcterms:isFormatOf`

**Common oEmbed endpoints:** YouTube (`/oembed`), Vimeo (`/api/oembed`), SoundCloud (`/oembed`), EUscreen (`/services/oembed`), Sketchfab (`/oembed`), Eureka3D, WEAVE.

### 7.4 IIIF Guidance for Providers

**Image preparation:** Scripts for IIPImage server setup and pyramid TIFF conversion using VIPS (Linux). Storage increase ~1200%.

**Manifest creation:** EDM2IIIF tool at `openup.ait.co.at/edm2manifest/` — creates IIIF manifests from EDM metadata for IMAGE-type objects via OAI-PMH or ZIP upload.

---

## 8. Persistent Identifiers (PIDs)

### 8.1 Policy (20 Principles)

Organized in 4 areas:

**Characteristics:** P1: URI following recognized scheme with large ID space. P2: Opaque (minimal embedded meaning). P3: Unique (one resource, never reused). P4: Persistent (never changed/deleted).

**Assigning & managing change:** P5: Assigned to resources with stable definitions. P6: Not restricted to specific resource types. P7: Significant changes = new PID. P8: Deleted resources keep PID, marked deprecated.

**Dissemination & interoperability:** P9: Resolves to landing page/resource/PID record. P10: Deprecated PIDs show tombstone page. P11: PID record maintained, machine-readable, openly accessible. P12: No restrictions on PID usage. P13: Users informed on sustainable referencing.

**Sustainability & governance:** P14–P20: Trustworthy infrastructure, single committed owner, public ownership info, no new PID on ownership change, explicit PID policy.

### 8.2 Recognized PID Schemes

| Scheme | Format | Resolver |
|---|---|---|
| **Handle** | `hdl:10.<AGENCY_ID>/<LOCAL_ID>` | hdl.handle.net |
| **DOI** | `info:doi/10.<AGENCY_ID>/<LOCAL_ID>` | doi.org |
| **NBN** | `URN:NBN:<COUNTRY>-<LOCAL_ID>` | Country-specific (AT, CH, CZ, DE, FI, HU, IT, NL, NO, SE, SI, SK) |
| **ARK** | `ark:/<NAAN>/<Name>` | n2t.net |
| **PURL** | Persistent URLs | purl.org, purl.pt, purl.gov |

### 8.3 PIDs in EDM

**Providing PIDs (4 steps):**
1. Identify existing PIDs for ProvidedCHO and WebResource
2. Supply PID as literal via `edm:pid` (any valid form; multiple allowed)
3. Use PID as `rdf:about` attribute of the relevant EDM class
4. PIDs validated during ingestion against the PID scheme registry; unrecognized PIDs flagged

**During ingestion:** PIDs are normalized and converted into `edm:PersistentIdentifier` class instances with canonical form (`rdf:value`), scheme (`skos:inScheme`), URL form (`edm:hasURL`), equivalents, and creation metadata.

### 8.4 Role of Aggregators

CHIs are the authoritative source for PIDs. Aggregators should NOT create new PIDs but should:
1. Advocate for PID adoption among data providers
2. Promote good practices aligned with the 20 principles
3. Include PIDs in metadata following the EDM PID profile
4. Optionally become a registration authority within existing PID systems

### 8.5 Upgrading Existing PIDs

Europeana scanned all records for PIDs in `rdf:about` and `dc:identifier`. Upgrade process: normalize detected PIDs, create `edm:PersistentIdentifier` class, get aggregator confirmation. Aggregators review with CHIs to verify PID scope and correct EDM class mapping.

---

## 9. Copyright and Legal

### 9.1 Copyright Management Guidelines for CHIs

Three-phase maturity model published March 2022 by the Europeana Copyright Community Steering Group:

**Phase 1 — Foundation:** Develop workflows at collection management stages:
- **Acquisition:** Obtain copyright information at acquisition; integrate transfer/license clauses
- **Documentation:** Record and maintain copyright status; ensure visibility
- **Digitisation:** Clear copyright in reproductions; prioritize procedures where no new copyright emerges
- **Digital access:** Maintain clear policies; define access/reuse policy; publish guidance

**Phase 2 — Expansion:** Build copyright knowledge and support:
- **Staff training:** Establish education levels per role; design targeted guidance/training
- **Senior management:** Dedicated training on copyright importance

**Phase 3 — Integration:** Embed copyright in activities and projects:
- **Short-term:** Include copyright in project plans/templates; document resource requirements
- **Long-term:** Make the case for copyright resources based on project needs

**Cross-cutting goals:**
- Harmonize copyright approaches across the organisation (overarching policy)
- Harmonize risk management (evaluate risk appetite; compare risks of open vs closed)

### 9.2 Article 14 — Reproductions of Public Domain Visual Art

Article 14 of the CDSM Directive establishes that when copyright on a work of visual art has expired, reproductions of that work are not subject to copyright unless the reproduction is itself original. This safeguards the public domain.

**Implementation across EU/EEA (key patterns):**

*Countries with "other photographs" related rights (50-year protection for non-original photos):* Austria, Denmark, Finland, Germany, Iceland, Italy, Norway, Spain, Sweden. Article 14 creates an exception to this related right for reproductions of public domain visual art.

*Countries without such related rights:* Belgium, Bulgaria, Croatia, Cyprus, Czechia, Estonia, France, Greece, Hungary, Ireland, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia. In these countries, non-original reproductions were generally unprotected already; Article 14 was often implemented as a clarification or not transposed at all (deemed unnecessary).

**Notable variations:**
- **Belgium:** Extended scope beyond visual arts; retroactive effect
- **France:** Not transposed (existing law already compliant), but Cultural Heritage Code can restrict use of heritage images
- **Germany:** 2018 BGH ruling held that mere reproduction photographs are not protected by related rights
- **Italy:** Cultural Heritage Code imposes authorization requirements regardless of copyright
- **Sweden:** Applied to "work of art" (broader than "work of visual art"); probably retroactive
- **Poland:** Not transposed; referred to CJEU by European Commission

### 9.3 Out of Commerce Works

The CDSM Directive allows CHIs to make available out-of-commerce works under licenses from representative CMOs, or under an exception where no representative CMO exists. Key elements tracked per country: legal provisions, out-of-commerce determination, representative CMOs, opt-out conditions, license/exception scope, publicity measures.

Countries with detailed implementations include Austria, Belgium, Croatia, Czechia, Estonia, France, Germany, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Netherlands, Slovakia, Spain.

### 9.4 Openness and Digital Cultural Heritage

**Key principles:**
- "Open" = anyone free to access, use, modify, and share for any purpose
- Being available online does not make content "open" — copyright is automatic, all rights reserved by default
- Only CC BY and CC BY-SA are considered "open" licenses; CC0 and PDM are public domain tools
- Rights Statements are labels (not legally binding) communicating copyright status
- All Europeana metadata is CC0; each digital object individually labeled by the data provider
- The Europeana Public Domain Charter holds that public domain works should remain public domain when digitised
- FAIR principles (Findable, Accessible, Interoperable, Reusable) go beyond openness; CARE Principles for Indigenous Data Governance provide an important counterpart

---

## 10. Organisation Entities

Organisation pages on europeana.eu allow browsing collections by institution.

**Data source:** Zoho CRM, enriched with Wikidata. Entity API provides access (`GET https://api.europeana.eu/entity/organization/{ID}`).

**New provider onboarding:** Aggregators submit spreadsheet via Jira. Mandatory CRM fields: Institution Name & Language, Sector, Subsector, Website, Official Language, Country. Recommended: alternative names, `owl:sameAs` URIs (Wikidata, VIAF, ULAN, GND, ISNI, ARK, ROR).

**Enrichment during ingestion:** Organisation names/URIs in `edm:dataProvider`, `edm:intermediateProvider`, `edm:provider` are matched against the entity collection and replaced with Europeana entity URIs.

**Organisation page curation:** Authorized users can edit description (240 char limit) and pin up to 24 highlight items via the Europeana website. Publication handled by EF staff.

---

## 11. 3D Content

### 11.1 Requirements

1. 3D models published online and accessible in a viewer
2. Metadata mapped to EDM with `edm:type` = '3D'
3. Data Exchange Agreement signed with Europeana or aggregator

### 11.2 Mapping 3D to EDM (8 Steps)

1. **oEmbed viewer URL** (mandatory for Tier 2): Provide in `edm:isShownBy`; supported patterns include Sketchfab and WEAVE viewer URLs
2. **Thumbnail** (mandatory for Tier 1): Provide via `edm:object`
3. **Direct 3D file link** (mandatory for Tier 3): As `edm:WebResource`; link views to models via `dcterms:isFormatOf`
4. **Intended usage** (mandatory for Tier 2): `edm:intendedUsage` with controlled vocabulary
5. **Relation to reality** (optional): `schema:digitalSourceType` (captured/reconstructed/born-digital)
6. **Extra properties** (optional): `dc:title`, `dc:language`, `dcterms:temporal`
7. **Model type** (optional, helps Tier 3/4): `dc:type` from controlled vocabulary (3DMesh, 3DPointCloud, BIM, parametricModel) with corresponding technical metadata (`edm:vertexCount`, `edm:polygonCount`, `edm:pointCount`)
8. **Paradata** (optional): Digitisation process info via `rdfs:seeAlso` with `dcterms:conformsTo` (CIDOC DIG, CARARE 2.0)

**Formats:** No officially recommended format. Common: DAE, PLY, WRL, glTF, OBJ, STL, NXS/NXZ, DICOM, IFC, USDZ. 3D PDF is NOT sufficient. Europeana does NOT host 3D files.

**Rights for 3D:** If original object and 3D model have different rights, use the most restrictive. Faithful representations of public domain objects are generally in public domain. New copyright only arises from creative choices in shapes/textures/lighting.

---

## 12. User Guides and Operational Tools

### 12.1 Metis Sandbox

See section 6.6 for details. Access: `https://metis-sandbox.europeana.eu/`. Key resource for testing data quality before submission.

### 12.2 Jira for Partners

The DPS team uses Jira with 2-week sprints starting Tuesdays. Each data partner has an epic; each dataset has a ticket. New datasets submitted via DPS service desk. Prioritisation: first come first served, weighted by deadlines, demand, and quality. Ticket statuses: To Do → In Progress → Ready to Publish / Issues on EF side / Issues on Agg side → Done.

### 12.3 Search Tips

**Production API:** `https://api.europeana.eu/`
**Preview API:** `https://metis-preview-api-prod.eanadev.org/`
**Preview portal:** `https://metis-preview-portal.eanadev.org/en`

**Useful queries:**
- Content/metadata tiers: `edm_datasetName:08604* contentTier:2 AND metadataTier:B`
- By agent: `who:Vermeer`; `who:Rembrandt OR who:Vermeer`
- By year: `YEAR:1910`; `YEAR:[1525 TO 1527]`
- By file type: `provider_aggregation_edm_isShownBy:*.wmv*`
- IIIF items: `sv_dcterms_conformsTo:*iiif*`
- By data provider with media: `has_media:* AND DATA_PROVIDER:"The British Library"`
- By timestamp: `timestamp_created:[2016-01-01T00:00:0.000Z TO 2016-08-28T00:00:00.000Z]`

### 12.4 Usage Statistics Dashboard

Available via Europeana Welcome Pack. Two databoards: institution-specific (visits, time, bounce rate, page views) and Europeana-wide (visitors, downloads, click-throughs, visits by country/channel). Powered by Matomo; dashboard via Databox.

### 12.5 Training Guidelines

Standardised development process: Pre-alpha → Alpha (internal, 3-10 testers) → Beta (external testing) → V1 Public (accessibility: WCAG 2.1 Level AA) → V2/V3 (translations). Delivery methodology: Relate-Tell-Show-Do-Review. Scaling: train the trainer, translation/localisation, extending learning pathways.

---

## 13. Key Contacts and Resources

- **Service Desk:** `https://europeana.atlassian.net/servicedesk/customer/portal/5`
- **API registration:** `https://pro.europeana.eu/pages/get-api`
- **API support:** `api@europeana.eu`; Google Group
- **EDM XML Schema:** `http://www.europeana.eu/schemas/edm/EDM.xsd`
- **GitHub (Metis schema):** `europeana/metis-schema`
- **GitHub (vocabularies):** `europeana/metis-vocabularies`
- **FTP bulk data:** `ftp://download.europeana.eu/dataset/`
- **SPARQL endpoint:** `https://sparql.europeana.eu/`
- **Metis Sandbox:** `https://metis-sandbox.europeana.eu/`
- **IIIF manifests:** `https://iiif.europeana.eu/presentation/{DATASET}/{LOCAL}/manifest`