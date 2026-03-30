---
tags:
  - '#edm'
  - '#quality'
  - '#framework'
  - '#tiers'
  - '#epf'
  - '#metadata'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier A-C requirements](../Tier%20A-C%20requirements.md)

# Metadata Tier C

**Metadata Tier C (Europeana website as a knowledge platform)**

To offer users the best possible experience when working with your collections online, at least 75% of your metadata elements that are relevant need to have at least 1 language tag. The metadata should include at least three distinct enabling elements covering at least two distinct discovery and user scenarios and two distinct contextual classes with all minimum required elements or links to LOD vocabularies (also with all minimum required elements).

- [Language](#language)
- [Enabling elements](#enabling-elements)
- [Contextual classess](#contextual-classess)
- [Example record](#example-record)

## **Language**

At least **75% of the metadata elements** from ProvidedCHO that are relevant have **at least one language qualified value**

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

At least **four distinct metadata elements** taken from two distinct ‘Discovery scenario’ groups present in the **edm:ProvidedCHO** class

|                              |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|:-----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Discovery scenarios**      | **Enabling elements**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Browse by date or time-span  | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)l, [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to an [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) that is present in the record)                                                                                                                                                                                                                                           |
| Browse by subjects and types | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [skos:Concept](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md)), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)                                                                                                                                                                                                                                                                           |
| Browse by agents             | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) that is present in the record), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Agent](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) that is present in the record) |
| Browse by places             | [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) (with a link to a [edm:Place](../../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md) that is present in the record), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](../../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md)                                                                                                                                                                                                                                                                                                                                                       |

## **Contextual classess**

At least **two contextual class** with all minimum required elements, OR link to a [LOD vocabulary we support.](https://pro.europeana.eu/page/europeana-semantic-enrichment#enrich-your-own-metadata)

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
 <edm:ProvidedCHO rdf:about="#exampleMetC">
        <dc:title xml:lang="en">Metadata Example Record Tier C</dc:title>
        <dc:type xml:lang="en">Periodical</dc:type>
        <dc:format>Bound item</dc:format>
        <dc:subject rdf:resource="http://vocab.getty.edu/aat/300411614"/>
        <dc:language>deu</dc:language>
        <edm:currentLocation rdf:resource="http://www.wikidata.org/entity/Q90"/>
        <dcterms:isPartOf xml:lang="en">Europeana Foundation Example Records</dcterms:isPartOf>
        <edm:type>TEXT</edm:type>
    </edm:ProvidedCHO>
    <ore:Aggregation rdf:about="#exampleMetC_AGG">
        <edm:aggregatedCHO rdf:resource="#exampleMetC"/>
        <edm:dataProvider>Europeana Foundation</edm:dataProvider>
        <edm:isShownBy rdf:resource="http://media.culturegrid.org.uk/mediaLibrary/Partage/LoveArtNouveau/Glasgow/DSCF4092.JPG"/>
        <edm:provider>Europeana Foundation</edm:provider>
        <edm:rights rdf:resource="http://rightsstatements.org/vocab/NoC-OKLR/1.0/"/>
    </ore:Aggregation>
</rdf:RDF>
```

For more details, see page [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .
