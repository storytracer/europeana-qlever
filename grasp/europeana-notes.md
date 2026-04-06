# Europeana SPARQL Guide

## The Proxy-Aggregation Model

Metadata is NOT on the item directly. It flows through proxies and aggregations.

Each item has two proxies. The **provider proxy** has the original descriptive metadata:
```sparql
?proxy ore:proxyFor ?item .
FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" . }
?proxy dc:title ?title .
```

The **Europeana proxy** has normalised fields (edm:type, edm:year):
```sparql
?eProxy ore:proxyFor ?item .
?eProxy edm:europeanaProxy "true" .
?eProxy edm:type ?type .
```

The **aggregation** has rights, provider info, and URLs:
```sparql
?agg edm:aggregatedCHO ?item .
?agg edm:rights ?rights .
?agg edm:dataProvider ?dataProvider .
```

The **Europeana aggregation** has country and completeness:
```sparql
?eAgg edm:aggregatedCHO ?item .
?eAgg a edm:EuropeanaAggregation .
?eAgg edm:country ?country .
```

## Where properties live

- **Provider proxy** (`?proxy`): dc:title, dc:description, dc:creator, dc:contributor, dc:publisher, dc:subject, dc:date, dc:language, dc:identifier, dc:format, dc:rights, dc:source, dc:type, dcterms:spatial, dcterms:temporal
- **Europeana proxy** (`?eProxy`): edm:type, edm:year
- **Aggregation** (`?agg`): edm:rights, edm:dataProvider, edm:provider, edm:isShownAt, edm:isShownBy
- **Europeana aggregation** (`?eAgg`): edm:country, edm:completeness

## Key facts

- `edm:type` is a string literal: `"IMAGE"`, `"TEXT"`, `"SOUND"`, `"VIDEO"`, or `"3D"`
- `edm:rights` is a URI (e.g. `<http://creativecommons.org/licenses/by/4.0/>`)
- `edm:dataProvider` and `edm:country` are literal strings
- Entity URIs (agents, concepts, places) appear as objects of dc:creator, dc:subject, etc. on the provider proxy
- Entities have `skos:prefLabel` with language tags
- Always COUNT DISTINCT `?item` — items have multiple proxies and links
