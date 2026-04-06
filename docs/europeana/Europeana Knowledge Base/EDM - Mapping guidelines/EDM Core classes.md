---
tags:
  - '#core-classes'
---

# EDM Core classes

This section details **the three core classes: edm:ProvidedCHO, edm:WebResource, and ore:Aggregation**.

EDM separates the cultural heritage object from its digital representation in order for metadata values to be associated appropriately. In this it differs greatly from ESE even though many of the properties will be familiar.

To enable this separation, EDM defines three classes to represent the core object. Each submission of an item to Europeana should give rise to the creation of three types of “resource” (section of metadata):

- **one for the source cultural heritage object -­ edm:ProvidedCHO**
- **one for the digital object being submitted -­ edm:WebResource**
- **one for the overall package - ore:Aggregation**

Each will have its own associated metadata, giving three core “metadata sections” per item submitted.

For example, the Mona Lisa is represented by the edm:ProvidedCHO and its digital image by the class edm:WebResource. This allows the relevant metadata properties to be applied to each class. In the Mona Lisa example, the edm:ProvidedCHO could have a dc:creator property with the value “Leonardo da Vinci” and the edm:WebResource a dc:format property with the value “jpg”. Because the metadata about an object and its digital representations will now be separated between those two classes, there is also a mechanism to associate the related classes. This is the ore:Aggregation class and it is the pivotal object between the edm:ProvidedCHO and the edm:WebResource(s). It has properties to allow linking between the associated classes and also has some more familiar descriptive properties, such as edm:dataProvider, that apply to the whole group.

![](https://europeana.atlassian.net/wiki/download/attachments/987758622/image-20211022-114414.png?version=1&modificationDate=1634903057971&cacheVersion=1&api=v2)

To handle more complex provided objects additional properties have been defined to express the relationships between parts of objects. For example, an edm:ProvidedCHO could have an edm:isNextInSequence property to link to another object which logically precedes it.   
   
With the ability to express such relationships, providers should always try to “distribute” their original descriptions onto objects that precisely match their holdings, i.e. choose the most appropriate level of granularity for the CHO. In the archive domain, for example, a record can describe different object levels (“sub-­series”, “file, “item”, etc.). The description should be broken down into a number of sub-descriptions each of which is about an object at a different level that is considered to be a CHO. They should be related using dcterms:isPartOf (or dcterms:hasPart) and edm:isNextInSequence statements. For example: the first edm:ProvidedCHO would relate to an aggregation for a sub-­‐series, the second edm:ProvidedCHO to an aggregation for a file and the   
third edm:ProvidedCHO would relate to an aggregation for an item.

The next three subsections of this page consist of a table for each class showing the properties that apply to it. Each property has:

- a brief definition together with some mapping notes, including a snippet of xml showing how to code for a simple text string (Literal) or for a link to another resource (Ref).
- the expected type of value. This is either “**Literal**” for a text string or “**Ref**” for a **URI or local identifier**.
- a cardinality column (**Card**.) showing whether the property is **mandatory** and/or **repeatable**.
