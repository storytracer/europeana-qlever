---
tags:
  - '#organisation-entities'
  - '#enrichment'
---

[Semantic enrichments](../Semantic%20enrichments.md)

# Europeana automatic enrichment with organisations

This page describes how Europeana links information about providing organisations to Europeana entities for organisations.

- [Europeana organisation entities](#europeana-organisation-entities)
- [Where is semantic enrichment applied?](#where-is-semantic-enrichment-applied)
- [Semantic enrichments - cases](#semantic-enrichments-cases)
  - [Case 1: Matching based on textual values](#case-1-matching-based-on-textual-values)
  - [Case 2: Matching based on URI (co-)references](#case-2-matching-based-on-uri-co-references)

# Europeana organisation entities

Data partners include information about organisations involved in the aggregation chain in the metadata, like so:

```java
<ore:Aggregation rdf:about="#Example_01Aggregation">
        <edm:aggregatedCHO rdf:resource="#Example_01"/>
        <edm:dataProvider>Bibliothèque nationale de France</edm:dataProvider>
        <edm:intermediateProvider>The European Library</edm:intermediateProvider>
        <edm:provider>Gallica</edm:provider>
        [ other Aggregation data ]
</ore:Aggregation>
```

Organisations are recorded in the Europeana customer relationship management system (CRM), where we store the main information related to them, such as, among others, the officialname and English translation, acronym, country of location, and website. Each Europeana organisation entity contains information extracted from the CRM that is augmented with organisation data available in Wikidata. You can retrieve an entity by making the following request:

```java
https://api.europeana.eu/entity/organization/[IDENTIFIER]
Accept: [ACCEPT]
```

```java
https://api.europeana.eu/entity/organization/[IDENTIFIER].[FORMAT]
```

Example:

```java
https://api.europeana.eu/entity/organization/4373.json
```

More information about metadata included in the organisation entity is available [Entity API Documentation](../Europeana%20APIs%20Documentation/API%20Suite/Entity%20API%20Documentation.md).

# Where is semantic enrichment applied?

Semantic enrichment links values in source metadata fields to corresponding Europeana entities for organisations. This process follows a structured approach, where specific metadata fields (source fields) are matched against predefined reference points (target fields) to establish meaningful connections. The enrichment process adheres to a set of rules that define how matches are determined, ensuring consistency and reliability.

|  **Contextual Entity Type**    |  **Source fields**                                                 |  **Target fields**                                                                           |
|:-------------------------------|:-------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| **Organisations**              | edm:dataProvider <br/> edm:intermediateProvider <br/> edm:provider | skos:prefLabel <br/> skos:altLabel <br/> skos:hiddenLabel <br/> edm:acronym <br/> owl:sameAs |

# Semantic enrichments - cases

The following cases demonstrate how matches are established between source metadata and Europeana entity metadata for organisations. Each case outlines the specific matching mechanism used, whether based on textual values or URI (co-)references, and includes an example to illustrate the process in practice.

## Case 1: Matching based on textual values

Enrichment process looks for a textual reference (label) mapped to the source field and finds an organisation entity with the same label in the target field.

> [!IMPORTANT]
> Data partners can provide organisation names in their original language, an English translation, or acronyms, as long as these are recorded in the CRM.

***Before enrichment:***

|                                                                                                                                                                                                                                                                                                                                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ```xml<br/><ore:Aggregation rdf:about="#Example_01Aggregation"><br/>        <edm:aggregatedCHO rdf:resource="#Example_01"/><br/>        <edm:dataProvider>Bibliothèque nationale de France</edm:dataProvider><br/>        [ other Aggregation data ]<br/></ore:Aggregation><br/>```  *Source data in provided ore:Aggregation class* <br/> | ```java<br/><foaf:Organization rdf:about="http://data.europeana.eu/organization/4373"><br/>        <skos:prefLabel xml:lang="en">National Library of France</skos:prefLabel><br/>        <skos:prefLabel xml:lang="fr">Bibliothèque nationale de France</skos:prefLabel><br/>        <edm:acronym xml:lang="fr">BnF</edm:acronym><br/>        [ other information about organisation ]<br/></foaf:Organization><br/>```  *Target data in Europeana entity for organisation* <br/> |

***After enrichment:***

When a match is found, the source value is replaced with the Europeana organisation entity URI and the entity is added to the record. Each entity is an instance of a contextual class as defined in the EDM for representing organisations (foaf:Organization).

Including the foaf:Organization class in the metadata enables the use of additional contextual information while keeping it separate from the Aggregation class.

```java
<ore:Aggregation rdf:about="/aggregation/provider/Example_01Aggregation">
        <edm:aggregatedCHO rdf:resource="#Example_01"/>
        <edm:dataProvider rdf:resource="http://data.europeana.eu/organization/4373"/>
        [ other Provider’s Aggregation data ]
 </ore:Aggregation>

<foaf:Organization rdf:about="http://data.europeana.eu/organization/4373">
        <skos:prefLabel xml:lang="en">National Library of France</skos:prefLabel>
        <skos:prefLabel xml:lang="fr">Bibliothèque nationale de France</skos:prefLabel>
        [ other information about organisation ]
</foaf:Organization>
```

## Case 2: Matching based on URI (co-)references

Enrichment process looks for a URI mapped to the source field and matches it against the co-reference link (indicated by owl:sameAs relation) available for the organisation entity.

> [!IMPORTANT]
> Data partners can provide URIs from external vocabularies or persistent identifiers for organisations. We list some examples below.
>
> To ensure proper enrichment, partners should notify us about the URIs they wish to use so we can record them in our CRM.

<details>
<summary>Example URIs for National Library of France:</summary>

|                                               |                                                                |
|:----------------------------------------------|:---------------------------------------------------------------|
| **Vocabulary / PI system name**               | **Example URI**                                                |
| Wikidata                                      | ```java<br/>http://www.wikidata.org/entity/Q193563<br/>```     |
| Virtual International Authority File (VIAF)   | ```java<br/>http://viaf.org/viaf/137156173<br/>```             |
| The Getty - Union List of Artist Names (ULAN) | ```java<br/>http://vocab.getty.edu/ulan/500309981<br/>```      |
| Gemeinsame Normdatei (GND)                    | ```java<br/>https://d-nb.info/gnd/5156217-0<br/>```            |
| International Standard Name Identifier (ISNI) | ```java<br/>https://isni.org/isni/0000000123531945<br/>```     |
| Archival Resource Key (ARK)                   | ```java<br/>https://data.bnf.fr/ark:/12148/cb12381002j<br/>``` |
| The Research Organization Registry (ROR)      | ```java<br/>https://ror.org/04v1bf639<br/>```                  |

</details>

***Before enrichment:***

|                                                                                                                                                                                                                                                                                                                                                                           |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ```java<br/><ore:Aggregation rdf:about="#Example_02Aggregation"><br/>        <edm:aggregatedCHO rdf:resource="#Example_02"/><br/>        <edm:dataProvider rdf:resource="https://data.bnf.fr/ark:/12148/cb12381002j"/><br/>        [ other Aggregation data ]<br/> </ore:Aggregation><br/>```  *Source data in provided ore:Aggregation class* <br/>  <br/>  <br/>  <br/> | ```java<br/><foaf:Organization rdf:about="http://data.europeana.eu/organization/4373"><br/>        <skos:prefLabel xml:lang="en">National Library of France</skos:prefLabel><br/>        <skos:prefLabel xml:lang="fr">Bibliothèque nationale de France</skos:prefLabel><br/>        <edm:acronym xml:lang="fr">BnF</edm:acronym><br/>        <owl:sameAs rdf:resource="http://www.wikidata.org/entity/Q193563"/><br/>        <owl:sameAs rdf:resource="http://viaf.org/viaf/137156173"/><br/>        <owl:sameAs rdf:resource="https://data.bnf.fr/ark:/12148/cb12381002j"/><br/>        [ other information about organisation ]<br/></foaf:Organization><br/>```  *Target data in Europeana entity for organisation* <br/> |

***After enrichment:***

When a match is found, the source value is replaced with the Europeana organisation entity URI and the entity is added to the record as foaf:Organization contextual class.

```java
 <ore:Aggregation rdf:about="/aggregation/provider/Example_02Aggregation">
        <edm:aggregatedCHO rdf:resource="#Example_02"/>
        <edm:dataProvider rdf:resource="http://data.europeana.eu/organization/4373"/>
        [ other Provider’s Aggregation data ]
 </ore:Aggregation>

<foaf:Organization rdf:about="http://data.europeana.eu/organization/4373">
        <skos:prefLabel xml:lang="en">National Library of France</skos:prefLabel>
        <skos:prefLabel xml:lang="fr">Bibliothèque nationale de France</skos:prefLabel>
        [ other properties of Organization entity]
</foaf:Organization>
```
