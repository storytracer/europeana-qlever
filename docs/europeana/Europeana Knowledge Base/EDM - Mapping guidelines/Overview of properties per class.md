---
tags:
  - '#edm-properties'
  - '#edm-classes'
  - '#edm-contextual-classes'
  - '#edm-core-classes'
---

[EDM - Mapping guidelines](../EDM%20-%20Mapping%20guidelines.md)

# Overview of properties per class

- [Core Clasess](#core-clasess)
  - [Properties of edm:ProvidedCHO](#properties-of-edm-providedcho)
  - [Properties for ore:Aggregation](#properties-for-ore-aggregation)
  - [Properties for edm:WebResource](#properties-for-edm-webresource)
- [Contextual Classes](#contextual-classes)
  - [Properties for edm:Agent](#properties-for-edm-agent)
  - [Properties for edm:Place](#properties-for-edm-place)
  - [Properties for edm:TimeSpan](#properties-for-edm-timespan)
  - [Properties for skos:Concept](#properties-for-skos-concept)
  - [Properties for cc:License](#properties-for-cc-license)

## **Core Clasess**

### **Properties of edm:ProvidedCHO**

<details>
<summary>Properties of edm:ProvidedCHO class</summary>

|                          |                                                                                                  |
|:-------------------------|:-------------------------------------------------------------------------------------------------|
| **dc:contributor**       | **recommended property**                                                                         |
| dc:coverage              | optional property                                                                                |
| **dc:creator**           | **recommended property**                                                                         |
| **dc:date**              | **recommended property**                                                                         |
| **dc:description**       | **at least one of the blue properties should be present (and can be used alongside each other)** |
| dc:format                | optional property                                                                                |
| **dc:identifier**        | **recommended property**                                                                         |
| **dc:language**          | **mandatory property, if edm:type=TEXT**                                                         |
| **dc:publisher**         | **recommended property**                                                                         |
| dc:relation              | optional property                                                                                |
| dc:rights                | optional property                                                                                |
| **dc:source**            | **recommended property**                                                                         |
| **dc:subject**           | **at least one of the red properties should be present (and can be used alongside each other)**  |
| **dc:title**             | **at least one of the blue properties should be present (and can be used alongside each other)** |
| **dc:type**              | **at least one of the red properties should be present (and can be used alongside each other)**  |
| **dcterms:alternative**  | **recommended property**                                                                         |
| dcterms:conformsTo       | optional property                                                                                |
| **dcterms:created**      | **recommended property**                                                                         |
| dcterms:extent           | optional property                                                                                |
| dcterms:hasFormat        | optional property                                                                                |
| dcterms:hasPart          | optional property                                                                                |
| dcterms:hasVersion       | optional property                                                                                |
| dcterms:isFormatOf       | optional property                                                                                |
| **dcterms:isPartOf**     | recommended property                                                                             |
| dcterms:isReferencedBy   | optional property                                                                                |
| dcterms:isReplacedBy     | optional property                                                                                |
| dcterms:isRequiredBy     | optional property                                                                                |
| **dcterms:issued**       | **recommended property**                                                                         |
| dcterms:isVersionOf      | optional property                                                                                |
| dcterms:medium           | optional property                                                                                |
| dcterms:provenance       | optional property                                                                                |
| dcterms:references       | optional property                                                                                |
| dcterms:replaces         | optional property                                                                                |
| dcterms:requires         | optional property                                                                                |
| **dcterms:spatial**      | **at least one of the red properties should be present (and can be used alongside each other)**  |
| dcterms:tableOfContents  | optional property                                                                                |
| **dcterms:temporal**     | **at least one of the red properties should be present (and can be used alongside each other)**  |
| edm:currentLocation      | optional property                                                                                |
| edm:hasMet               | optional property                                                                                |
| edm:hasType              | optional property                                                                                |
| edm:incorporates         | optional property                                                                                |
| edm:isDerivativeOf       | optional property                                                                                |
| **edm:isNextInSequence** | **recommended property**                                                                         |
| edm:isRelatedTo          | optional property                                                                                |
| edm:isRepresentationOf   | optional property                                                                                |
| edm:isSimilarTo          | optional property                                                                                |
| edm:isSuccessorOf        | optional property                                                                                |
| edm:realizes             | optional property                                                                                |
| **edm:type**             | **mandatory property**                                                                           |
| owl:sameAs               | optional property                                                                                |

</details>

### **Properties for ore:Aggregation**

<details>
<summary>Properties for ore:Aggregation</summary>

|  **edm:aggregatedCHO**       |  **mandatory property**                                                                           |
|:-----------------------------|:--------------------------------------------------------------------------------------------------|
| **edm:dataProvider**         | **mandatory property**                                                                            |
| edm:hasView                  | optional property                                                                                 |
| **edm:isShownAt**            | **at least one of the green properties should be present (and can be used alongside each other)** |
| **edm:isShownBy**            | **at least one of the green properties should be present (and can be used alongside each other)** |
| **edm:object**               | **recommended property**                                                                          |
| **edm:provider**             | **mandatory property**                                                                            |
| dc:rights                    | optional property                                                                                 |
| **edm:rights**               | **mandatory property**                                                                            |
| edm:ugc                      | optional property                                                                                 |
| **edm:intermediateProvider** | **recommended property**                                                                          |

</details>

### **Properties for edm:WebResource**

<details>
<summary>Properties for edm:WebResource</summary>

|                        |                          |
|:-----------------------|:-------------------------|
| dc:creator             | optional property        |
| dc:description         | optional property        |
| dc:type                | optional property        |
| dc:format              | optional property        |
| dc:rights              | optional property        |
| dc:source              | optional property        |
| dcterms:conformsTo     | optional property        |
| dcterms:created        | optional property        |
| dcterms:extent         | optional property        |
| dcterms:hasPart        | optional property        |
| dcterms:isFormatOf     | optional property        |
| dcterms:isPartOf       | optional property        |
| dcterms:isReferencedBy | optional property        |
| dcterms:issued         | optional property        |
| edm:isNextInSequence   | optional property        |
| **edm:rights**         | **recommended property** |
| owl:sameAs             | optional property        |

</details>

## **Contextual Classes**

### **Properties for edm:Agent**

<details>
<summary>Properties for edm:Agent</summary>

|                                |                          |
|:-------------------------------|:-------------------------|
| **skos:prefLabel**             | **recommended property** |
| **skos:altLabel**              | **recommended property** |
| skos:note                      | optional property        |
| dc:date                        | optional property        |
| dc:identifier                  | optional property        |
| dcterms:hasPart                | optional property        |
| dcterms:isPartOf               | optional property        |
| edm:begin                      | optional property        |
| edm:end                        | optional property        |
| edm:hasMet                     | optional property        |
| edm:isRelatedTo                | optional property        |
| foaf:name                      | optional property        |
| rdaGr2:biographicalInformation | optional property        |
| **rdaGr2:dateOfBirth**         | **recommended property** |
| **rdaGr2:dateOfDeath**         | **recommended property** |
| rdaGr2:dateOfEstablishment     | optional property        |
| rdaGr2:dateOfTermination       | optional property        |
| rdaGr2:gender                  | optional property        |
| rdaGr2:placeOfBirth            | optional property        |
| rdaGr2:placeOfDeath            | optional property        |
| rdaGr2:professionOrOccupation  | optional property        |
| owl:sameAs                     | optional property        |

</details>

### **Properties for edm:Place**

<details>
<summary>Properties for edm:Place</summary>

|                      |                          |
|:---------------------|:-------------------------|
| **wgs84\_pos:lat**   | **recommended property** |
| **wgs84\_pos:long**  | **recommended property** |
| wgs84\_pos:alt       | optional property        |
| **skos:prefLabel**   | **recommended property** |
| skos:altLabel        | optional property        |
| skos:note            | optional property        |
| dcterms:hasPart      | optional property        |
| dcterms:isPartOf     | optional property        |
| edm:isNextInSequence | optional property        |
| owl:sameAs           | optional property        |

</details>

### **Properties for edm:TimeSpan**

<details>
<summary>Properties for edm:TimeSpan</summary>

|                      |                          |
|:---------------------|:-------------------------|
| **skos:prefLabel**   | **recommended property** |
| skos:altLabel        | optional property        |
| skos:note            | optional property        |
| dcterms:hasPart      | optional property        |
| dcterms:isPartOf     | optional property        |
| **edm:begin**        | **recommended property** |
| **edm:end**          | **recommended property** |
| edm:isNextInSequence | optional property        |
| owl:sameAs           | optional property        |

</details>

### **Properties for skos:Concept**

<details>
<summary>Properties for skos:Concept</summary>

|  **skos:prefLabel**    |  **recommended property**    |
|:-----------------------|:-----------------------------|
| **skos:altLabel**      | **recommended property**     |
| skos:broader           | optional property            |
| skos:narrower          | optional property            |
| skos:related           | optional property            |
| skos:broadMatch        | optional property            |
| skos:narrowMatch       | optional property            |
| skos:relatedMatch      | optional property            |
| skos:exactMatch        | optional property            |
| skos:closeMatch        | optional property            |
| skos:note              | optional property            |
| skos:notation          | optional property            |
| skos:inScheme          | optional property            |

</details>

### **Properties for cc:License**

<details>
<summary>Properties for cc:License</summary>

|  **odrl:inheritFrom**    |  **mandatory property**    |
|:-------------------------|:---------------------------|
| cc:deprecatedOn          | optional property          |

</details>
