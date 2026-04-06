---
tags:
  - '#mapping-rules'
  - '#metadata-quality'
  - '#identifiers'
---

# Basic metadata quality aspects

- [Identifiers for resources in the data](#identifiers-for-resources-in-the-data)
- [Language aspects of the data](#language-aspects-of-the-data)
  - [The language of the values given in the metadata properties](#the-language-of-the-values-given-in-the-metadata-properties)
  - [The language of the object being described](#the-language-of-the-object-being-described)
- [General mapping rules](#general-mapping-rules)

### Identifiers for resources in the data

- Datasets will be provided to Europeana in an RDF/XML structure and will contain metadata descriptions for many cultural heritage objects.
- The metadata description for one cultural heritage object is made up of several “sections”.
- Each section corresponds to an instance of one of the classes described above and contains the properties and values associated with that class.
- Each of these sections of metadata can be regarded as a “resource”in its own right because it will have a have a unique identifier andone or more properties associated to that particular class. The term “resource” is used for these sections of metadata in the remainder of this part of the document.
- Each resource must have its own unique identifier (URI) so that all the resourcesin one description can be linked together internally. For more information on providing URI's consult the document '[URIs in the context of the Europeana Data Model](https://pro.europeana.eu/files/Europeana_Professional/Share_your_data/Technical_requirements/FAQs/URIs%20in%20EDM_pro.pdf)'
- The identifier for the resource is given in the “rdf:about” statement at the start of the section of metadata for the resource.
- The link from a referring resource (a) to another resource (b) is made by putting the identifier of (b) in one of the properties of (a) as an “rdf:resource”. See examples below.

Each resource (section of metadata) starts with the “rdf:about” statement containing the identifier of the resource. For example:

*Identifier for the resource representing the Provided CHO*

```java
<edm:ProvidedCHO rdf:about="#UEDIN:214">
```

*Identifier for resource representing the WebResource*

```java
<edm:WebResource rdf:about="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg">
```

*Identifier for resource representing the Aggregation*

```java
<ore:Aggregation rdf:about="http://www.mimo-db.eu/UEDIN/214">
```

The resources are then linked using those identifiers in the “rdf:resource “ statement.  
*The Aggregation resource is linked to the ProvidedCHO resource using its ID in the rdf:resource statement*

```java
<ore:Aggregation rdf:about="http://www.mimo-db.eu/UEDIN/214">
<edm:aggregatedCHO rdf:resource="#UEDIN:214"/>
...
</ore:Aggregation>
```

*The Aggregation is linked to the WebResource resource using its ID in the rdf:resource statement*

```java
<ore:Aggregation rdf:about=http://www.mimo-db.eu/UEDIN/214>
<edm:aggregatedCHO rdf:resource="#UEDIN:214"/>
<edm:isShownBy rdf:resource="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg"/>...
</ore:Aggregation>
```

Contextual resources are linked in a similar fashion. A property in the metadata of one of the core class resources will contain the ID of the contextual resource. In this example the edm:ProvidedCHO has a dc:type property which contains the HTTP URI which is the identifier for the skos:Concept resource.

```java
<edm:ProvidedCHO rdf:about="#UEDIN:214">
<dc:title> ...
<dc:type rdf:resource="http://www.mimo-db.eu/HornbostelAndSachs/356"/>
<dc:......
</edm:ProvidedCHO>
<skos:Concept rdf:about="http://www.mimo-db.eu/HornbostelAndSachs/356">
<skos:prefLabel xml:lang="en">423.22 Labrosones with slides</skos:prefLabel>
</skos:Concept>
```

In the example identifiers above you will see that the URIs are not of the same sort.

- The ID of the ProvidedCHO resource is an internal identifier (a record identifier in fact) used here simply to allow other resources to refer to it.
- The ID of the WebResource resource is a real HTTP URI that will resolve to an external resource.

There **are four types of identifier** that can be used in this context:

1. an HTTP URI that references a linked open data resource external to the data submitted to Europeana  
(*A dereferenceable Uniform Resource Identifier uses HTTP to obtain a copy or representation of the resource it identifies, see* <https://en.wikipedia.org/wiki/Linked_data> )  
2. an HTTP URI that references another resource inside the same metadata description submitted to Europeana  
3. a local URI that is not dereferenceable but that refers to another resource inside the same metadata description (e.g. an identifier internal to the provider infrastructure)  
4. an identifier that is not dereferenceable but that refers to another resource inside the same metadata description (any string used to identify a resource, such as an inventory number)

### Language aspects of the data

There are two language aspects to the data in Europeana that are relevant for providers:

- **the language of the values in the properties**
- **the language of the object being described**

In the ISO 639-­2 standard widely-­known languages have both a two letter code (e.g. “fr” for French and “it” for Italian) and a three letter code (“eng” for English “fre” for French). Less widely used languages may only have the three letter code. Providers are recommended to use the two letter code wherever possible, as per the table at <https://www.loc.gov/standards/iso639-2/php/code_list.php>

[IANA has created a registry rationalising the codes](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry). It clarifies which languages are recommended to use the two letter code and which must use the three letter code. Providers are recommended to consult this registry.

A useful explanation of this can be found at <https://www.w3.org/International/articles/language-tags/index.en> .

#### The language of the values given in the metadata properties

The language of the values given in the properties should be declared using the xml:lang attribute with the appropriate language code. For example, a description in French can be:

```java
<dc:description xml:lang="fr">Trois boutons en argent</dc:description>
```

If that description is also available in English the property can be repeated

```java
<dc:description xml:lang="en">Three silver buttons</dc:description>
```

Note that when the value of a property is a reference to a resource (i.e., with the attribute “rdf:resource”) the use of “xml:lang” is not allowed.  
It is also important to note that for Europeana there are specific rules for translations of titles that apply to dc:title and dcterms:alternative. These are given in the property description tables in the next sections.

#### The language of the object being described

Where there is a language aspect to the object being described, providers are asked to indicate the language of the object using the dc:language property. For objects with the edm:type of TEXT it is mandatory and for other types (for example, a voice recording or an image with some text on it) it is recommended. We also recommend the use of the ISO 639-­‐2 code ZXX for no linguistic content. It is recommended to use a language code for the value:

```java
<dc:language>it</dc:language>
```

### General mapping rules

1. Providers are encouraged to provide as many properties as they can from their existing data to create a full description. It is not necessary to use all the available EDM properties, but those that are marked as mandatory must be provided.
2. Provide the properties inthe record in the same order given in this document.
3. If the same contextual class applies to multiple ProvidedCHOs then it should be repeated for each ProvidedCHO. I.e. it cannot just be provided once in the data file.
4. The values provided for properties will either be a referenceor a literal. Most properties can have either type of value but for some, one or the other is specified.
5. Provide only a reference or a literal value to avoid duplicating data.
6. Properties used in combination with (i.e. which link to) contextual resources are recommended.
7. Whenever a literal value is used an xml:lang tag should be employed to indicate the language of the value. It is recommended to use them wherever appropriate.   
   Note that when the value of a property is a reference to a resource (i.e., with the attribute “rdf:resource”) the use of “xml:lang” is not allowed.
8. Try to find the most precise property that is available. For example, use the sub-­properties dcterms:spatial or dcterms:temporal instead of the more general dc:coverage.
9. All classes and other resources represented in an EDM record should have an identifier as described in the above  section **(Identifiers for resources in the data)**
10. Do not use HTMLmark­‐up in property values as it may distort the portal display and the API data output.
11. Ensure the mandatory or alternative mandatory properties are included.
12. The properties dc:type and edm:type should have different values.
