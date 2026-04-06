---
tags:
  - '#quality'
  - '#framework'
  - '#edm'
  - '#metadata'
  - '#tiers'
  - '#epf'
---

# Metadata Tier A

**Metadata Tier A (Europeana website as a basic search platform)**

The criteria for Metadata Tier A define the minimum requirements for records to be findable in the Europeana website. To make your collections more visible, at least 25% of the metadata elements that have been provided and are relevant, need to have at least one language tag. Additionally, the metadata should include at least one of the enabling elements taken from the Discovery and User scenarios.

- [Language](#language)
- [Enabling Elements](#enabling-elements)
- [Contextul classes](#contextul-classes)
- [Example record](#example-record)

## **Language**

 At least **25% of the metadata elements** from **ProvidedCHO** that are relevant have at least **one language qualified value**.  At least one of the following is true:

(1*) a literal value (ie. String) that is language qualified (ie. xml:lang);*

(2) *a link (i.e. URI) to a contextual entity (only edm:Place, skos:Concept and edm:TimeSpan)*

that is present in the record and has **at least one language qualified skos:prefLabel** (multiple occurrences are ignored once one language qualified value is found).

**Metadata elements in edm:ProvidedCHO**

<details>
<summary>Metadata elements in edm:ProvidedCHO</summary>

- dc:coverage
- dc:description
- dc:format
- dc:relation
- dc:rights
- dc:source
- dc:subject
- dc:title
- dc:type
- dcterms:alternative
- dcterms:hasPart
- dcterms:isPartOf
- dcterms:isReferencedBy,
- dcterms:medium
- dcterms:provenance
- dcterms:references
- dcterms:spatial
- dcterms:tableOfContents
- dcterms:temporal
- edm:currentLocation
- edm:hasType,
- edm:isRelatedTo

</details>

## **Enabling Elements**

At least **one** metadata element from one of the ‘Discovery scenario’ groups present in the **edm:ProvidedCHO class**

|                              |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|:-----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Discovery scenarios**      | **Enabling elements**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Browse by date or time-span  | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)l, [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to an [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) that is present in the record)                                                                                                                                                                                                                                           |
| Browse by subjects and types | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md)), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)                                                                                                                                                                                                                                                                           |
| Browse by agents             | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) that is present in the record), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) that is present in the record) |
| Browse by places             | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md) that is present in the record), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)                                                                                                                                                                                                                                                                                                                                                       |

## Contextul classes

None is required for Metadata Tier:A

## Example record

```java
<rdf:RDF>
......
    <edm:ProvidedCHO rdf:about="#exampleMetA">
        <dc:title xml:lang="en">Metadata Example Record Tier A</dc:title>
        <dc:type>book</dc:type>
        <dc:language>deu</dc:language>
        <edm:type>TEXT</edm:type>
        <dcterms:isPartOf>Europeana Foundation Example Records</dcterms:isPartOf>
    </edm:ProvidedCHO>
    <ore:Aggregation rdf:about="#exampleMetA_AGG">
        <edm:aggregatedCHO rdf:resource="ark:/12148/bpt6k4773206h"/>
        <edm:dataProvider>Europeana Foundation</edm:dataProvider>
        <edm:isShownBy rdf:resource="http://media.culturegrid.org.uk/mediaLibrary/Partage/LoveArtNouveau/Glasgow/DSCF4092.JPG"/>
        <edm:provider>Europeana Foundation</edm:provider>
        <edm:rights rdf:resource="http://rightsstatements.org/vocab/NoC-OKLR/1.0/"/>
    </ore:Aggregation>
</rdf:RDF>
```

For more details, see page [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .
