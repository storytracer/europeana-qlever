
# Annotation API Documentation

The Annotation API is allows users to search, obtain and contribute annotations about items in Europeana. Annotations are user-contributed or software-generated enhancements, additions or corrections to (or a selection of) metadata or content resources. We adopted the [Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) as a base model for the representation of annotations and as a format for exchanging annotations between client applications and the API, but also the [Web Annotation Protocol](https://www.w3.org/TR/annotation-protocol/) as base protocol for the API.

|                                                                 |                                            |
|:----------------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] [Get your API Key here](#get-your-api-key-here) <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                                  |                                                                                              |
|:---------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/annotation) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

- [The Annotation Data Model](#the-annotation-data-model)
  - [What are annotations?](#what-are-annotations)
  - [Basics of the model](#basics-of-the-model)
  - [Application Scenarios](#application-scenarios)
  - [Object links](#object-links)
  - [Annotating media resources](#annotating-media-resources)
  - [Transcriptions](#transcriptions)
- [Retrieval](#retrieval)
- [Discovery](#discovery)
- [Provision](#provision)
  - [Create](#create)
  - [Update](#update)
  - [Delete](#delete)

# The Annotation Data Model

## What are annotations?

Annotations (in the Europeana context) are user-contributed or software-generated enhancements to (a selection of) metadata or content resource. The Annotations API adopted the [Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) (WADM) as a base model for representing and exchanging annotations between client applications and the API. The WADM is a W3C recommendation that describes a model and format to share annotations across different platforms.

Please note that, even though we have adopted WADM as underlying data model for this API, it is not expected that we support the full extent of the model. We thus advise to look at the [EDM Annotations Profile](https://docs.google.com/document/d/1V-XjlQXPOQLZo7-c6UBzqYEc0mNPtCBfXFCWdquuUvc) which describes the basics of our implementation and, in particular, the section on [Annotation Scenarios](#annotation-scenarios) for a comprehensive list of the different kinds of annotations that we support.

## Basics of the model

In WADM, an annotation is essentially a reified relation between two or more resources, typically a body and a target, and conveys that the **body** reflects what is intended to be said about the **target**. A body can also be absent to describe situations where a target is simply bookmarked. A **target** can represent a resource or just a part of it that is being annotated.

Being reified as a class enables an annotation to be further described with a **motivation** which expresses the reason why the annotation was created but also some **provenance** information such as the user that created the annotation and the software application that was used, as well as the times when it was initially created and sent to the API.

<details>
<summary>The following fields are used to describe an Annotation resource in JSON-LD</summary>

|  **Field**                                                                                                                                                                                                                                                                                                                                                                                  |  **Datatype**                                                                                          |  **Description**                                                                                                                                                                                                                                                     |
|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Annotation**                                                                                                                                                                                                                                                                                                                                                                              |                                                                                                        |                                                                                                                                                                                                                                                                      |
| @context                                                                                                                                                                                                                                                                                                                                                                                    | String (URL)                                                                                           | The URL of the JSON-LD context. (always with value "<http://www.w3.org/ns/anno.jsonld>")                                                                                                                                                                             |
| id                                                                                                                                                                                                                                                                                                                                                                                          | String (URI)                                                                                           | The identifier of the Annotation. It is automatically generated upon creation.                                                                                                                                                                                       |
| type                                                                                                                                                                                                                                                                                                                                                                                        | String                                                                                                 | The type of the resource. Always set to "Annotation".                                                                                                                                                                                                                |
| created                                                                                                                                                                                                                                                                                                                                                                                     | String (DateTime)                                                                                      | The time at which the Annotation was created by the client application. It is expressed in ISO8601 format with a timezone specified.                                                                                                                                 |
| creator                                                                                                                                                                                                                                                                                                                                                                                     | Object ([Agent](#agent))                                                                               | The agent responsible for creating the Annotation. This may be either a human or software agent and is always determined by the user information present in the JWT token used upon creation.                                                                        |
| generated                                                                                                                                                                                                                                                                                                                                                                                   | String (DateTime)                                                                                      | The time at which the annotation was sent to the server. It is expressed in ISO8601 format with a timezone specified.                                                                                                                                                |
| generator                                                                                                                                                                                                                                                                                                                                                                                   | Object (Software)                                                                                      | The agent responsible for generating the Annotation. The client application used to submit the annotation to the server and is always determined by the client information present in the JWT token used upon creation.                                              |
| motivation                                                                                                                                                                                                                                                                                                                                                                                  | String                                                                                                 | Expresses the reason why the annotation was created. Depending on the application scenario, the value can one of the following: "tagging", "linking", "describing", “highlighting“, “transcribing“, “translating“, “captioning“, “subtitling“, “linkForContributing“ |
| body                                                                                                                                                                                                                                                                                                                                                                                        | String or Object (Semantic Resource or Textual Body)                                                   | A body conveying what is intended to be said about the target. If the value is provided as a string, then it is interpreted as the URI and must only be used for the semantic tagging scenario. See the application scenarios section for more information.          |
| bodyValue                                                                                                                                                                                                                                                                                                                                                                                   | String                                                                                                 | A string conveying the tag text. This field must only be used in combination with "tagging" as motivation and when the language of the tag is not known. Otherwise, it is recommended to use the body field as defined in the Application Scenarios section.         |
| target                                                                                                                                                                                                                                                                                                                                                                                      | String, Array (String), [Media Resource](#media-resource) or Array ([Media Resource](#media-resource)) | The URL of the resource that is being annotated, or a specific resource in the case of media annotations. An array of URLs may also be set (mostly used for the object linking).                                                                                     |
| **User Agent**                                                                                                                                                                                                                                                                                                                                                                              |                                                                                                        |                                                                                                                                                                                                                                                                      |
| A user agent typically responsible for creating the annotation.                                                                                                                                                                                                                                                                                                                             |                                                                                                        |                                                                                                                                                                                                                                                                      |
| id                                                                                                                                                                                                                                                                                                                                                                                          | String                                                                                                 | The unique identifier of the user. This identififer is obained from the JWT token used upon creation.                                                                                                                                                                |
| type                                                                                                                                                                                                                                                                                                                                                                                        | String                                                                                                 | The type of the resource. Always set to "Person".                                                                                                                                                                                                                    |
| **Software Agent**                                                                                                                                                                                                                                                                                                                                                                          |                                                                                                        |                                                                                                                                                                                                                                                                      |
| A client application or software typically responsible for generating the annotation on behalf of the user. A software can also create annotations if they result from an automatic process.                                                                                                                                                                                                |                                                                                                        |                                                                                                                                                                                                                                                                      |
| id                                                                                                                                                                                                                                                                                                                                                                                          | String                                                                                                 | The identifier of the client application. This identififer is obained from the JWT token used upon creation.                                                                                                                                                         |
| type                                                                                                                                                                                                                                                                                                                                                                                        | String                                                                                                 | The type of the resource. Always set to "Software".                                                                                                                                                                                                                  |
| **Semantic Resource**                                                                                                                                                                                                                                                                                                                                                                       |                                                                                                        |                                                                                                                                                                                                                                                                      |
| A Semantic Resource is used whenever an external resource needs to be referenced as the body of the annotation. It is mostly used for Semantic Tagging.                                                                                                                                                                                                                                     |                                                                                                        |                                                                                                                                                                                                                                                                      |
| type                                                                                                                                                                                                                                                                                                                                                                                        | String                                                                                                 | Always "SpecificResource".                                                                                                                                                                                                                                           |
| source                                                                                                                                                                                                                                                                                                                                                                                      | String (URI)                                                                                           | The URI of the resource being referred as body.                                                                                                                                                                                                                      |
| language                                                                                                                                                                                                                                                                                                                                                                                    | String (ISO639)                                                                                        | The ISO639 language code corresponding to the language of the resource.                                                                                                                                                                                              |
| **Media Resource**                                                                                                                                                                                                                                                                                                                                                                          |                                                                                                        |                                                                                                                                                                                                                                                                      |
| Annotations that refer to a media resource require that an oa:SpecificResource object is defined so that the context in which the annotation was made is captured by the annotation. Besides context, a Specific Resource can be used to capture any additional information about how a target is used in the Annotation. The following table lists the properties supported by this class. |                                                                                                        |                                                                                                                                                                                                                                                                      |
| type                                                                                                                                                                                                                                                                                                                                                                                        | String                                                                                                 | Always "SpecificResource".                                                                                                                                                                                                                                           |
| source                                                                                                                                                                                                                                                                                                                                                                                      | String (URL)                                                                                           | The URL that identifies the media resource which is the ultimate target of the annotation.                                                                                                                                                                           |
| scope                                                                                                                                                                                                                                                                                                                                                                                       | String (URI)                                                                                           | The unique identifier of the Europeana item to which this media resource is associated. In more general terms, scope is used to define the context in which the annotation was made, in terms of the resources that the annotator was viewing or using at the time.  |

</details>

<details>
<summary>Example of the annotation model</summary>

#### SHOW A DYNAMIC EXAMPLE

</details>

## Application Scenarios

Because annotations are a very flexible construct, in theory, any kind of information could be represented as an annotation. However, to guarantee consistency of the annotations and their proper display or reuse, a range of “use cases” for annotations were identified, modelled and implemented which we call application scenarios. This list can grow as new and relevant use cases are identified and proposed for adoption.

This section explains all the application scenarios that are presently supported with examples on how they are represented in the API.

> *The examples used in this Section are shortened versions of the Annotation Model which exclude administrative fields such as created, creator, generated, generator, you can find an example of a complete Annotation Data Model implementation* [*here*](#here)*.*

### 1. Tagging (without language)

A tag is a short textual label for a resource. It can be used to e.g. classify or name a resource. This scenario only applies when the language of the tag is not known, otherwise see the scenario described in the next Section.

|                |                                                                              |
|:---------------|:-----------------------------------------------------------------------------|
| **Annotation** |                                                                              |
| `motivation`   | `tagging`                                                                    |
| `bodyValue`    | The short text of the tag. It typically contains a single word or expression |
| `target`       | The URL of the Item                                                          |

<details>
<summary>Example: An Europeana item tagged with the word "painting"</summary>

```java
{
  "motivation": "tagging",
  "bodyValue": "painting",
  "target": "http://data.europeana.eu/item/92062/BibliographicResource_1000126189360"
}
```

</details>

### 2. Tagging (with language)

A language tag is a short textual label for a resource that is qualified with a language. Similarly as the previous scenario, language qualified tags can be used to name or classify a resource.

|                |                                                                                                                                                    |
|:---------------|:---------------------------------------------------------------------------------------------------------------------------------------------------|
| **Annotation** |                                                                                                                                                    |
| `motivation`   | `tagging`                                                                                                                                          |
| `body`         | A `TextualBody` as the body of the annotation with the tag as the value of `value` field and the respective language indicated in `language` field |
| `target`       | The URL of the Item                                                                                                                                |

<details>
<summary>Example: An Europeana item tagged with the English word "painting"</summary>

```java
{
  "motivation": "tagging",
  "body": {
    "type": "TextualBody",
    "value": "painting",
    "language": "en"
 },
  "target": "http://data.europeana.eu/item/92062/BibliographicResource_1000126189360"
}
```

</details>

### 3. Semantic tagging

An annotation of a CHO with a semantic tag. A semantic tag is a tag from a controlled (linked data) vocabulary such as VIAF or AAT. As any other tag, semantic tags are typically used to classify a resource with the benefit of bring extra information to the annotation as the result of being a linked data resource.

|                |                                                             |
|:---------------|:------------------------------------------------------------|
| **Annotation** |                                                             |
| `motivation`   | `tagging`                                                   |
| `body`         | The URL of the semantic resource being used to tag the item |
| `target`       | The URL of the Item                                         |

<details>
<summary>Example: An Europeana item tagged with a semantic resource for Paris from Geonames</summary>

```java
{
  "motivation": "tagging",
  "body": "http://sws.geonames.org/2988507",
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}
```

</details>

### 4. Geospatial tagging with coordinates

An annotation of a CHO with a location given in geospatial coordinates (latitude, longitude, and optionally altitude). In addition, there can be a label expressing the name or address of the location.

|                |                                                                                                                                                                                                         |
|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Annotation** |                                                                                                                                                                                                         |
| `motivation`   | `tagging`                                                                                                                                                                                               |
| `body`         | A resource of type `Place` that follows the EDM guidelines for Places. Some of the properties that may be present are: `latitude`, `longitude`, `altitude`, `prefLabel` or `altLabel` when appropriate. |
| `target`       | The URL of the Item                                                                                                                                                                                     |

<details>
<summary>Example: An Europeana item tagged with geospatial information</summary>

```java
{
  "motivation": "tagging",
  "body": {
    "@context": "http://www.europeana.eu/schemas/context/entity.jsonld",
    "type": "Place",
    "prefLabel": {
      "en": "A label for the location, e.g., an address or place name"
    },
    "lat": "48.85341",
    "long": "2.3488"
  },
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}
```

</details>

### 5. Geospatial tagging with an address

An annotation of a CHO with a location given in geospatial coordinates (latitude, longitude, and optionally altitude). In addition, there can be a label expressing the name or address of the location.

|                |                                                                                                                                                                                                         |
|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Annotation** |                                                                                                                                                                                                         |
| `motivation`   | `tagging`                                                                                                                                                                                               |
| `body`         | A resource of type `Place` that follows the EDM guidelines for Places. Some of the properties that may be present are: `latitude`, `longitude`, `altitude`, `prefLabel` or `altLabel` when appropriate. |
| `target`       | The URL of the Item                                                                                                                                                                                     |

<details>
<summary>Example: An Europeana item tagged with geospatial information</summary>

```java
{
  "motivation": "tagging",
  "body": {
    "@context": "http://www.europeana.eu/schemas/context/entity.jsonld",
    "type": "Place",
    "prefLabel": {
      "en": "A label for the location, e.g., an address or place name"
    },
    "lat": "48.85341",
    "long": "2.3488"
  },
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}
```

</details>

## Object links

An object link is a relationship between two (Europeana) objects. This relationship can be any.

|               |                                                                                                                                                                                                      |
|:--------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Example:      | This [object in Europeana](https://www.europeana.eu/en/item/09102/_UEDIN_214) is (in some way) similar to [this object](https://www.europeana.eu/en/item/92062/BibliographicResource_1000126189360). |
| Requirement:  | An object link can only be made between two Europeana objects.                                                                                                                                       |
| In the API:   | Set the "motivation" to "linking" and set as target an array containing the URIs of both objects.                                                                                                    |
| Availability: | Since version 0.2.1.                                                                                                                                                                                 |

<details>
<summary>Example: linking two Europeana items together.</summary>

```java
{
  "motivation": "linking",
  "target": [
      "http://data.europeana.eu/item/92062/BibliographicResource_1000126189360",
      "http://data.europeana.eu/item/92062/BibliographicResource_1000126189361"
  ]
}
```

</details>

## Annotating media resources

Annotating a media resource means that the target of the annotation is not the Europeana item but instead a specific media resource within that item.

|               |                                                                                                                                                                                                       |
|:--------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| In the API:   | Set the "target" of the annotation to a JSON object with the "scope" holding the unique identifier of the Europeana item and the "source" field the URL of the actual media resource being annotated. |
| Availability: | Since version 0.2.8.                                                                                                                                                                                  |

<details>
<summary>Example: tagging a sound track of an Europeana item with the simple tag "Folk Music".</summary>

```java
{
  "motivation": "tagging",
  "bodyValue": "Folk Music",
  "target": {
    "type": "SpecificResource",
    "scope": "http://data.europeana.eu/item/2059207/data_sounds_T471_5",
    "source": "http://comhaltasarchive.ie/tracks/12535"
  }
}
```

</details>

## Transcriptions

A transcription is typically an annotation expressing a relation between an image and the text that is represented on that image. Besides the text, the annotation can also refer to a page where the text is displayed, like in the example below.

|               |                                                                                            |
|:--------------|:-------------------------------------------------------------------------------------------|
| In the API:   | Set the "motivation" to "transcribing" and apply the same criteria as for media resources. |
| Availability: | Since version 0.2.8.                                                                       |

<details>
<summary>Example: annotating the image of an Europeana item with the transcription page available at Transcribathon.</summary>

#### Example: annotating the [image](https://glam.uni.wroc.pl/iiif/image-api/RKP_HAASE_371_62468_0001/full/full/0/default.jpg) of an [Europeana item](https://www.europeana.eu/item/743/_nhp5sXg) with the [transcription page](https://europeana.transcribathon.eu/documents/story/item/?item=39378387) available at [Transcribathon](https://transcribathon.eu).

```java
{
  "motivation": "transcribing",
  "body": {
    "id": "https://europeana.transcribathon.eu/documents/story/item/?item=39378387",
    "language": "de",
    "format": "text/html"
  },
  "target": {
    "scope": "http://data.europeana.eu/item/743/_nhp5sXg",
    "source": 
    "https://glam.uni.wroc.pl/iiif/image-api/RKP_HAASE_371_62468_0001/full/full/0/default.jpg"
  }
}
```

</details>

# Retrieval

Retrieves all metadata available for a specific annotation. This includes only the metadata that is part of the annotation.

### Request

```java
https://api.europeana.eu/annotation/[IDENTIFIER]
Accept: [ACCEPT]
```

```java
https://api.europeana.eu/annotation/[IDENTIFIER].[FORMAT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                |
|:------------------|:-----------------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| IDENTIFIER        | path             | The local identifier of the annotation.                                                                                                         |
| ACCEPT            | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported. |
| FORMAT            | path             | Convenience method where the format is indicated as a path parameter instead of via the Accept header.                                          |

### Response

<details>
<summary>Example Response from the Read method in the Annotation API</summary>

```java
HTTP/1.1 200 OK
Content-Type: application/ld+json
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "id": "http://data.europeana.eu/annotation/base/1",
  "type": "Annotation",
  "created": "2016-01-31T12:03:45Z",
  "generated": "2016-01-31T12:04:00Z",
  "generator": "http://www.europeana.eu",
  "bodyValue": "Trombone",
  "motivation": "tagging",
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}

```

</details>

See [data model](#data-model) for more information on the representation of an annotation.

# Discovery

Search for annotations.

> *GET /search*

### Request

<details>
<summary>Table of parameters that can be sent in an Annotation Search Request</summary>

|  Parameter    |  Datatype    |  Description                                                                                                                                                                                                                                                                                                                                                                                     |
|:--------------|:-------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| query         | String       | The search term(s), this is mandatory.                                                                                                                                                                                                                                                                                                                                                           |
| profile       | String       | The search profile which determines the extent of information returned as search result. Currently, 3 options are supported: <br/><ul><li><p>"minimal" which returns only the identifier of the annotation</p></li><li><p>"standard" (default) which returns the annotation as it was sent to the API</p></li><li><p>“dereference“ which expands the description for semantic tags</p></li></ul> |
| qf            | String       | Query filter, to search on specific fields. The list of fields is presented below.                                                                                                                                                                                                                                                                                                               |
| facet         | String       | Includes a field to be used as facet in the response (see below which fields can be used as facets). More than one field can be added if separated by a space.                                                                                                                                                                                                                                   |
| pageSize      | Number       | The number of records to return per page. For minimal profile, the maximum is 10.000 while for the standard profile is 100, with 10 as default for both profiles.                                                                                                                                                                                                                                |
| page          | Number       | The page of the search results, defaults to 0 (first page).                                                                                                                                                                                                                                                                                                                                      |
| sort          | String       | Includes a field to be used for sorting. One of: created, generated or modified.                                                                                                                                                                                                                                                                                                                 |
| sortOrder     | String       | Order of sorting, either "asc" (ascending) or "desc" (descending).                                                                                                                                                                                                                                                                                                                               |

</details>

### Search and Facet fields

The following table shows the fields that can be used for searching annotations and the ones that can be used for faceting:

<details>
<summary>Table of search and facet fields for the Search method of the Annotations API</summary>

|  Field              |  Datatype    |  Used for Facetting    |  Description                                                                                           |
|:--------------------|:-------------|:-----------------------|:-------------------------------------------------------------------------------------------------------|
| motivation          | keyword      | yes                    | motivation of the Annotation                                                                           |
| anno\_uri           | keyword      |                        | complete identifier of an Annotation                                                                   |
| anno\_id            | keyword      |                        | local identifier of an Annotation (/<provider>/<identifier>)                                           |
| generator\_uri      | keyword      | yes                    | complete identifier of the generator                                                                   |
| generator\_name     | keyword      | yes                    | name of the generator                                                                                  |
| generated           | date         |                        | date on which the Annotation was first provided to the API                                             |
| creator\_uri        | keyword      | yes                    | complete identifier of the creator                                                                     |
| creator\_name       | keyword      | yes                    | name of the user that created the annotation                                                           |
| created             | date         |                        | date on which the Annotation was created by the annotation client application                          |
| modified            | date         |                        | date on which the Annotation was last modified                                                         |
| moderation\_score   | integer      | yes                    | sum of all reports made to an Annotation by other users                                                |
| text                | text         |                        | searches in all searchable text in an Annotation                                                       |
| body\_value         | text         | yes                    | value within the body of an Annotation, applies to e.g. simple tagging                                 |
| body\_uri           | keyword      | yes                    | complete identifier of the resource within the body of an Annotation, applies to e.g. semantic tagging |
| target\_uri         | keyword      | yes                    | complete identified of the target(s) of an Annotation                                                  |
| target\_record\_id  | keyword      | yes                    | local identifier of a record when the target is a record (/collectionId/objectId)                      |
| link\_resource\_uri | keyword      | yes                    | complete identifier of the resource being linked to (ie. through the relation property)                |
| link\_relation      | keyword      | yes                    | property being used to link two resources.                                                             |

</details>

### Response

<details>
<summary>An example of a Response to a Search Request from the Annotations API</summary>

```java

{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "id": "http://annotations.europeana.eu/annotation/search?wskey=xxxxx&query=*:*&page=0&pageSize=10",
  "items": [
    "http://data.europeana.eu/annotation/base/1",
    "http://data.europeana.eu/annotation/base/2",
    [..]
  ],
  "next": "http://annotations.europeana.eu/annotation/search?wskey=xxxxx&query=*:*&page=1&pageSize=10",
  "partOf": {
     "id": "http://annotations.europeana.eu/annotation/search?wskey=xxxxx&query=*:*",
     "total": 135610
  },
  "total": 10,
  "type": "AnnotationPage"
}
```

</details>

<details>
<summary>Example: Search for recently added tags:</summary>

> */search?wskey=xxxxx&profile=minimal&query=\*:\*&qf=motivation:tagging&sort=created&sortOrder=desc*

</details>

<details>
<summary>Example: Search for tags for Europeana record ID /92028/532E53363138382D2F290A40B3CA26B3889A6907:</summary>

> */search?wskey=xxxxx&profile=minimal&query=target\_id:"/92028/532E53363138382D2F290A40B3CA26B3889A6907"*

</details>

<details>
<summary>Example: Don't show annotations which are reported by two or more different users:</summary>

> */search?wskey=xxxxx&profile=minimal&query=\*:\*&qf=moderation\_score:[-1 TO \*]*

Note that providing \*:\* as a search query means you will get all annotations.

</details>

# Provision

> *Creating annotations in the production (live) environment is currently limited to only selected partners, You can* [*request access to the write methods by emailing us with your use case*](mailto:api@europeana.eu)*.*

## Create

The API has a generic method available for the creation of annotations. The creation method expects a body payload in the request with the full annotation. Alternatively you can provide this information as part of the body parameter.

> *POST* [*http://annotations.europeana.eu/annotation/*](http://annotations.europeana.eu/annotation/)

### Request

<details>
<summary>Example Request for the Create method in the Annotation API</summary>

An example to create a simple tag:

```java
POST  http://annotations.europeana.eu/annotation/?wskey=YOUR_KEY&userToken=YOUR_TOKEN HTTP/1.1
Accept: application/ld+json
Content-Type: application/ld+json
Content-Length: 999
{
  "motivation": "tagging",
  "bodyValue": "Trombone",
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}
```

Note that the motivation for a simple and a semantic tag is always "tagging", whereas the motivation for object linking scenarios is "linking".

</details>

### Response

<details>
<summary>Example Response to a Create request in the Annotation API</summary>

Response to the example request:

```java

Content-Type: application/ld+json
ETag: "_87e52ce126126"
Link: <http://www.w3.org/ns/ldp#Resource>l; rel="type"
Allow: POST,GET,OPTIONS,HEAD
Vary: Accept
Content-Length: 999
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "id": "http://data.europeana.eu/annotation/base/1",
  "type": "Annotation",
  "created": "2016-01-31T12:03:45Z",
  "creator": "http://data.europeana.eu/user/55376",
  "generated": "2016-01-31T12:04:00Z",
  "generator": "http://data.europeana.eu/provider/historypin",
  "bodyValue": "Trombone",
  "motivation": "tagging",
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}

```

</details>

For more examples and information on the data model for an annotation, see [data model](#data-model).

## Update

Update the contents of an annotation. For this you can send a PUT request to the ID of the annotation. You can only update the annotations you have created yourself.

> *PUT /base/1*

### Request

You can provide the same content in the Update method as you’d provide for the Create method. Note that you have to provide the full annotation body, you currently cannot update parts of the annotation.

<details>
<summary>Example Request of the Update Method in the Annotation API</summary>

```java
PUT /base/1 HTTP/1.1
Accept: application/ld+json
{
  "bodyValue": "Trombone",
  "motivation": "tagging",
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}
```

</details>

### Response

<details>
<summary>Example Response of the Update Method in the Annotation API</summary>

```java
HTTP/1.1 200 OK
Content-Type: application/ld+json
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "id": "http://data.europeana.eu/annotation/base/1",
  "type": "Annotation",
  "created": "2016-01-31T12:03:45Z",
  "generated": "2016-01-31T12:04:00Z",
  "generator": "http://www.europeana.eu",
  "bodyValue": "Trombone",
  "motivation": "tagging",
  "target": "http://data.europeana.eu/item/09102/_UEDIN_214"
}
```

</details>

## Delete

Delete an annotation. You can send a DELETE HTTP request using the ID of the annotation. You can only delete the annotations you have created yourself. Deletion means the annotation will not be available anymore for search, and only available for retrieval based on the ID of the annotation.

> *DELETE /base/1*

### Request

```java
DELETE /collections/1 HTTP/1.1
```

### Response

```java
HTTP/1.1 204 NO CONTENT
Content-Length: 0
```

### Roadmap and Changelog

We deploy new versions of this API quite regularly. It is currently available as a Public [Alpha](https://pro.europeana.eu/page/intro#release-alpha), which is the first public version released primarily to get feedback from you. Do note that this means that changes can be introduced which could break backwards compatibility. To see the changes made for the current version and also all previous releases, see the [API changelog in the project GitHub](https://github.com/europeana/annotation/releases).

### Credits

This API was initially developed as part of the [Europeana Sounds](http://pro.europeana.eu/get-involved/projects/project-list/europeana-sounds) project. It's development has been carried out by the [AIT Austrian Institute of Technology](http://www.ait.ac.at/) in cooperation with the Europeana Foundation.
