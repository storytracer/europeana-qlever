---
language:
- multilingual
license: apache-2.0
tags:
- europeana
- cultural-heritage
- linked-data
- edm
- sparql
- parquet
pretty_name: Europeana Items (Enriched)
size_categories:
- 10M<n<100M
source_datasets:
- Europeana Data Exchange Agreement
task_categories:
- text-classification
- feature-extraction
---

# Europeana Items (Enriched)

Denormalized export of ~66 million cultural heritage item records from [Europeana](https://www.europeana.eu/), the EU's digital platform for cultural heritage. Each row is one item (painting, photograph, book, sound recording, video, 3D object, etc.) with resolved multilingual metadata.

## Source

Built from the full Europeana EDM (Europeana Data Model) Turtle dump using [europeana-qlever](https://github.com/europeana/europeana-qlever): a pipeline that indexes ~2-5 billion RDF triples into a QLever SPARQL engine, exports flat component tables, and composes them into this denormalized Parquet file via DuckDB.

The upstream data is published by Europeana under the [Europeana Data Exchange Agreement](https://www.europeana.eu/en/rights/data-exchange-agreement). Individual item rights vary per record (see the `rights` column).

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `item` | `VARCHAR` | Europeana item URI (`http://data.europeana.eu/item/...`) |
| `titles` | `LIST<STRUCT<value, lang>>` | All `dc:title` values with ISO 639 language tags |
| `descriptions` | `LIST<STRUCT<value, lang>>` | All `dc:description` values with language tags |
| `creators` | `LIST<STRUCT<name, uri>>` | Creator display names resolved from `edm:Agent` entities. `uri` is the agent entity URI (or NULL for literal-only creators) |
| `subjects` | `LIST<STRUCT<label, uri>>` | Subject terms resolved from `skos:Concept` entities. `uri` is the concept URI (NULL for literal subjects) |
| `dates` | `LIST<VARCHAR>` | `dc:date` values (free-text, not normalized) |
| `years` | `LIST<VARCHAR>` | Normalized `edm:year` values from Europeana enrichment |
| `languages` | `LIST<VARCHAR>` | `dc:language` codes |
| `type` | `VARCHAR` | `edm:type`: TEXT, IMAGE, SOUND, VIDEO, or 3D |
| `country` | `VARCHAR` | Country of the providing institution |
| `institution` | `VARCHAR` | Name of the institution that provided the metadata (`edm:dataProvider`) |
| `aggregator` | `VARCHAR` | Name of the aggregator supplying data to Europeana (`edm:provider`) |
| `rights` | `VARCHAR` | Rights statement URI (Creative Commons, Rights Statements, etc.) |
| `completeness` | `VARCHAR` | Europeana metadata completeness score (1-10) |
| `is_shown_at` | `VARCHAR` | URL where the item can be viewed on the institution's site |
| `is_shown_by` | `VARCHAR` | Direct URL to the digital object (image, PDF, etc.) |
| `preview` | `VARCHAR` | Thumbnail URL |
| `landing_page` | `VARCHAR` | Europeana landing page URL |
| `dataset_name` | `VARCHAR` | Europeana dataset identifier |

## Usage

```python
import duckdb

db = duckdb.connect()

# Basic stats
db.sql("SELECT type, COUNT(*) FROM 'items_enriched.parquet' GROUP BY type ORDER BY 2 DESC").show()

# Unnest creators
db.sql("""
    SELECT item, c.name, c.uri
    FROM 'items_enriched.parquet', UNNEST(creators) AS c
    LIMIT 10
""").show()

# Filter openly licensed images from a specific country
db.sql("""
    SELECT item, titles, creators, rights
    FROM 'items_enriched.parquet'
    WHERE type = 'IMAGE'
      AND country = 'Netherlands'
      AND rights LIKE '%/publicdomain/%'
    LIMIT 100
""").show()
```

```python
import pandas as pd

df = pd.read_parquet("items_enriched.parquet")
```

## Limitations

- **Snapshot**: This is a point-in-time export. Europeana refreshes its data weekly; this file is not automatically updated.
- **Metadata only**: This dataset contains metadata records, not the digital objects themselves. Use `is_shown_by` or `is_shown_at` URLs to access the actual media.
- **Multilingual**: Titles and descriptions may be in any language. The `lang` field in the struct carries the ISO 639 tag when available, but some values have no language tag.
- **Completeness varies**: Not all fields are populated for every record. The `completeness` score (1-10) indicates overall metadata quality.

## Generation

```bash
pip install europeana-qlever
europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL
# or just the enriched export:
europeana-qlever -d /data/europeana export -q items_enriched
```

See the [europeana-qlever README](https://github.com/europeana/europeana-qlever) for full pipeline documentation.
