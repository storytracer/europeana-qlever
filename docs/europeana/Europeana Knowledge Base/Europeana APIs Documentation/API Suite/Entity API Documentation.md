---
tags:
  - '#apidocs'
---

# Entity API Documentation

The Entity API allows you to search for or retrieve information about entities that are referred to by items available in Europeana. It presently offers 3 methods:

1. Retrieval of the complete metadata set associated with an Entity
2. A way to suggest entities based on a string
3. a lookup method for resolving external URIs.

|                                                                                 |                                            |
|:--------------------------------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] [Get your API Key here](https://pro.europeana.eu/pages/get-api) <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                              |                                                                                              |
|:-----------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/entity) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

- [About the Europeana Entity collection](#about-the-europeana-entity-collection)
  - [Identifiers for entities](#identifiers-for-entities)
  - [Internal view of an entity](#internal-view-of-an-entity)
- [Supported classes of entities](#supported-classes-of-entities)
  - [Agent](#agent)
  - [Place](#place)
  - [Time Span](#time-span)
  - [Concept](#concept)
  - [Organisation](#organisation)
  - [Other classes of resources that are common to all entities](#other-classes-of-resources-that-are-common-to-all-entities)
- [Getting Started](#getting-started)
- [Retrieving an Entity](#retrieving-an-entity)
- [Resolving an entity by using an external URI](#resolving-an-entity-by-using-an-external-uri)
- [Search for an entity](#search-for-an-entity)
- [Roadmap and Changelog](#roadmap-and-changelog)

# About the Europeana Entity collection

In the context of Europeana APIs, an entity can be:

- a person (or “agent”), for instance Lili Boulanger or Claude Debussy;
- a topic (or “concept”) like Art Nouveau, migration or Musique Concrète
- a place, for instance Perpignan, Bratislava or Arnhem
- a time period, for instance the 21st century

Entities are helpful to provide context to an item and relate it to other items that have entities in common, which helps users to discover other items in the collection. They are linked to external data sources and controlled vocabularies like​ [Wikidata](http://www.wikidata.org/), [AAT](http://vocab.getty.edu/aat/), [VIAF](http://viaf.org/viaf/), [ULAN](http://vocab.getty.edu/ulan/), and [Geonames](http://geonames.org/) and are regularly updated and consolidated.  
The Entity API allows you to search for or retrieve information about entities that are referred to by items available in [Europeana.It](http://Europeana.It) presently offers 3 methods:

- Retrieval of the complete metadata set associated with an Entity;
- A way to suggest entities based on a string;
- a lookup method for resolving external URIs.

This collection is regularly updated and consolidated from external data sources so that the metadata is kept as fresh as possible.

## Identifiers for entities

As linked open data resources, all Europeana entities are identified using URIs defined under the `data.europeana.eu` namespace. This means that such identifiers are content negotiable to either the Europeana Website or APIs depending on the format requested via the Accept header.

**Syntax for URIs:**

```java
http://data.europeana.eu/[ENTITY_TYPE]/[ENTITY_ID]
```

**Example:**

```java
http://data.europeana.eu/agent/59904
```

## Internal view of an entity

The metadata that is made available for an entity is typically obtained from external data sources such as Wikidata. This data can also be complemented or changed to better fit the context in which they are used in Europeana. All this information is kept internally apart with its own provenance information for transparency and to facilitate its maintenance and management.

<details>
<summary>The following fields are included when the internal view is requested in JSON-LD:</summary>

|  **Field**                                                                            |  **Datatype**              |  **Description**                                                                                                                                                                 |
|:--------------------------------------------------------------------------------------|:---------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Entity**                                                                            |                            |                                                                                                                                                                                  |
| id                                                                                    | String (URI)               | The unique identifier of the Entity.                                                                                                                                             |
| *… all metadata fields depending on the entity class …*                               |                            |                                                                                                                                                                                  |
| proxies                                                                               | Array (Object (Proxy))     | The proxies represent a snapshot of the metadata that was aggregated from source and which will be consolidated into the main entity.                                            |
| **Proxy**                                                                             |                            |                                                                                                                                                                                  |
| id                                                                                    | String (URI)               | The unique identifier of the Entity.                                                                                                                                             |
| type                                                                                  | String                     | The type of the resource. Always set to "Proxy".                                                                                                                                 |
| *… all metadata fields obtained from the data source depending on the entity class …* |                            |                                                                                                                                                                                  |
| proxyFor                                                                              | String (URI)               | A reference to the entity that this Proxy corresponds to                                                                                                                         |
| proxyIn                                                                               | Object (Proxy Aggregation) | Represents the result of the aggregation of metadata of this entity from a specific data source.                                                                                 |
| **Proxy Aggregation**                                                                 |                            |                                                                                                                                                                                  |
| id                                                                                    | String (URI)               | The unique identifier of the aggregation corresponding to the associated Proxy.                                                                                                  |
| type                                                                                  | String                     | The type of the resource. Always set to "Aggregation".                                                                                                                           |
| created                                                                               | String (Datetime)          | The time at which the metadata was obtained from the source. <br/> The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'.                 |
| modified                                                                              | String (Datetime)          | The time at which the metadata was modified from the source, after creation. <br/> The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'. |
| rights                                                                                | String (URI)               | The uri of the rights statement that indicates the copyright, usage and access rights of the metadata of the entity.                                                             |
| source                                                                                | String (URI)               | The URI of the source vocabulary where the metadata for the entity was obtained from.                                                                                            |

</details>

# Supported classes of entities

There are five classes of entities supported by this API, namely: Agent, Place, Concept, TimeSpan and Organisation. The following subsection describe the metadata fields used to describe the entities.

## Agent

The Agent entity comprises people, either individually or in groups, who have the potential to perform intentional actions for which they can be held responsible.

<details>
<summary>The following fields are used to describe an Agent entity in JSON-LD:</summary>

|  **Field**              |  **Datatype**         |  **Description**                                                                                                        |
|:------------------------|:----------------------|:------------------------------------------------------------------------------------------------------------------------|
| **Agent**               |                       |                                                                                                                         |
| id                      | String (URI)          | The unique identifier of the Agent.                                                                                     |
| type                    | String                | The type of the entity. Always set to "Agent" for agents.                                                               |
| depiction               | Object (Web Resource) | A image resource where the entity is shown.                                                                             |
| isShownBy               | Object (Web Resource) | A image resource related to the entity.                                                                                 |
| prefLabel               | Object (LangMap)      | The preferred form of the name of the entity.                                                                           |
| altLabel                | Object (LangMap)      | Alternative forms of the name of the entity.                                                                            |
| dateOfBirth             | String                | The date the agent (person) was born.                                                                                   |
| dateOfEstablishment     | String                | The date on which the agent (corporate body) was established or founded.                                                |
| dateOfDeath             | String                | The date the agent (person) died.                                                                                       |
| dateOfTermination       | String                | The date on which the agent (corporate body) was terminated or dissolved.                                               |
| date                    | String                | A significant date associated with the agent.                                                                           |
| placeOfBirth            | String (URI)          | The town, city, province, state, and/or country in which a person was born.                                             |
| placeOfDeath            | String (URI)          | The town, city, province, state, and/or country in which a person died.                                                 |
| gender                  | String                | The gender with which the agent identifies.                                                                             |
| professionOrOccupation  | Array (String (URI))  | The profession or occupation in which the agent works or has worked.                                                    |
| biographicalInformation | Object (LangMap)      | Information pertaining to the life or history of the agent.                                                             |
| note                    | Object (LangMap)      | Information related to the entity.                                                                                      |
| isPartOf                | Array (String (URI))  | Reference to an agent that the described agent is part of.                                                              |
| hasPart                 | Array (String (URI))  | Reference to an Agent that is part of the Agent being described (e.g. part of a corporation).                           |
| hasMet                  | Array (String (URI))  | Reference to another entity which the Agent has “met” in a broad sense. For example a reference to a Place.             |
| isRelatedTo             | Array(String(URI))    | Reference to other entities, particularly other agents, with whom the agent is related in a generic sense.              |
| identifier              | String                | An identifier for the entity.                                                                                           |
| sameAs                  | Array (String (URI))  | URI of an equivalent entity in other vocabulary.                                                                        |
| inScheme                | Array (String (URI))  | The concept scheme(s) that this entity belongs to.                                                                      |
| isAggregatedBy          | Object (Aggregation)  | Represents the results of consolidating into a single representation the metadata obtained from different data sources. |

</details>

## Place

A physical location associated to a cultural heritage object. Presently, covers European countries and the most relevant places.

<details>
<summary>The following fields are used to describe a Place entity in JSON-LD:</summary>

|  **Field**       |  **Datatype**         |  **Description**                                                                                                        |
|:-----------------|:----------------------|:------------------------------------------------------------------------------------------------------------------------|
| **Place**        |                       |                                                                                                                         |
| id               | String (URI)          | The unique identifier of the Place.                                                                                     |
| type             | String                | The type of the entity. Always set to "Place" for places.                                                               |
| depiction        | Object (Web Resource) | A image resource where the entity is shown.                                                                             |
| isShownBy        | Object (Web Resource) | A image resource related to the entity.                                                                                 |
| prefLabel        | Object (LangMap)      | The preferred form of the name of the entity.                                                                           |
| altLabel         | Object (LangMap)      | Alternative forms of the name of the entity.                                                                            |
| lat              | Number                | The latitude coordinate of the Place.                                                                                   |
| long             | Number                | The longitude coordinate of the Place.                                                                                  |
| alt              | Number                | The altitude of the Place.                                                                                              |
| note             | Object (LangMap)      | Information related to the entity.                                                                                      |
| hasPart          | Array (String (URI))  | Reference to an agent that the described agent is part of.                                                              |
| isPartOf         | Array (String (URI))  | Reference to an Agent that is part of the Agent being described (e.g. part of a corporation).                           |
| isNextInSequence | Array (String (URI))  | Used to represent a sequence of Place entities over time e.g. the historical layers of the city of Troy.                |
| sameAs           | Array(String(URI))    | URI of an equivalent entity in other vocabulary.                                                                        |
| inScheme         | Array(String(URI))    | The concept scheme(s) that this entity belongs to.                                                                      |
| isAggregatedBy   | Object (Aggregation)  | Represents the results of consolidating into a single representation the metadata obtained from different data sources. |

</details>

## Time Span

A period of time having a beginning, an end and a duration. Presently, only centuries AD are available in the Entity Collection.

<details>
<summary>The following fields are used to describe a Time Span entity in JSON-LD:</summary>

|  **Field**       |  **Datatype**         |  **Description**                                                                                                                 |
|:-----------------|:----------------------|:---------------------------------------------------------------------------------------------------------------------------------|
| **Time Span**    |                       |                                                                                                                                  |
| id               | String (URI)          | The unique identifier of the Time Span.                                                                                          |
| type             | String                | The type of the entity. Always set to "TimeSpan".                                                                                |
| depiction        | Object (Web Resource) | A image resource where the entity is shown.                                                                                      |
| isShownBy        | Object (Web Resource) | A image resource related to the entity.                                                                                          |
| prefLabel        | Object (LangMap)      | The preferred form of the name of the entity.                                                                                    |
| altLabel         | Object (LangMap)      | Alternative forms of the name of the entity.                                                                                     |
| begin            | String                | The date the timespan started, represented in the form of an ISO 8601 date starting with the year and with hyphens (YYYY-MM-DD). |
| end              | String                | The date the timespan finshed represented in the form of an ISO 8601 date starting with the year and with hyphens (YYYY-MM-DD).  |
| note             | Object (LangMap)      | Information related to the entity.                                                                                               |
| isPartOf         | Array (String (URI))  | Reference to a timespan of which the described timespan is a part.                                                               |
| hasPart          | Array (String (URI))  | Reference to a timespan which is part of the described Timespan.                                                                 |
| isNextInSequence | Array (String (URI))  | Can be used to represent a sequence of periods of time.                                                                          |
| sameAs           | Array(String(URI))    | URI of an equivalent entity in other vocabulary.                                                                                 |
| inScheme         | Array(String(URI))    | The concept scheme(s) that this entity belongs to.                                                                               |
| isAggregatedBy   | Object (Aggregation)  | Represents the results of consolidating into a single representation the metadata obtained from different data sources.          |

</details>

## Concept

A Concept is defined as a unit of thought or meaning that comes from an organised knowledge base (such as subject terms from a thesaurus or controlled vocabulary) where URIs or local identifiers have been created to represent each concept.

<details>
<summary>The following fields are used to describe a Concept entity in JSON-LD:</summary>

|  **Field**     |  **Datatype**           |  **Description**                                                                                                                      |
|:---------------|:------------------------|:--------------------------------------------------------------------------------------------------------------------------------------|
| **Concept**    |                         |                                                                                                                                       |
| id             | String (URI)            | The unique identifier of the Concept.                                                                                                 |
| type           | String                  | The type of the entity. Always set to "Concept".                                                                                      |
| depiction      | Object (Web Resource)   | A image resource where the Conceptis shown.                                                                                           |
| isShownBy      | Object (Web Resource)   | A image resource related to the Concept.                                                                                              |
| prefLabel      | Object (LangMap)        | The preferred form of the name of the Concept.                                                                                        |
| altLabel       | Object (LangMap)        | Alternative forms of the name of the Concept.                                                                                         |
| note           | Object (LangMap)        | Information related to the Concept.                                                                                                   |
| notation       | Array (Datatype Object) | The notation in which the Concept is represented.                                                                                     |
| broader        | Array(String(URI))      | A broader concept in the same thesaurus or controlled vocabulary.                                                                     |
| narrower       | Array(String(URI))      | A narrower concept in the same thesaurus or controlled vocabulary.                                                                    |
| related        | Array(String(URI))      | A related concept in the same thesaurus or controlled vocabulary.                                                                     |
| broadMatch     | Array(String(URI))      | A broader matching concept from another thesaurus or controlled vocabulary.                                                           |
| narrowMatch    | Array(String(URI))      | A narrower matching concept from another thesaurus or controlled vocabulary.                                                          |
| relatedMatch   | Array(String(URI))      | A related matching concept from another thesaurus or controlled vocabulary.                                                           |
| closeMatch     | Array(String(URI))      | A close matching concept from another thesaurus or controlled vocabulary.                                                             |
| exactMatch     | Array(String(URI))      | URI of an equivalent Concept in other vocabulary.                                                                                     |
| inScheme       | Array(String(URI))      | The concept scheme(s) that this Concept belongs to.                                                                                   |
| isAggregatedBy | Object (Aggregation)    | Represents the results of consolidating into a single representation the metadata obtained from different data sources.               |
| proxies        | Array (Object (Proxy))  | The proxies represent a snapshot of the metadata that was aggregated from source and which will be consolidated into the main entity. |

</details>

## Organisation

The organisation providing data directly or via an aggregator.

<details>
<summary>The following fields are used to describe an Organisation entity in JSON-LD:</summary>

|  **Field**         |  **Datatype**                                |  **Description**                                                                                                                      |
|:-------------------|:---------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------|
| **Organisation**   |                                              |                                                                                                                                       |
| id                 | String (URI)                                 | The unique identifier of the Organisation.                                                                                            |
| type               | String                                       | The type of the entity. Always set to "Organization".                                                                                 |
| depiction          | Object (Web Resource)                        | A image resource where the Organisation is shown.                                                                                     |
| isShownBy          | Object (Web Resource)                        | A image resource related to the Organisation.                                                                                         |
| prefLabel          | Object (LangMap)                             | The preferred form of the name of the Organisation.                                                                                   |
| acronym            | Object (LangMap)                             | The acronym of the Organisation.                                                                                                      |
| altLabel           | Object (LangMap)                             | Alternative forms of the name of the Organisation.                                                                                    |
| hiddenLabel        | Array (String)                               | A lexical label not meant to be displayed.                                                                                            |
| description        | Object (LangMap)                             | A description for this Organisation.                                                                                                  |
| logo               | Object (WebResource)                         | A image resource of the logo for this Organisation.                                                                                   |
| europeanaRole      | Array (Object (Reference or Europeana Role)) | The role in Europeana for this Organisation.                                                                                          |
| country            | Object (Reference or Place)                  | The country of this Organisation                                                                                                      |
| language           | Array (String)                               | The official language(s) of the Organisation.                                                                                         |
| homepage           | String (URL)                                 | The homepage of the Organisation.                                                                                                     |
| phone              | String                                       | The phone number of the Organisation.                                                                                                 |
| mbox               | String                                       | The contact email address of the Organisation.                                                                                        |
| hasAddress         | Object (Address)                             | The address of the Organisation.                                                                                                      |
| aggregatesFrom     | Array (Object (Reference or Organisation))   | The Organisations that this Organisation aggregated from.                                                                             |
| aggregatedVia      | Array (Object (Reference or Organisation))   | The Organisations that aggregate content from this Organisation.                                                                      |
| identifier         | Arrray (String)                              | An identifier for the Organisation.                                                                                                   |
| sameAs             | Array (String(URI))                          | URI of an equivalent entity in other vocabulary or data source.                                                                       |
| isAggregatedBy     | Object (Aggregation)                         | Represents the results of consolidating into a single representation the metadata obtained from different data sources.               |
| proxies            | Array (Object (Proxy))                       | The proxies represent a snapshot of the metadata that was aggregated from source and which will be consolidated into the main entity. |
| **Address**        |                                              |                                                                                                                                       |
| id                 | String (URI)                                 | The unique identifier of the Address.                                                                                                 |
| type               | String                                       | The type of the entity. Always set to "Address".                                                                                      |
| streetAddress      | String                                       | The street address associated to the address of the Organisation.                                                                     |
| postalCode         | String                                       | The postal code associated to the address of the Organisation.                                                                        |
| postOfficeBox      | String                                       | The post office box associated to the address of the Organisation.                                                                    |
| locality           | String                                       | The city or locality associated to the address of the Organisation.                                                                   |
| countryName        | String                                       | The country associated to the address of the Organisation.                                                                            |
| hasGeo             | String (URI)                                 | The geo URI containing the latitude and longitude coordinates of the Organisation.                                                    |
| **Europeana Role** |                                              |                                                                                                                                       |
| id                 | String (URI)                                 | The unique identifier of the Role.                                                                                                    |
| type               | String                                       | The type of the entity. Always set to "Concept".                                                                                      |
| prefLabel          | Object (LangMap)                             | The preferred form of the name of the Role.                                                                                           |

</details>

## Other classes of resources that are common to all entities

<details>
<summary>The following classes and fields two classes are used as part of the enitty definitions in JSON-LD:</summary>

|  **Field**                                    |  **Datatype**        |  **Description**                                                                                                                                                                                                          |
|:----------------------------------------------|:---------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Web Resource (ie. depiction or isShownBy)** |                      |                                                                                                                                                                                                                           |
| id                                            | String               | The URL of the media resource                                                                                                                                                                                             |
| type                                          | String               | The type of the resource. Always set to "WebResource".                                                                                                                                                                    |
| source                                        | String               | The source where the media resource was obtained from, typically the identifier of a record.                                                                                                                              |
| thumbnail                                     | String               | The URL of a lower resolution thumbnail.                                                                                                                                                                                  |
| **Aggregation**                               |                      |                                                                                                                                                                                                                           |
| id                                            | String               | The identifier of the aggregation.                                                                                                                                                                                        |
| type                                          | String               | The type of the resource. Always set to "Aggregation".                                                                                                                                                                    |
| created                                       | String (Datetime)    | The time at which the entity was first created in Europeana. The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'.                                                                |
| modified                                      | String (Datetime)    | The time at which the metadata for the entity was modified as a result of an update from the source vocabulary or manually. The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'. |
| pageRank                                      | Number               | A non-negative integer specifying the page rank obtained from Wikidata for this resource.                                                                                                                                 |
| recordCount                                   | Integer              | A non-negative integer specifying the number of items in Europeana that refer to this entity.                                                                                                                             |
| score                                         | Number               | A non-negative integer specifying the score number to be used when ranking this entity in search, suggest and enrich methods.                                                                                             |
| aggregates                                    | Array (String (URI)) | The identifiers of all proxy aggregations from which the metadata for this entity was obtained from and consolidated.                                                                                                     |

</details>

# Getting Started

### What you need to know about this API:

- Adopts linked open data standards
- Supports JSON-LD and RDF/XML (only for retrieving entity data)
- Requires read access

# Retrieving an Entity

Retrieves all metadata available for a specific entity. This includes all labels (preferred, alternative or others when applicable), descriptive and contextual information such as references to other entities and also references to external data sources (ie. correferencing). For a full list of data fields, please see the [supported classes of entities](#supported-classes-of-entities) section.

### Request

```java
https://api.europeana.eu/entity/[TYPE]/[IDENTIFIER]
Accept: [ACCEPT]
```

```java
https://api.europeana.eu/entity/[TYPE]/[IDENTIFIER].[FORMAT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|:------------------|:-----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TYPE              | path             | The type of the entity. One of: “agent“, “place“, “concept“, “timespan“, “organization“                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| IDENTIFIER        | path             | The local identifier of the entity.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ACCEPT            | header           | Indicates the preferred format(s) via which the entity is to be represented if the format is accepted by the service. Both JSON-LD and RDF/XML are supported.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| FORMAT            | path             | Convenience method where the format is indicated as a path parameter instead of via the Accept header.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| profile           | query            | A parameter used to define the extent of the response. Two profiles are supported, “internal“ and “external“ (default). <br/><ul><li><p><strong>internal</strong>: Presents the available metadata for an entity and associated administrative information.   The metadata available for each entity is described in the <a href="https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2324561923#Supported-classes-of-entities" rel="nofollow"><span class="inline-comment-marker" data-ref="25132173-46a5-4f67-ac8f-cae3f8c9c557">Supported classes of entities</span> section</a>.</p></li><li><p><strong>external</strong>: Presents the internal view of metadata as described in <a href="https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2324561923#Internal-view-of-an-entity" rel="nofollow"><span class="inline-comment-marker" data-ref="47cd7bc3-09b8-4245-8e4b-1d9679c438a1">Internal view of an entity</span> section</a>, in addition to the information present in the external profile.</p></li></ul> |

### Response

<details>
<summary>Example Retrieve call</summary>

**Request**

`GET https://api.europeana.eu/entity/agent/base/147466`

**Response**

```java
{
"@context": "http://www.europeana.eu/schemas/context/entity.jsonld",
"id": "http://data.europeana.eu/agent/147466",
"type": "Agent",
"isShownBy": {
  "id": "http://atena.beic.it/webclient/DeliveryManager?pid=8366128&custom_att_2=deeplink",
  "type": "WebResource",
  "source": "http://data.europeana.eu/item/9200369/webclient_DeliveryManager_pid_8365778_custom_att_2_simple_viewer",
  "thumbnail": "https://api.europeana.eu/api/v2/thumbnail-by-url.json?uri=http%3A%2F%2Fatena.beic.it%2Fwebclient%2FDeliveryManager%3Fpid%3D8366399%26custom_att_2%3Ddeeplink&type=SOUND"
},
"prefLabel": {
  "de": "Arturo Toscanini",
  "fi": "Arturo Toscanini",
  "ru": "Артуро Тосканини",
  "sv": "Arturo Toscanini",
  "pt": "Arturo Toscanini",
  "bg": "Артуро Тосканини",
  "el": "Αρτούρο Τοσκανίνι",
  "en": "Arturo Toscanini",
  "hr": "Arturo Toscanini",
  "it": "Arturo Toscanini",
  "fr": "Arturo Toscanini",
  "hu": "Arturo Toscanini",
  "eu": "Arturo Toscanini",
  "sk": "Arturo Toscanini",
  "sl": "Arturo Toscanini",
  "ga": "Arturo Toscanini",
  "pl": "Arturo Toscanini",
  "ro": "Arturo Toscanini",
  "ca": "Arturo Toscanini",
  "nl": "Arturo Toscanini"
},
"altLabel": {
  "ru": [
    "Тосканини, Артуро"
  ]
},
"dateOfBirth": "1867-03-25",
"dateOfDeath": "1957-01-16",
"placeOfBirth": "http://data.europeana.eu/place/148579",
  "note": {
    "de": [
    "Italienischer Dirigent"
    ],
    "ru": [
    "Итальянский дирижёр"
    ],
    "fi": [
    "Italialainen kapellimestari"
    ],
    "sv": [
    "Italiensk dirigent"
    ],
    "bg": [
    "Италиански диригент"
    ],
    "el": [
    "Ιταλός διευθυντής ορχήστρας"
    ],
    "en": [
    "Italian conductor (1867-1957)"
    ],
    "it": [
    "Direttore d'orchestra italiano (1867-1957)"
    ],
    "fr": [
    "Chef d'orchestre italien"
    ],
    "pl": [
    "Dyrygent włoski"
    ],
    "hu": [
    "Olasz karmester"
    ],
    "nl": [
    "Italiaans dirigent"
    ]
  },
"hasMet": [
  "http://data.europeana.eu/concept/235"
],
"sameAs": [
  "http://www.wikidata.org/entity/Q13003",
  "http://viaf.org/viaf/19867298",
  "https://d-nb.info/gnd/118623443",
  "http://id.loc.gov/authorities/names/n50014549",
  "http://data.bnf.fr/ark:/12148/cb139005146",
  "http://www.idref.fr/027369293/id",
  "http://id.ndl.go.jp/auth/ndlna/00621569",
  "https://www.freebase.com/m/0140v2",
  "https://g.co/kg/m/0140v2",
  "http://openlibrary.org/works/OL5191079A",
  "http://libris.kb.se/resource/auth/313235",
  "http://datos.bne.es/resource/XX1282069",
  "http://data.bibliotheken.nl/id/thes/p072682442",
  "https://livedata.bibsys.no/authority/90606822",
  "http://id.worldcat.org/fast/4524",
  "http://data.cervantesvirtual.com/person/54819",
  "http://data.carnegiehall.org/names/10549",
  "https://libris.kb.se/mkz26r652wmwhm9",
  "http://dbpedia.org/resource/Arturo_Toscanini"
],
"isAggregatedBy": {
  "id": "http://data.europeana.eu/agent/147466#aggregation",
  "type": "Aggregation",
  "created": "2023-01-20T14:56:39Z",
  "modified": "2023-01-20T14:56:39Z",
  "pageRank": 36,
  "recordCount": 0,
  "score": 658,
  "aggregates": [
    "http://data.europeana.eu/agent/147466#aggr_europeana",
    "http://data.europeana.eu/agent/147466#aggr_source_1"
]
}
}
```

</details>

# Resolving an entity by using an external URI

The resolve method was designed to search for entities in the Entity Collection that match a given identifier used by an external source. The response redirects you to the corresponding Europeana Entity through its URI. In case there is no equivalent Entity in Europeana, an HTTP 404 is returned. This method makes use of the co-reference information typically present within owl:sameAs properties (or skos:exactMatch in the case of entities of type skos:Concept) for the lookup.

### Request

```java
https://api.europeana.eu/entity/resolve?uri=[URI]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                      |
|:------------------|:-----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URI               | query            | The external URI being used for entity lookup.                                                                                                                                        |
| ACCEPT            | header           | Indicates the preferred format(s) which will be used by content negotiation to redirect to either the Europeana website for display formats or this API for machine readable formats. |

### Response

On success, the method returns an HTTP 301 with the Europeana URI within the *Location* Header field.

<details>
<summary>Example Resolve call</summary>

**Request**

`GET https://api.europeana.eu/entity/resolve?wskey=apidemo&uri=http://dbpedia.org/resource/Leonardo_da_Vinci`

**Response**

`HTTP 301 data.europeana.eu/agent/146741`

</details>

# Search for an entity

Search for entities in the Entity Collection based on a given selection criteria.

### Request

```java
https://api.europeana.eu/entity/search
Accept: [ACCEPT]
```

|  **Parameter**         |  **Location**    |  **Description**                                                                                                                                                                                                                                                                                                                                                                                                                     |
|:-----------------------|:-----------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| query ***(required)*** | query            | The text or search criteria to be used for searching.                                                                                                                                                                                                                                                                                                                                                                                |
| qf                     | query            | A search query filter, ie. a filter is applied on the result list to remove unwanted results and therefore has no effect on ranking. This parameter can be used multiple types if more than one query filter is needed.                                                                                                                                                                                                              |
| type                   | query            | Used to restrict matching to a specific entity class, or otherwise match all entity classes if either 'all' or no type is indicated.                                                                                                                                                                                                                                                                                                 |
| scope                  | query            | Used to restrict matching to a specific scope of entities. The only possible value for the moment is 'europeana' to limit results to entities that are referenced in the main Europeana database.                                                                                                                                                                                                                                    |
| lang                   | query            | A two letter [ISO639 code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) of the language used for searching the text against. It also determines the data that will be returned for the entity description by keeping only the data that is qualifed with the requested language. <br/> *Available values* : en, nl, fr, de, es, sv, it, fi, da, el, cs, sk, sl, pt, hu, lt, pl, ro, bg, hr, lv, ga, mt, et, no, ca, ru, eu |
| profile                | query            | A parameter used to define the extent of the response. Only one profile is supported, namely “facets“. <br/><ul><li><p><strong>facets</strong>: Performs the faceting on the selected fields and presents the counts from the top most frequent value for a field to the lowest.</p></li></ul>                                                                                                                                       |
| page                   | query            | The number of the page (defaults to 1).                                                                                                                                                                                                                                                                                                                                                                                              |
| pageSize               | query            | The number of items to retrieve, maximum is 100, defaults to 10.                                                                                                                                                                                                                                                                                                                                                                     |
| sort                   | query            | A comma separated list of fields used for sorting the results. The field can be suffixed with the order in which the results are sorted, either 'asc' or 'desc' by the following: <field\_name>+<sort\_order>. The special keyword 'score' can be used to order by the ranking as determined by the search engine (which is the default).                                                                                            |
| facet                  | query            | A comma separated list of fields to be returned as facets for the given query.                                                                                                                                                                                                                                                                                                                                                       |

<details>
<summary>Example query</summary>

“Search for all organization entities that have the word ‘unternehmen’ in their metadata:

<https://api.europeana.eu/entity/search?&query=unternehmen&type=organization>

</details>

### Response

<details>
<summary>The response is a JSON-LD structure composed of the following fields:</summary>

|  **Field**             |  **Datatype**                |  **Description**                                                                           |
|:-----------------------|:-----------------------------|:-------------------------------------------------------------------------------------------|
| **Search Result Page** |                              |                                                                                            |
| id                     | String (URI)                 | The identifier of the search results page.                                                 |
| type                   | String                       | The type of the resource. Always set to "ResultPage".                                      |
| partOf                 | Object (Result List)         | The list of all results matching the search query.                                         |
| facets                 | Array (Object (Facet))       | The list of all facets that reflect the results that match the search query.               |
| total                  | Integer                      | The total number of entities in the result page.                                           |
| items                  | Array (Entity)               | The entities that are part of this result page.                                            |
| next                   | String (URI)                 | A reference to the previous page in the sequence of pages that make up the search results. |
| prev                   | String (URI)                 | A reference to the next page in the sequence of pages that make up the search results.     |
| **Search Result List** |                              |                                                                                            |
| id                     | String (URI)                 | The identifier of the search result list.                                                  |
| type                   | String                       | The type of the resource. Always set to "ResultList".                                      |
| total                  | Integer                      | The total number of results matching the search query.                                     |
| first                  | String (URI)                 | Indicates the first preceding page of results in the result list.                          |
| last                   | String (URI)                 | Indicates the furthest proceeding page of results in the result list.                      |
| **Facet**              |                              |                                                                                            |
| type                   | String                       | The type of the resource. Always set to "Facet".                                           |
| field                  | String                       | The name of the field being facetted.                                                      |
| values                 | Array (Object (Facet Value)) | The top most frequent values that were found in the field.                                 |
| **Facet Value**        |                              |                                                                                            |
| label                  | String                       | The value that was found in the field.                                                     |
| value                  | Integer                      | The total number of entities that contain this value in the field.                         |

</details>

# Roadmap and Changelog

The current version of the Entities API is 0.10.3 (December 2021) which has support for suggest, retrieval and resolution by external identifier. It is currently available as a Public [Alpha](https://pro.europeana.eu/page/intro#release-alpha), which is the first public version released primarily to get feedback from you. Do note that this means that changes can be introduced which could break backwards compatibility. It also means that to use this API you need a separate API key than for the other Europeana APIs. To see the changes made for the current version and also all previous releases, see the [API changelog in the project GitHub](https://github.com/europeana/entity-api/releases).
