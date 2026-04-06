---
tags:
  - '#metadata'
  - '#framework'
  - '#quality'
  - '#edm'
  - '#tiers'
  - '#epf'
---

# Metadata Tier B

**Metadata Tier B (Europeana website as an exploration platform)**

If you want to increase the visibility of your content through our thematic collections and other browse entry points, at least 50% of the provided metadata elements that are relevant need to have at least one language tag. The metadata should now include at least three enabling elements covering at least two distinct discovery and user scenarios and one contextual class with all minimum required elements or link to LOD vocabulary (also with all minimum required elements).

- [Language](#language)
- [Enabling elements](#enabling-elements)
- [Contextual classess](#contextual-classess)
- [Example record](#example-record)

## **Language**

At **least 50% of the metadata elements** from **ProvidedCHO** that are relevant have **at least one language qualified value.**

**Metadata elements in ProvidedCHO**

<details>
<summary>Metadata elements in ProvidedCHO</summary>

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
- dcterms:isReferencedBy
- dcterms:medium
- dcterms:provenance
- dcterms:references
- dcterms:spatial
- dcterms:tableOfContents
- dcterms:temporal
- edm:currentLocation
- edm:hasType
- edm:isRelatedTo

</details>

## **Enabling elements**

At least **three distinct metadata elements** taken from **two distinct ‘Discovery scenario’ groups** present in the edm:P**rovidedCHO** class

|                              |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|:-----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Discovery scenarios**      | **Enabling elements**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Browse by date or time-span  | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)l, [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to an [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) that is present in the record)                                                                                                                                                                                                                                           |
| Browse by subjects and types | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md)), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)                                                                                                                                                                                                                                                                           |
| Browse by agents             | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) that is present in the record), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) that is present in the record) |
| Browse by places             | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md) that is present in the record), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)                                                                                                                                                                                                                                                                                                                                                       |

## **Contextual classess**

At least **one contextual class** with all minimum required elements, OR link to a [LOD vocabulary we support.](https://pro.europeana.eu/page/europeana-semantic-enrichment#enrich-your-own-metadata)

**Contextual resource referred by the ProvidedCHO:** A contextual entity (an instance of a contextual class such as edm:Agent, skos:Concept, edm:Place, edm:TimeSpan) that is **linked directly** from edm:ProvidedCHO (ie. Provider's ore:Proxy) and therefore ignoring contextual resources that are only linked from other contextual resources via e.g. placeOfBirth.

|                                                                                                    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|:---------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Contextual classess**                                                                            | **Minimum required metadata elements per contextual class**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| [edm:TimeSpan](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_TimeSpan.md) | [edm:TimeSpan](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_TimeSpan.md) AND [edm:TimeSpan](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_TimeSpan.md)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| [edm:TimeSpan](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_TimeSpan.md) | [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) AND ([skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) OR [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) OR [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) OR [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) OR [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) OR [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md))                                                       |
| [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md)       | [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) AND ([edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) OR [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) OR [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) OR [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) OR [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) OR [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) OR [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md)) |
| [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md)       | [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md) AND [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md) AND [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

## Example record

```java
 <rdf:RDF>
 ...
 <edm:ProvidedCHO rdf:about="#exampleMetB">
        <dc:title xml:lang="en">Metadata Example Record Tier B</dc:title>
        <dc:subject rdf:resource="http://vocab.getty.edu/aat/300026657"/>
        <dc:type>Bound item</dc:type>
        <dcterms:created>1951</dcterms:created>
        <dcterms:isPartOf>Europeana Foundation Example Records</dcterms:isPartOf>
        <edm:type>IMAGE</edm:type>
    </edm:ProvidedCHO>
    <ore:Aggregation rdf:about="#exampleMetB_AGG">
        <edm:aggregatedCHO rdf:resource="#exampleMetB"/>
        <edm:dataProvider>Europeana Foundation</edm:dataProvider>
        <edm:isShownBy rdf:resource="http://media.culturegrid.org.uk/mediaLibrary/Partage/LoveArtNouveau/Glasgow/DSCF4092.JPG"/>
        <edm:provider>Europeana Foundation</edm:provider> 
        <edm:rights rdf:resource="http://rightsstatements.org/vocab/NoC-OKLR/1.0/"/>
    </ore:Aggregation>
</rdf:RDF>
```

For more details, see page [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .
