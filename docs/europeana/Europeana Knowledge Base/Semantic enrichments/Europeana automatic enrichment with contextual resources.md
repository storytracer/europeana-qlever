---
tags:
  - '#metadata'
  - '#enrichment'
---

# Europeana automatic enrichment with contextual resources

- [Introduction](#introduction)
- [Why is semantic enrichment important?](#why-is-semantic-enrichment-important)
- [Where is semantic enrichment applied?](#where-is-semantic-enrichment-applied)
- [Semantic enrichment - cases](#semantic-enrichment-cases)
  - [Text labels based matching](#text-labels-based-matching)
    - [Case 1: Plain literal enrichment](#case-1-plain-literal-enrichment)
  - [URI (co-)references based matching](#uri-co-references-based-matching)
    - [Case 2: Coreference enrichment](#case-2-coreference-enrichment)
    - [Case 3: Using coreferences in entity data](#case-3-using-coreferences-in-entity-data)
- [Credits and edit history](#credits-and-edit-history)

# Introduction

As part of the aggregation process, Europeana automatically enriches metadata by matching provided values to contextual resources from the Europeana Entity Collection. This process, known as automatic semantic enrichment, enhances records by adding additional information beyond the original data.

> [!IMPORTANT]
> **What is the Europeana entity collection?**
>
> It is a curated reference point that aggregates information from several controlled vocabularies such as Wikidata, Geonames, AAT, VIAF and others.

The enrichment process can be summarised into two main steps:

1. Values of provided metadata fields are automatically matched to Europeana contextual entities and links to these resources are added to metadata. The matching process follows predefined rules that determine how a provided metadata value corresponds to a specific contextual entity.
2. Added links point to data from the Europeana entity collection. Each linked Europeana entity is an instance of a contextual class as defined in the EDM for representing people (edm:Agent), places (edm:Place), concepts (skos:Concept), time periods (edm:Timespan) or organisations (foaf:Organization). Data available for the specific entity  includes multilingual synonyms of an enriched term, hierarchical relationships (broader concepts) and links to equivalent entities in other vocabularies.

<details>
<summary>Example: Enrichment with the Europeana entity for wig</summary>

The following example demonstrates how semantic enrichment is applied to a record containing the term *wig* in dc:subject. Based on predefined rules, the provided subject is linked to the Europeana entity for *wig*. The link to the Europeana *wig* entity is stored in Europeana’s proxy class, ensuring that enrichment remains separate from the source metadata in the provider’s proxy class. Additionally, a contextual entity is created as an instance of the appropriate contextual  class defined in the Europeana Data Model (EDM), in this case skos:Concept, which holds additional metadata associated with the *wig* entity, such as translated labels, hierarchical relationships and references to other (external) vocabularies.

**Before**

```java
<edm:ProvidedCHO rdf:about="...">
...
  <dc:subject xml:lang="en">Wig</dc:subject>
...
</edm:ProvidedCHO>
```

**After**

```java
<ore:Proxy rdf:about="...">
...
  <edm:europeanaProxy>true</edm:europeanaProxy>
  <dc:subject rdf:resource="http://data.europeana.eu/concept/2712"/>
...
</ore:Proxy>

<skos:Concept rdf:about="http://data.europeana.eu/concept/2712">
  <skos:prefLabel xml:lang="en">Wig</skos:prefLabel>
  <skos:prefLabel xml:lang="de">Perücke</skos:prefLabel>
  <skos:prefLabel xml:lang="el">περούκα</skos:prefLabel>
  <skos:prefLabel xml:lang="sl">Lasulja</skos:prefLabel>
  <skos:broader rdf:resource="http://data.europeana.eu/concept/2381"/>
  <skos:broader rdf:resource="http://data.europeana.eu/concept/2397"/>
  <skos:exactMatch rdf:resource="http://www.wikidata.org/entity/Q105507"/>
  <skos:exactMatch rdf:resource="http://vocab.getty.edu/aat/300046049"/>
  <skos:exactMatch rdf:resource="http://thesaurus.europeanafashion.eu/thesaurus/10186"/>
...
</skos:Concept>
```

Providers should note that for organisations, the enrichment process differs slightly. After finding a match, the source value is replaced with the corresponding Europeana entity for the organisation instead of being retained. More details on this process can be found [here](https://europeana.atlassian.net/wiki/x/AYDeiw?atlOrigin=eyJpIjoiMjY5ZTU1NGMyOTFmNDJkN2E1MDAwMmU0YmJmZGMyZTYiLCJwIjoiYyJ9).

</details>

# Why is semantic enrichment important?

The primary goal of semantic enrichment is to enhance the interlinking of the data, adding more context to provided objects and improving the user experience in the Europeana portal by offering additional ways to search and navigate collections.

- **Enhanced exploration**

Semantic enrichment creates connections between provided objects and contextual entities, enabling users to explore relationships between them. For example, if a cultural heritage object in Europeana is attributed to Claude Monet, users can discover it through Monet’s entity page or navigate from the object’s page to learn more about Monet and related works. Similarly, a user searching for *Impressionism* can access a collection of objects linked to the movement, including artworks by associated artists like Monet.

- **Expanded multilinguality**

Through enrichment, multilingual terms are added to records, allowing Europeana to adapt to the language of the user. Since most entities have labels in multiple languages, the Europeana website displays the label that best matches the user’s preferred language.

- **Improved findability**

Enrichments can improve search recall and precision by adding more searchable content to records. This enables users to find records even if their search term does not exactly match the original metadata. For instance, if a provided object lists its creator as *Raffaello Sanzi*o in the source data, enrichment can link it to his more widely recognised name, *Raphael*, ensuring that searches for either name return relevant results. Entities with multilingual labels also aid cross-lingual retrieval by allowing users to search in their preferred language while still retrieving relevant records. For example, a French user searching for *Londres* (London) will also find records tagged with the English equivalent, *London*, broadening access across different languages.

- **Contextualisation and disambiguation of terms**

Enrichments add contextual information to provided objects, helping eliminate ambiguity and can, for example, reduce confusion caused by terms that have multiple meanings (polysemy). For example, the term *Paris* could refer to the capital of France or Paris, a character from Greek mythology. By linking terms to Europeana entities, we ensure that Paris (city) is distinct from Paris (mythological figure).

# Where is semantic enrichment applied?

The enrichment process links values in the source metadata fields to target fields of Europeana entities:

- **Source fields** are the metadata fields that describe the provided cultural heritage object, for example, the creator’s name, place of creation, subjects, etc. These fields are used to find a corresponding contextual entity.
- **Target fields** are fields in an external dataset (in our case, this is Europeana entity collection) that contain structured information about entities.

The process of matching source and target fields follows predefined rules that determine when a source field value corresponds to a target field value. To reduce errors and ensure contextually relevant enrichments, Europeana applies the following rules:

- Case insensitivity: matches are found regardless of letter casing, so *paris* and *Paris* are treated as the same value.
- Consideration of language tags: When language tags are present in the source fields, the system prioritises matches where both the source and target fields share the same value and language tag. If no language tags are available, matching solely relies on the text label within the field.
- Field-specific enrichment rules: certain metadata fields can only be enriched with a specific type of entity. For example, a *creator* field can only be linked to an entity classified as an Agent (edm:Agent) rather than a place or concept.
- Multiple entity enrichment: matches are established based on direct equivalence, meaning identical values in both fields. However, matches can sometimes go beyond a direct one-to-one match by accounting for hierarchical relationships. For instance, a term may be linked to both its specific entity and a broader entity within the same hierarchy, such as a city being enriched with both its specific entity and the entity for the country it belongs to.

The following table lists source and target fields for different Europeana entity types:

|  Entity type     |  Source fields                                                                                                                                                                                                |  Target fields                                         |
|:-----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------|
| **Agent**        | *In edm:ProvidedCHO class:* <br/> dc:creator, <br/> dc:contributor. <br/>  <br/> *In (provided or dereferenced) edm:Agent contextual class:* <br/> owl:sameAs.                                                | skos:prefLabel, <br/> skos:altLabel <br/> owl:sameAs.  |
| **Place**        | *In edm:ProvidedCHO class:* <br/> dcterms:spatial, <br/> dc:coverage. <br/>  <br/> *In (provided or dereferenced) edm:Place contextual class:* <br/> owl:sameAs.                                              | skos:prefLabel, <br/> skos:altLabel, <br/> owl:sameAs. |
| **Time Periods** | *In edm:ProvidedCHO class:* <br/> dc:date, <br/> dcterms:temporal, <br/> dcterms:created, <br/> dcterms:issued. <br/>  <br/> *In (provided or dereferenced) edm:TimeSpan contextual class:* <br/> owl:sameAs. | skos:prefLabel, <br/> skos:altLabel, <br/> owl:sameAs. |
| **Concept**      | *In edm:ProvidedCHO class:* <br/> dc:subject, <br/> dc:type, <br/> dc:format, <br/> dcterms:medium. <br/>  <br/> *In (provided or dereferenced) skos:Concept contextual class:* <br/> skos:exactMatch.        | skos:prefLabel, <br/> skos:exactMatch.                 |

# Semantic enrichment - cases

Building on the concepts of source and target fields discussed in the previous section, the following cases illustrate how matches are established between the source metadata and Europeana entities during the enrichment process. Each case highlights the specific matching mechanism applied, whether based on textual labels or co-references (URIs) and provides examples to clarify how the process works in practice.

They fare categorised into two groups: **matching based on text labels** and **matching based on URI (co-)references**, which together describe the diverse ways in which metadata can be enriched by Europeana:

## Text labels based matching

### **Case 1: Plain literal enrichment**

When the source field describing the cultural heritage object contains a textual value (literal), the process attempts to find a corresponding Europeana entity with the same text in one of the target fields (skos:prefLabel or skos:altLabel).

Example:

|                                                                                                                                                                                                     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *Before* <br/> ```java<br/><edm:ProvidedCHO rdf:about="..."><br/>...<br/>  <dc:creator xml:lang=”en”>Pablo Picasso</dc:creator><br/>...<br/></edm:ProvidedCHO><br/>```   <br/>  <br/>  <br/>  <br/> | *After* <br/> ```java<br/><ore:Proxy rdf:about="..."><br/>...<br/>  <edm:europeanaProxy>true</edm:europeanaProxy><br/>  <dc:creator rdf:resource="http://data.europeana.eu/agent/60206"/><br/>...<br/></ore:Proxy><br/><br/><br/><edm:Agent rdf:about="http://data.europeana.eu/agent/60206"><br/>...<br/>  <skos:prefLabel xml:lang="en">Pablo Picasso</skos:prefLabel><br/>  <skos:exactMatch rdf:resource="http://www.wikidata.org/entity/Q5593"/><br/>...<br/></edm:Agent><br/>``` |

## **URI (co-)references based matching**

### **Case 2: Coreference enrichment**

When the source field describing the cultural heritage object contains a reference (URI), the process attempts to find a corresponding contextual entity with the same URI in one of the target fields (owl:sameAs or skos:exactMatch).

Example:

|                                                                                                                                                                                     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *Before* <br/> ```java<br/><edm:ProvidedCHO rdf:about="..."><br/>...<br/>  <dc:subject rdf:resource=”http://vocab.getty.edu/aat/300055920”/><br/>...<br/></edm:ProvidedCHO><br/>``` | *After* <br/> ```java<br/><ore:Proxy rdf:about="..."><br/>...<br/>  <edm:europeanaProxy>true</edm:europeanaProxy><br/>  <dc:subject rdf:resource="http://data.europeana.eu/concept/123"/><br/>...<br/></ore:Proxy><br/><br/><br/><skos:Concept rdf:about="http://data.europeana.eu/concept/123"><br/>...<br/>  <skos:prefLabel xml:lang="en">Folklore</skos:prefLabel><br/>  <skos:exactMatch rdf:resource="http://vocab.getty.edu/aat/300055920"/><br/>...<br/></skos:Concept><br/>``` |

> [!IMPORTANT]
> Providers should note it is irrelevant whether the URI is dereferenceable or not.

### **Case 3: Using coreferences in entity data**

This scenario applies to co-references (URIs) within a given contextual entity, which can either be a contextual class supplied by the data provider in the original EDM record or created by Europeana when a dereferenceable URI is supplied. The process attempts to find a match by comparing a reference (URI) in owl:sameAs or skos:exactMatch of either the provided or dereferenced contextual class with an identical URI in owl:sameAs or skos:exactMatch of the Europeana entity.

Example:

|                                                                                                                                                                                                                                                                                                                                      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *Before* <br/> ```java<br/><edm:ProvidedCHO rdf:about="..."><br/>...<br/>  <dc:subject rdf:resource=”#Concept_abcd”/><br/>...<br/></edm:ProvidedCHO><br/><br/><br/><skos:Concept rdf:about="#Concept_abcd"><br/>...<br/>  <skos:exactMatch rdf:resource="http://vocab.getty.edu/aat/300055920"/><br/>...<br/></skos:Concept><br/>``` | *After* <br/> ```java<br/><ore:Proxy rdf:about="..."><br/>...<br/>  <edm:europeanaProxy>true</edm:europeanaProxy><br/>  <dc:subject rdf:resource="http://data.europeana.eu/concept/123"/><br/>...<br/></ore:Proxy><br/><br/><br/><skos:Concept rdf:about="http://data.europeana.eu/concept/123"><br/>...<br/>  <skos:prefLabel xml:lang="en">Folklore</skos:prefLabel><br/>  <skos:exactMatch rdf:resource="http://vocab.getty.edu/aat/300055920"/><br/>...<br/></skos:Concept><br/>``` |

# Credits and edit history

- 2025-03-20 documentation updated by Maša Škrinjar in collaboration with Hugo Manguinhas
- 2025-03-26 final page edits by Adina Ciocoiu
