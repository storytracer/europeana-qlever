---
tags:
  - '#apidocs'
---

[Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) > [API Suite](../API%20Suite.md)

# Search API Documentation

The Search API provides a way to **search for metadata records and media** on the Europeana repository. For example, you would use the Search API to get a response to the query *give me all the results for the word "Vermeer"*. Additionaly, it provides an alternative method using the [OpenSearch.RSS](#opensearch-rss) protocol for easier integration with external services.

The Search API is the easiest API to use and understand. It interacts with Europeana's data in much the same way as the [Europeana website](http://www.europeana.eu/) does. You can search for keywords, and the API will return all records that match that keyword. You can refine your search with more advanced filters and advanced [query syntax](#query-syntax). You can choose to only return objects with certain copyright statements, or you can choose to return the results in a language of your choice. This means that with the Search API, you can get a response to the query: 'Give me all objects by Vermeer that are openly licensed and have high-resolution images.'

Before starting to use this API, we recommend reading the [Page not accessible (ID: 2385313809)], [registering for an API key](https://pro.europeana.eu/get-api), and reading the [Terms of Use](https://www.europeana.eu/rights/terms-of-use). If you want to get started with this API, go to the [Getting Started](#getting-started) section or try some calls using our [Swagger Console](#swagger-console).

|                                                                                 |                                            |
|:--------------------------------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] [Get your API Key here](https://pro.europeana.eu/pages/get-api) <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                              |                                                                                              |
|:-----------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/search) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

---

- [Getting Started](#getting-started)
- [Query, Filter, and Faceting Fields](#query-filter-and-faceting-fields)
- [Reusability](#reusability)
- [Profiles](#profiles)
- [Metadata Sets](#metadata-sets)
- [Faceting](#faceting)
- [Pagination](#pagination)
- [Query Syntax](#query-syntax)
- [Open Search](#open-search)
- [Libraries and Plugins](#libraries-and-plugins)

---

## Getting Started

### Request

Every call to the Search API is an HTTPS request using the following base URL:

> [*https://api.europeana.eu/record/v2/search.json*](https://api.europeana.eu/record/v2/search.json)

On top of this base URL, you need two required parameters to make a successful Search API request: a *query*. to input these required parameters, use “query=” attached to that URL, using a question mark “?” to separate the parameters from the base URL and an ampersand “&” to separate parameters from each other

`api.europeana.eu/record/v2/search.json?query=Vermeer`

Below you’ll find a table with the other standard parameters you can use in your API Search request:

<details>
<summary>Search API Request Parameters</summary>

|  Parameter                  |  [Datatype](#datatype)    |  Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|:----------------------------|:--------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| query                       | String                    | The search term(s). See [Query Syntax](#query-syntax) for information on forming complex queries and examples.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| qf                          | String                    | Query Refinement. This parameter can be defined more than once. See [Query Syntax](#query-syntax) page for more information.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| [reusability](#reusability) | String                    | Filter by copyright status. Possible values are open, restricted or permission.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| media                       | Boolean                   | Filter by records where an URL to the full media file is present in the edm:isShownBy or edm:hasView metadata and is resolvable.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| thumbnail                   | Boolean                   | Filter by records where a thumbnail image has been generated for any of the WebResource media resources (thumbnail available in the edmPreview field).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| landingpage                 | Boolean                   | Filter by records where the link to the original object on the providers website (edm:isShownAt) is present and verified to be working.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| colourpalette               | String                    | Filter by images where one of the colours of an image matches the provided colour code. You can provide this parameter multiple times, the search will then do an ‘AND' search on all the provided colours. See: “[Colour Palette](#colour-palette)”                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| theme                       | String                    | Restrict the query over one of the Europeana [Thematic Collections](https://www.europeana.eu/themes). The possible values are: [archaeology](https://www.europeana.eu/themes/archaeology), [art](https://www.europeana.eu/themes/art), [fashion](https://www.europeana.eu/themes/fashion), [industrial](https://www.europeana.eu/themes/industrial-heritage), [manuscript](https://www.europeana.eu/themes/manuscripts), [map](https://www.europeana.eu/themes/maps-and-geography), [migration](https://www.europeana.eu/themes/migration), [music](https://www.europeana.eu/themes/music), [nature](https://www.europeana.eu/themes/natural-history), [newspaper](https://www.europeana.eu/themes/newspapers), [photography](https://www.europeana.eu/themes/photography), [sport](https://www.europeana.eu/themes/sport), [ww1](https://www.europeana.eu/themes/world-war-i). |
| sort                        | String                    | Sorting records in ascending or descending order of search fields. The following fields are supported: score (relevancy of the search result), timestamp\_created, timestamp\_update, europeana\_id, COMPLETENESS, is\_fulltext, has\_thumbnails, and has\_media. Sorting on more than one field is possible by using comma-separated values. It is also possible to randomly order items by using the keyword "random" instead of a field name. You can also request for a fixed random order by indicating a seed "random\_SEED" which is useful when paginating along the same randomized order. **Use:** field\_name+sort\_order. **Examples:** sort=timestamp\_update+desc sort=random+asc sort=random\_12345+asc                                                                                                                                                          |
| profile                     | String                    | A [profile](#profile) parameter which controls the format and richness of the response.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| rows                        | Number                    | The number of records to return. Maximum is 100. Defaults to 12. See [pagination](#pagination).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| start                       | Number                    | The item in the search results to start with when using [cursor-based pagination](#cursor-based-pagination). First item is 1. Defaults to 1.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| cursor                      | String                    | A cursor mark from where to start the search result set when using deep pagination. Set to \* to start [cursor-based pagination](#cursor-based-pagination).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| callback                    | String                    | Name of a client side callback function, see [API FAQ](../API%20FAQ.md).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

</details>

<details>
<summary>Example: Search for all openly licensed records with a direct link to the full media file:</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=Paris&reusability=open&media=true*](https://api.europeana.eu/record/v2/search.json?query=Paris&reusability=open&media=true)

</details>

### Response

A response from the Search API is always formatted in JSON and will contain fields that present information about the handling of the request, while the concrete information about the record is presented in the "items" field (see [Metadata Sets](#metadata-sets)).

<details>
<summary>Search API Response Parameters</summary>

|  Field        |  [Datatype](#datatype)    |  Description                                                                                                                                                                                                                                    |
|:--------------|:--------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| apikey        | String                    | the authentication parameter sent out by the client                                                                                                                                                                                             |
| action        | String                    | the name of the API method that was called                                                                                                                                                                                                      |
| success       | Boolean                   | a boolean (true/false) flag denoting the successful execution of the call                                                                                                                                                                       |
| statsDuration | Number                    | the time (in milliseconds) taken to serve the request                                                                                                                                                                                           |
| requestNumber | Number                    | a positive number denoting the number of request by this API key within the last 24 hours                                                                                                                                                       |
| params        | Object                    | The original request parameters. If an invalid request parameter was submitted, this response parameter will contain the default value (see individual calls for the default values). Shown up only if the profile parameter contains "params". |
| itemsCount    | Number                    | The number of retrieved records                                                                                                                                                                                                                 |
| totalResults  | Number                    | The total number of results                                                                                                                                                                                                                     |
| nextCursor    | String                    | Encoded string to pass along to the cursor to navigate to the next page in the search result set. See [Pagination](#pagination).                                                                                                                |
| items         | Array (Item)              | This is a collection of search results. Each item is represented by a summary of the metadata record. The actual content is dependent of the profile parameter.                                                                                 |
| facets        | Array (Facet)             | A collection of facets that describe the resultant dataset.                                                                                                                                                                                     |
| breadcrumbs   | Array (Breadcrumb)        | A collection of search queries that were applied in this call.                                                                                                                                                                                  |

</details>

### Error Responses

An error occurring during processing of an API method is reported by (1) a relevant HTTP status code, (2) a value of the success field and (3) a meaningful error message in the error field. The following table shows the fields appearing within an error response:

<details>
<summary>List of error responses</summary>

|  Field        |  [Datatype](#datatype)    |  Description                                                                      |
|:--------------|:--------------------------|:----------------------------------------------------------------------------------|
| apikey        | String                    | The authentication parameter sent out by the client                               |
| success       | Boolean                   | A boolean (true/false) flag denoting the successful execution of the call         |
| statsDuration | Number                    | The time (in milliseconds) taken to serve the request                             |
| error         | String                    | If the call was not successful, this fields will contain a detailed text message. |

</details>

The following kinds of error codes can be returned by the Record API:

<details>
<summary>List of Error codes the Record API can throw</summary>

|    HTTP Status Code  |  Description                                                                                                                                                                   |
|---------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|                 200  | The request was executed successfully.                                                                                                                                         |
|                 401  | Authentication credentials were missing or authentication failed.                                                                                                              |
|                 429  | The request could be served because the application has reached its usage limit.                                                                                               |
|                 500  | An error has occorred in the server which has not been properly handled. If you receive this error it means that something has gone really wrong, so please report them to us! |

</details>

<details>
<summary>Example: Request to the Search API supplying an invalid (unknown) API key</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=\**](https://api.europeana.eu/record/v2/search.json?query=*)

Response:

```java
{
    "apikey": "test",
    "success": false,
    "error": "Invalid API key"
}
```

</details>

## Query, Filter, and Faceting Fields

### Search Fields outside EDM

In addition to the fields defined in EDM, a handful of other administrative fields can also be used to search.

|  Search Field           |  [Datatype](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2385739812#Datatypes-for-Search-Fields)    |  Result Field                                |  Description                                                                                                                                                                                                                                 |
|:------------------------|:--------------------------------------------------------------------------------------------------------------------|:---------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| europeana\_id           | String                                                                                                              | id                                           | The Europeana ID of the record.                                                                                                                                                                                                              |
| timestamp               | Date                                                                                                                |                                              |                                                                                                                                                                                                                                              |
| timestamp\_created      | Date                                                                                                                | timestamp\_created timestamp\_created\_epoch | The date when record was created (formatted as [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601))                                                                                                                                            |
| timestamp\_update       | Date                                                                                                                | timestamp\_update timestamp\_update\_epoch   | The date when record was last updated (formatted as [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601))                                                                                                                                       |
| europeana\_completeness | Number                                                                                                              | europeanaCompleteness                        | An internal Europeana measure of the completeness of the metadata of the record, based on the availability of mandatory and optional schema fields. It is measured as a number from 1 to 10 and serves as indicator of the metadata quality. |
| COMPLETENESS            | String                                                                                                              | completeness                                 |                                                                                                                                                                                                                                              |

### Language-specific Search Fields

In EDM, most of the properties that accept a Literal may be language tagged, meaning the field has a tag that describes the language of the text using the [ISO 639-2](http://www.loc.gov/standards/iso639-2/php/code_list.php) standard. To allow for a language-specific search on such properties, the Search API defines a field for each of the language variations that appear in our repository while keeping the base field with all the values in all language variations. As opposed to the base field which typically has datatype Text (some fields may also be defined as String), the language-specific fields are always of type String to allow for faceting with the complete value (with no tokenization), see “datatypes for search fields” below for more details. If a language-specific field is part of a metadata set, it can also be output in the response (see “Language-Specific Result Fields” under the “[Metadata Sets](#metadata-sets)” Heading).

The following table shows the base and language-specific search fields for the dc:creator property:

|  Search Field                          |  Search Datatype    |  Result Field      |
|:---------------------------------------|:--------------------|:-------------------|
| [Page not accessible (ID: 2385313809)] | Text                | dcCreator          |
| proxy\_dc\_creator.\*                  | String              | dcCreatorLangAware |

### Search Fields defined in EDM

EDM defines an extensive list of classes and properties. In the Search API only a subset of these, corresponding to the ones found to be the most commonly used, can be used to search in the repository. These fields are listed in this section.

The ML (ie. multilingual) column of the table below marks the fields that have multilingual variations. To learn more about the type of information that these fields should hold, please refer to the [Page not accessible (ID: 2385313809)].

|  Search Field                                                                                   |  Search [Datatype](#datatype)    |  Result Field                        |  ML    |
|:------------------------------------------------------------------------------------------------|:---------------------------------|:-------------------------------------|:-------|
| [edm:ProvidedCHO](../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) |                                  |                                      |        |
| proxy\_dc\_contributor                                                                          | Text                             | dcContributor                        | ✓      |
| CONTRIBUTOR                                                                                     | String                           | dcContributor                        |        |
| proxy\_dc\_coverage                                                                             | String                           |                                      | ✓      |
| proxy\_dc\_creator                                                                              | Text                             | dcCreator dcCreatorLangAware         | ✓      |
| proxy\_dc\_date                                                                                 | String                           |                                      | ✓      |
| proxy\_dc\_description                                                                          | Text                             | dcDescription dcDescriptionLangAware | ✓      |
| proxy\_dc\_format                                                                               | Text                             |                                      | ✓      |
| proxy\_dc\_identifier                                                                           | String                           |                                      | ✓      |
| LANGUAGE                                                                                        | String                           | dcLanguage                           | ✓      |
| proxy\_dc\_publisher                                                                            | Text                             |                                      | ✓      |
| proxy\_dc\_rights                                                                               | String                           |                                      | ✓      |
| proxy\_dc\_source                                                                               | String                           |                                      | ✓      |
| proxy\_dc\_subject                                                                              | Text                             |                                      | ✓      |
| proxy\_dc\_title                                                                                | Text                             | dcTitleLangAware                     | ✓      |
| proxy\_dc\_type                                                                                 | String                           |                                      | ✓      |
| proxy\_dc\_type\_search                                                                         | Text                             |                                      | ✓      |
| proxy\_dcterms\_alternative                                                                     | String                           |                                      | ✓      |
| proxy\_dcterms\_created                                                                         | String                           |                                      | ✓      |
| proxy\_dcterms\_hasPart                                                                         | String                           | dctermsHasPart                       | ✓      |
| proxy\_dcterms\_isPartOf                                                                        | String                           | dctermsIsPartOf                      | ✓      |
| proxy\_dcterms\_issued                                                                          | String                           |                                      | ✓      |
| proxy\_dcterms\_medium                                                                          | Text                             |                                      | ✓      |
| proxy\_dcterms\_provenance                                                                      | String                           |                                      | ✓      |
| proxy\_dcterms\_spatial                                                                         | String                           | dctermsSpatial                       | ✓      |
| proxy\_dcterms\_temporal                                                                        | String                           |                                      | ✓      |
| proxy\_edm\_currentLocation                                                                     | String                           |                                      | ✓      |
| proxy\_edm\_hasMet                                                                              | String                           |                                      | ✓      |
| proxy\_edm\_isRelatedTo                                                                         | String                           |                                      | ✓      |
| TYPE                                                                                            | String                           | type                                 |        |
| YEAR                                                                                            | String                           | year                                 | ✓      |
| [ore:Aggregation](../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/ore_Aggregation.md) |                                  |                                      |        |
| DATA\_PROVIDER                                                                                  | String                           | edmDataProvider                      | ✓      |
| provider\_aggregation\_edm\_hasView                                                             | String                           |                                      |        |
| provider\_aggregation\_edm\_intermediateProvider                                                | String                           |                                      | ✓      |
| provider\_aggregation\_edm\_isShownAt                                                           | String                           | edmIsShownAt                         |        |
| provider\_aggregation\_edm\_isShownBy                                                           | String                           | edmIsShownBy                         |        |
| provider\_aggregation\_edm\_object                                                              | String                           | edmObject                            |        |
| PROVIDER                                                                                        | String                           | provider                             | ✓      |
| provider\_aggregation\_dc\_rights                                                               | String                           |                                      | ✓      |
| RIGHTS                                                                                          | String                           | rights                               | ✓      |
| UGC                                                                                             | Boolean                          | ugc                                  |        |
| edm\_previewNoDistribute                                                                        | Boolean                          | previewNoDistribute                  |        |
| [ore:Aggregation](../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/ore_Aggregation.md) |                                  |                                      |        |
| europeana\_collectionName[^1]                                                                   | String                           | europeanaCollectionName              |        |
| edm\_datasetName                                                                                | String                           | edmDatasetName                       |        |
| COUNTRY                                                                                         | String                           | country                              | ✓      |
| europeana\_aggregation\_edm\_language                                                           | String                           | language                             | ✓      |
| [edm:WebResource](../../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_WebResource.md) |                                  |                                      |        |
| edm\_webResource                                                                                | String                           |                                      |        |
| wr\_dc\_rights                                                                                  | String                           |                                      | ✓      |
| wr\_dcterms\_isReferencedBy                                                                     | String                           |                                      | ✓      |
| wr\_edm\_isNextInSequence                                                                       | String                           |                                      |        |
| wr\_edm\_rights                                                                                 | String                           |                                      | ✓      |
| wr\_svcs\_hasservice                                                                            | String                           |                                      | ✓      |
| [cc:License](../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/cc_License.md)     |                                  |                                      |        |
| wr\_cc\_license                                                                                 | String                           |                                      |        |
| provider\_aggregation\_cc\_license                                                              | String                           |                                      |        |
| provider\_aggregation\_odrl\_inherited\_from                                                    | String                           |                                      |        |
| wr\_cc\_odrl\_inherited\_from                                                                   | String                           |                                      |        |
| wr\_cc\_deprecated\_on                                                                          | Date                             |                                      |        |
| provider\_aggregation\_cc\_deprecated\_on                                                       | Date                             |                                      |        |
| [Page not accessible (ID: 2385313809)]                                                          |                                  |                                      |        |
| svcs\_service                                                                                   | String                           |                                      |        |
| sv\_dcterms\_conformsTo                                                                         | String                           |                                      |        |
| [edm:Agent](../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md)       |                                  |                                      |        |
| edm\_agent                                                                                      | String                           | edmAgent                             |        |
| ag\_skos\_prefLabel                                                                             | Text                             | edmAgentLabel                        | ✓      |
| ag\_skos\_altLabel                                                                              | Text                             |                                      | ✓      |
| ag\_foaf\_name                                                                                  | String                           |                                      | ✓      |
| ag\_rdagr2\_dateOfBirth                                                                         | String                           |                                      | ✓      |
| ag\_rdagr2\_dateOfDeath                                                                         | String                           |                                      | ✓      |
| ag\_rdagr2\_placeOfBirth                                                                        | Text                             |                                      | ✓      |
| ag\_rdagr2\_placeOfDeath                                                                        | Text                             |                                      | ✓      |
| ag\_rdagr2\_professionOrOccupation                                                              | String                           |                                      | ✓      |
| [skos:Concept](../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) |                                  |                                      |        |
| skos\_concept                                                                                   | String                           | edmConceptTerm                       |        |
| cc\_skos\_prefLabel                                                                             | String                           | edmConceptPrefLabel                  | ✓      |
| cc\_skos\_altLabel                                                                              | String                           |                                      | ✓      |
| [edm:Place](../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md)       |                                  |                                      |        |
| edm\_place                                                                                      | String                           | edmPlace                             |        |
| pl\_wgs84\_pos\_lat                                                                             | String                           | edmPlaceLatitude                     |        |
| pl\_wgs84\_pos\_long                                                                            | String                           | edmPlaceLongitude                    |        |
| pl\_wgs84\_pos\_alt                                                                             | String                           |                                      |        |
| pl\_skos\_prefLabel                                                                             | Text                             | edmPlaceLabel                        | ✓      |
| pl\_skos\_altLabel                                                                              | Text                             | edmPlaceAltLabel                     | ✓      |
| [edm:TimeSpan](../../EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_TimeSpan.md) |                                  |                                      |        |
| edm\_timespan                                                                                   | String                           | edmTimespan                          |        |
| ts\_skos\_prefLabel                                                                             | String                           | edmTimespanLabel                     | ✓      |
| ts\_skos\_altLabel                                                                              | String                           |                                      | ✓      |

**Notes:**

[^1]: This field has been deprecated with edmDatasetName. This change followed the change in EDM to rename to edm:collectionName to edm:datasetName. We will keep support for edmCollectionName for a grace period, but on January 2018, we will return only edmDatasetName so please update your API client.

### Aggregated Fields

Europeana aggregates its data from cultural institutions that can use diverse, fine-grained systems and methodologies. As a result, a link between for example an object and a person may be stored in different specialized fields. To provide simpler views on this data, Europeana has introduced several general Aggregated Fields, such as: title, who, what, when, and where. In these fields, we gather together information from different record fields to make the discovery of objects easier. Title, for example, aggregates data from the dc:title and dcterms:alternative fields which are part of Dublin Core, a popular general standard for describing different types of resources.

<details>
<summary>List of Aggregated Fields</summary>

|  Field Name    |  Search [Datatype](#datatype)    |  Fields being Aggregated                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|:---------------|:---------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| title          | Text                             | proxy\_dc\_title, proxy\_dcterms\_alternative                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| subject        | Text                             | proxy\_dc\_coverage, proxy\_dc\_subject, proxy\_dcterms\_spatial, proxy\_dcterms\_temporal                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| what           | Text                             | proxy\_dc\_format, proxy\_dc\_type, proxy\_dc\_subject, proxy\_dcterms\_medium, cc\_skos\_prefLabel, cc\_skos\_altLabel                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| when           | Text                             | proxy\_dcterms\_created, proxy\_dcterms\_temporal, proxy\_dc\_date, ts\_skos\_prefLabel, ts\_skos\_altLabel, proxy\_edm\_year, proxy\_dcterms\_issued                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| where          | Text                             | proxy\_dcterms\_spatial, pl\_skos\_prefLabel, pl\_skos\_altLabel                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| who            | Text                             | proxy\_dc\_contributor, proxy\_dc\_creator, ag\_skos\_prefLabel, ag\_skos\_altLabel, ag\_foaf\_name                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| text           | Text                             | provider\_aggregation\_edm\_dataProvider, provider\_aggregation\_edm\_intermediateProvider, provider\_aggregation\_edm\_provider, proxy\_dc\_contributor, proxy\_dc\_coverage, proxy\_dc\_creator, proxy\_dc\_date, proxy\_dc\_description, proxy\_dc\_format, proxy\_dc\_language, proxy\_dc\_publisher, proxy\_dc\_source, proxy\_dc\_subject, proxy\_dc\_title, proxy\_dc\_type, proxy\_dcterms\_alternative, proxy\_dcterms\_created, proxy\_dcterms\_issued, proxy\_dcterms\_medium, proxy\_dcterms\_provenance, proxy\_dcterms\_spatial, proxy\_dcterms\_temporal, proxy\_edm\_currentLocation, proxy\_edm\_type, ag\_skos\_altLabel, ag\_skos\_prefLabel, ag\_foaf\_name, ts\_skos\_altLabel, ts\_skos\_prefLabel, pl\_skos\_altLabel, pl\_skos\_prefLabel, cc\_skos\_altLabel, cc\_skos\_prefLabel, proxy\_dc\_type\_search |

</details>

### Media Search

The Search API allows not only to search on and retrieve metadata added by curators but also offers powerful features based on technical metadata. Technical metadata is metadata which is extracted from media files such as images and videos which are associated with records, such as the width and height of an image. This allows you to search for and filter Europeana records by media information, for instance to only search for records which have extra large images, high-quality audio files, or images that match a particular colour. Besides searching and filtering, faceting is also possible using technical metadata and is part of the default facets provided by the facet profile.

A Europeana metadata record can contain a reference to zero, one or more media files, this means that when a search is made on a technical metadata property or facet (such as image size), a record is returned if one of the media files present in the record match the search query. The following table lists the fields that relate to the metadata extracted from the media resources:

<details>
<summary>List of fields related to metadata extracted from media resources</summary>

|  Facet Name        |  [Datatype](#datatype)    |  Media Type    |  Description                                                                                                                                                                                                 |
|:-------------------|:--------------------------|:---------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| MEDIA              | Boolean                   |                | To indicate whether an URL to the full media file is present in the edm:isShownBy or edm:hasView metadata and is resolvable.                                                                                 |
| MIME\_TYPE         | String                    |                | Mime-type of the file, e.g. image/jpeg                                                                                                                                                                       |
| IMAGE\_SIZE        | String                    | Image          | Size in megapixels of an image, values: small (< 0.5MP), medium (0.5-1MP), large (1-4MP) and extra\_large (> 4MP)                                                                                            |
| IMAGE\_COLOUR      | Boolean                   | Image          | Lists 'true' for colour images. An alias to this facet is IMAGE\_COLOR, note that for non-colour images you cannot provide the 'false' value. Use the greyscale-facet instead.                               |
| IMAGE\_GREYSCALE   | Boolean                   | Image          | Lists 'true' for greyscale images. An alias to this facet is IMAGE\_GRAYSCALE, note that for colour images you cannot provide the 'false' value. Use the colour-facet instead.                               |
| COLOURPALETTE      | String                    | Image          | The most dominant colours present in images, expressed in HEX-colour codes. See [colour palette](#colour-palette).                                                                                           |
| IMAGE\_ASPECTRATIO | String                    | Image          | Portrait or landscape.                                                                                                                                                                                       |
| VIDEO\_HD          | Boolean                   | Video          | Lists 'true' for videos that have a resolution higher than 576p.                                                                                                                                             |
| VIDEO\_DURATION    | String                    | Video          | Duration of the video, values: short (< 4 minutes), medium (4-20 minutes) and long (> 20 minutes).                                                                                                           |
| SOUND\_HQ          | Boolean                   | Sound          | Lists 'true' for sound files where the bit depth is 16 or higher or if the file format is a lossless file type (ALAC, FLAC, APE, SHN, WAV, WMA, AIFF & DSD). Note that 'false' does not work for this facet. |
| SOUND\_DURATION    | String                    | Sound          | Duration of the sound file, values: very\_short (< 30 seconds), short (30 seconds - 3 minutes), medium (3-6 minutes) and long (> 6 minutes).                                                                 |
| TEXT\_FULLTEXT     | Boolean                   | Text           | Lists 'true' for text media types which are searchable, e.g. a PDF with text.                                                                                                                                |

</details>

### Colour palette

From all records with images, the six most prominent colours are extracted. These colours are then mapped to one of the 120 colours that can be found in the listing [here](http://www.w3.org/TR/css3-color/#svg-color). To search for records where one of the images matches a particular colour you can use the colour palette parameter, you can provide it multiple times. You need to provide a Hex rgb code as value, such as #8A2BE2 or #FFE4C4.

### Datatypes for Search Fields

The following datatypes are defined for the search fields used for querying, filtering and faceting.

<details>
<summary>List of Datatypes that a search field might hold</summary>

|  Datatype    |  Description                                                                                                                                                                                                                                                   |
|:-------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Boolean      | A true or false value.                                                                                                                                                                                                                                         |
| Number       | A numeric value, typically with integer precision.                                                                                                                                                                                                             |
| Date         | A point in time with millisecond precision. See Section X to learn more on how to query date fields.                                                                                                                                                           |
| String       | Values are preserved as they are present in the data, with no additional NLP processing. This datatype is typically more usefull for faceting.                                                                                                                 |
| Text         | A word tokenized with punctuation filtering and case sensitive value, with additional [stemming](https://nlp.stanford.edu/IR-book/html/htmledition/stemming-and-lemmatization-1.html) of words. This datatype is typically usefull for querying and filtering. |

</details>

## Reusability

The possible values of the reusability parameter are shown in the following Table:

<details>
<summary>Table of Reusability parameter values</summary>

|  Value     |                                                                               |  Description                                                                                                         |
|:-----------|:------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------|
| open       | The records are freely reusable.                                              |                                                                                                                      |
|            | [PDM](http://creativecommons.org/publicdomain/mark/1.0/)                      | Creative Commons - Public Domain Mark <http://creativecommons.org/publicdomain/mark/1.0/>                            |
|            | [CC0](http://creativecommons.org/publicdomain/zero/1.0/)                      | Creative Commons - Public Domain Dedication                                                                          |
|            | [CC BY](http://creativecommons.org/licenses/by/1.0/)                          | Creative Commons - Attribution                                                                                       |
|            | [CC BY-SA](http://creativecommons.org/licenses/by-sa/1.0/)                    | Creative Commons - Attribution ShareAlike                                                                            |
| restricted | The records are reusable, but with restrictions.                              |                                                                                                                      |
|            | [CC BY-NC](http://creativecommons.org/licenses/by-nc/1.0/)                    | Creative Commons - Attribution NonCommercial                                                                         |
|            | [CC BY-NC-SA](http://creativecommons.org/licenses/by-nc-sa/1.0/)              | Creative Commons - Attribution NonCommercial ShareAlike                                                              |
|            | [CC BY-NC-ND](http://creativecommons.org/licenses/by-nd-nc/1.0/)              | Creative Commons - Attribution NoDerivs NonCommercial                                                                |
|            | [CC BY-ND](http://creativecommons.org/licenses/by-nd/1.0/)                    | Creative Commons - Attribution NoDerivs                                                                              |
|            | [~~OOC-NC~~](http://www.europeana.eu/rights/out-of-copyright-non-commercial/) | Out of Copyright - Non Commercial re-use (RETIRED)                                                                   |
|            | [InC-EDU](http://rightsstatements.org/vocab/InC-EDU/1.0/)                     | Rights Statements - In Copyright - Educational Use Permitted                                                         |
|            | [NoC-NC](http://rightsstatements.org/vocab/NoC-NC/1.0/)                       | Rights Statements - No Copyright - Non-Commercial Use Only                                                           |
|            | [NoC-OKLR](http://rightsstatements.org/vocab/NoC-OKLR/1.0/)                   | Rights Statements - No Copyright - Other Known Legal Restrictions                                                    |
| permission | You can reuse the records only with explicit permission.                      |                                                                                                                      |
|            | [~~RR-F~~](http://www.europeana.eu/rights/rr-f/)                              | Rights Reserved - Free Access (RETIRED)                                                                              |
|            | [~~RR-P~~](http://www.europeana.eu/rights/rr-p/)                              | Rights Reserved - Paid Access (RETIRED) [http://www.europeana.eu/rights/rr-p/](http://www.europeana.eu/rights/rr-r/) |
|            | [~~RR-R~~](http://www.europeana.eu/rights/rr-r/)                              | Rights Reserved - Restricted Access (RETIRED) <http://www.europeana.eu/rights/rr-r/>                                 |
|            | [~~Unknown~~](http://www.europeana.eu/rights/unknown/)                        | Unknown Copyright Status (RETIRED)                                                                                   |
|            | [RS InC](http://rightsstatements.org/vocab/InC/1.0/)                          | Rights Statements - In Copyright                                                                                     |
|            | [RS InC-OW-EU](http://rightsstatements.org/vocab/InC-OW-EU/1.0/)              | Rights Statements - In Copyright - EU Orphan Work                                                                    |
|            | [RS CNE](http://rightsstatements.org/vocab/CNE/1.0/)                          | Rights Statements - Copyright not Evaluated                                                                          |

</details>

<details>
<summary>Example: Search only for freely reusable records:</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=Paris&reusability=open*](https://api.europeana.eu/record/v2/search.json?query=Paris&reusability=open&wskey=YOURAPIKEY)

</details>

## Profiles

A profile typically determines how extensive the response will be, by either dictating the metadata fields that will be present (ie. minimal, standard and rich) or appending additional data elements such as facets or breadcrumbs. Most facets can be combined with the exception of the metadata facets or combined facets such as rich. The following table lists the profiles supported by the API:

<details>
<summary>List of possible Profile parameter values</summary>

|  Profile                    |  Description                                                                                                                             |
|:----------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------|
| minimal                     | Returns minimal [set of metadata](#set-of-metadata).                                                                                     |
| standard                    | Returns a broader set of metadata.                                                                                                       |
| rich                        | Returns the broadest set of metadata.                                                                                                    |
| [facets](#facets)           | Information about [Facets](#facets) is added. For the records the Standard profile is used.                                              |
| [breadcrumbs](#breadcrumbs) | information about the query is added in the form of breadcrumbs. Facets are added as well; for the records the Standard profile is used. |
| params                      | The header of the response will contain a params key, which lists the requested and default parameters of the API call.                  |
| portal                      | *standard*, *facets*, and *breadcrumb* combined, plus additional fields.                                                                 |

</details>

### Breadcrumbs

A collection of search queries that were applied to your call.

<details>
<summary>List of Breadcrumb fields</summary>

|  Field    |  [Datatype](#datatype)    |  Description                                                            |
|:----------|:--------------------------|:------------------------------------------------------------------------|
| display   | String                    | Human-readable description of the search                                |
| param     | String                    | The search parameter name (\*\*query\*\* or \*\*qf\*\*)                 |
| value     | String                    | The search parameter value                                              |
| href      | String                    | The search part of the URL which can be reused in further calls         |
| last      | Boolean                   | Boolean value indicating whether the current breadcrumb is the last one |

</details>

## Metadata Sets

Each item in a search result is represented by a subset of the fields from the corresponding metadata record. The extent of the fields that are present is determined by the [Profile](#profile) chosen.

### Result Fields outside EDM

In addition to the fields defined in EDM, a handful of other fields were defined for administrative reasons that are output in the response.

<details>
<summary>List of Result fields outside EDM</summary>

|  Result Field             |  Description                                                                                       |
|:--------------------------|:---------------------------------------------------------------------------------------------------|
| guid                      | A link to the object page on the Europeana portal to be used by client applications.               |
| link                      | A link to the API object call. This link should be used to retrieve the full metadata object.      |
| title                     | The main and alternative titles of the item.                                                       |
| score                     | The relevancy score calculated by the search engine. Depends of the query.                         |
| timestamp                 | ?                                                                                                  |
| timestamp\_created\_epoch | UNIX timestamp of the date when record were created                                                |
| timestamp\_update\_epoch  | UNIX timestamp of the date when record were last updated                                           |
| timestamp\_created        | [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format of the date when record were created      |
| timestamp\_update         | [ISO 8601](http://en.wikipedia.org/wiki/ISO_8601) format of the date when record were last updated |

</details>

### Language-specific Result Fields

The same way as there are separate [language-specific fields for searching](#language-specific-fields-for-searching), there is also a way to distinguish language-specific values for the response. Such fields always end with the suffix "LangAware" and are represented as LangMap. In order to preserve backwards compatibility we have not changed the original fields. This means that fields such as title, description and creator now appear twice in the search response, one with their original field name (dcTitle) and one as a multilingual labelled list (dcTitleLangAware). In the future, we will replace the single-value fields with the correct multilingual ones.

The following table shows the base and language-specific result fields for the dc:creator property:

|  Result Field                          |  Result [Datatype](#datatype)    |  Search Field         |
|:---------------------------------------|:---------------------------------|:----------------------|
| [Page not accessible (ID: 2385313809)] | Array (String)                   | proxy\_dc\_creator    |
| [Page not accessible (ID: 2385313809)] | LangMap                          | proxy\_dc\_creator.\* |

### Result Fields

The table below lists all the fields that are output by the search divided per profile (metadata set).

<details>
<summary>Table of all Response Result fields</summary>

|  Result Field                |  JSON [Datatype](#datatype)    |  [Search Field](#search-field)           |
|:-----------------------------|:-------------------------------|:-----------------------------------------|
| Minimal [Profile](#profile)  |                                |                                          |
| id                           | String                         | europeana\_id                            |
| link                         | String                         |                                          |
| guid                         | String                         |                                          |
| edmPreview                   | Array (String)                 |                                          |
| edmIsShownBy                 | Array (String)                 | provider\_aggregation\_edm\_isShownBy    |
| edmIsShownAt                 | Array (String)                 | provider\_aggregation\_edm\_isShownAt    |
| title                        | Array (String)                 | title                                    |
| dcTitleLangAware             | LangMap                        | proxy\_dc\_title.\*                      |
| dcDescription                | Array (String)                 | proxy\_dc\_description                   |
| dcDescriptionLangAware       | LangMap                        | proxy\_dc\_description                   |
| dcCreator                    | Array (String)                 | proxy\_dc\_creator                       |
| dcCreatorLangAware           | LangMap                        | proxy\_dc\_creator.\*                    |
| edmPlaceLatitude             | Array (String)                 | pl\_wgs84\_pos\_lat                      |
| edmPlaceLongitude            | Array (String)                 | pl\_wgs84\_pos\_long                     |
| type                         | String                         | TYPE                                     |
| year                         | Array (String)                 | YEAR                                     |
| provider                     | Array (String)                 | PROVIDER                                 |
| dataProvider                 | Array (String)                 | provider\_aggregation\_edm\_dataProvider |
| rights                       | Array (String)                 | RIGHTS                                   |
| europeanaCompleteness        | Number                         | COMPLETENESS                             |
| score                        | Number                         | score                                    |
| Standard [Profile](#profile) |                                |                                          |
| previewNoDistribute          | Boolean                        | edm\_previewNoDistribute                 |
| edmConceptTerm               | Array (String)                 | skos\_concept                            |
| edmConceptPrefLabel          | Array (LangMap)                | cc\_skos\_prefLabel                      |
| edmConceptPrefLabelLangAware | LangMap                        | cc\_skos\_prefLabel.\*                   |
| edmConceptBroaderTerm        | Array (String)                 | cc\_skos\_broader                        |
| edmConceptBroaderLabel       | Array (LangMap)                | cc\_skos\_broader                        |
| edmTimespanLabel             | Array (LangMap)                | ts\_skos\_prefLabel                      |
| edmTimespanLabelLangAware    | LangMap                        | ts\_skos\_prefLabel.\*                   |
| ugc                          | Array (Boolean)                | UGC                                      |
| completeness                 | Number                         | COMPLETENESS                             |
| country                      | Array (String)                 | COUNTRY                                  |
| europeanaCollectionName[^1]  | Array (String)                 | europeana\_collectionName                |
| edmDatasetName               | Array (String)                 | edm\_datasetName                         |
| edmPlaceAltLabel             | ???                            | pl\_skos\_altLabel                       |
| edmPlaceAltLabelLangAware    | LangMap                        | pl\_skos\_altLabel.\*                    |
| dcLanguage                   | Array (String)                 | proxy\_dc\_language                      |
| dctermsIsPartOf              | Array (String)                 | proxy\_dcterms\_isPartOf                 |
| timestamp                    | Number                         | timestamp                                |
| timestampCreated             | String                         | timestamp\_created                       |
| timestampUpdate              | String                         | timestamp\_update                        |
| language                     | Array (String)                 | LANGUAGE                                 |
| Portal [Profile](#profile)   |                                |                                          |
| dctermsSpatial               | Array (String)                 | proxy\_dcterms\_spatial                  |
| edmPlace                     | Array (String)                 | edm\_place                               |
| edmTimespan                  | Array (String)                 | edm\_timespan                            |
| edmAgent                     | Array (String)                 | edm\_agent                               |
| edmAgentLabel                | Array (LangMap)                | ag\_skos\_prefLabel                      |
| dcContributor                | Array (String)                 | proxy\_dc\_contributor                   |
| Rich [Profile](#profile)     |                                |                                          |
| edmLandingPage               |                                | europeana\_aggregation\_edm\_landingPage |

[^1]: This field has been deprecated with edmDatasetName. This change followed the change in EDM to rename to edm:collectionName to edm:datasetName. Starting from January 2018, we will return only edmDatasetName . Please update your API client.

</details>

### JSON Datatypes

The JSON output of this API uses the following datatypes:

<details>
<summary>List of data types that are used in the JSON Output</summary>

|  Datatype    |  Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Boolean      | true or false                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Number       | integer or double precision floating-point number                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| String       | double-quoted Unicode, with backslash escaping                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Array        | an ordered sequence of values, comma-separated and enclosed in square brackets; the values do not need to be of the same type                                                                                                                                                                                                                                                                                                                                                                                          |
| Object       | an unordered collection of key:value pairs with the ':' character separating the key and the value, comma-separated and enclosed in curly braces; the keys must be strings and should be distinct from each other                                                                                                                                                                                                                                                                                                      |
| LangMap      | A special datatype to provide values in various languages. It is an associative array where the keys are ISO language codes or "def" (where the language is not given), and the value is an array of strings. For example: `"dcTitle": {"por": ["Paris"]}`. Here the datatype of dcTitle is a LanguageMap: the language code is "por" (stands for Portuguese), and the value is a list with only one element: "Paris". For those familiar with Java notations: is it the JSON equivalent of `Map<String,List<String>>` |

</details>

<details>
<summary>Example: Include the broadest set of metadata in the search response:</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=Paris&profile=rich*](https://api.europeana.eu/record/v2/search.json?query=Paris&profile=rich)

</details>

## Faceting

The number of records that Europeana contains is very big and growing. Therefore we need efficient ways to allow our users to discover what they need easily. One such technique is a faceted indexing system that classifies each record along multiple dimensions. The facets, seen on the side of europeana.eu, can be useful for filtering search results and can also be used by API clients. If you conduct a search for the keyword "paris" and have a look at the TYPE facet, this facet would tell how many items exist within your search result grouped by TYPE (such as IMAGE, VIDEO etc.). All search fields can also be faceted on.

When you search within your result set for a specific facet, the other items in your facet would still exist (if you search for TYPE:IMAGE, then you can still see how many results there are for TYPE:VIDEO etc.). This last functionality, called multi-facets, is not supported for the Technical Metadata fields.

### Requesting Facets

Facets can be requested by either setting the facets or the portal profiles with the [profile ](#profile)parameter. By default, a predefined set of facets is returned corresponding to the facets seen on the side of the europeana.eu, which correspond to the following search fields:

- TYPE, LANGUAGE, COMPLETENESS, CONTRIBUTOR, COUNTRY, DATA\_PROVIDER, LANGUAGE, PROVIDER, RIGHTS, UGC, YEAR, COLOURPALETTE, MIME\_TYPE, REUSABILITY, IMAGE\_SIZE, SOUND\_DURATION, VIDEO\_DURATION, TEXT\_FULLTEXT, LANDINGPAGE, MEDIA, THUMBNAIL, IMAGE\_ASPECTRATIO, IMAGE\_COLOUR, VIDEO\_HD, SOUND\_HQ

### Facet objects in the Response

When requested, facets appear on the response within the facets field as an Array of Facet objects, which are composed by the following fields:

<details>
<summary>List of Response fields when using the facet profile</summary>

|  Result Field    |  JSON Datatype      |  Description                                                           |
|:-----------------|:--------------------|:-----------------------------------------------------------------------|
| Facet Object     |                     |                                                                        |
| name             | String              | The name of the field being facetted, e.g. COUNTRY                     |
| fields           | Array (Facet Value) | A collection of values for the given facet.                            |
| Facet Value      |                     |                                                                        |
| label            | String              | The value that was found within the field of one or more objects.      |
| count            | Number              | The number of objects for which the value was found within that field. |

</details>

<details>
<summary>Example: Requesting default facets for all Europeana records</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=\*&rows=0&profile=facets*](https://api.europeana.eu/record/v2/search.json?query=*&rows=0&profile=facets)

Response:

```java
{
  "apikey": "YOURAPIKEY",
  "success": true,
  "requestNumber": 999,
  "totalResults": 62029238,
  "items": [],
  "facets": [
    {
      "name": "RIGHTS",
      "fields": [
        {
          "label": "http://rightsstatements.org/vocab/InC/1.0/",
          "count": 21135772
        },
        ...
        {
          "label": "http://creativecommons.org/licenses/by-nc-nd/3.0/de/",
          "count": 2732
        }
      ]
    }
    ...
  ]
}

```

</details>

### Individual Facets

It is also possible to select which facets to retrieve beyond (or instead of) the default facet set, via the `facet` parameter.

|  Parameter    |  Datatype    |  Description                                                      |
|:--------------|:-------------|:------------------------------------------------------------------|
| facet         | String       | A name of an individual field or a comma separated list of fields |

The value of the parameter could be "DEFAULT" (which is a shortcut for the default facet set) or any [search field](#search-field). A remainder that search fields with datatype Text are indexed as tokenized terms which imply that facet values and counts will reflect such terms as opposed to the whole value (ie. phrase) like in the remaining datatypes. This is the reason why the [language-specific search fields](#language-specific-search-fields) were added with type string so that faceting could be done on the complete values. These are the fields actually used by the Europeana Collections Portal to display the facet values on the side.

*We have aligned the logic for faceting across all fields in the API output to be consistent. Previously, faceting on the 'default' facets (such as TYPE, or RIGHTS) would use a different logic than faceting on custom fields (such as proxy\_dc\_creator). The difference is that now all other values in a list of facet values are returned (multi-facet).*

<details>
<summary>Example: Requesting an individual facet</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=\*&facet=LANGUAGE&profile=facets&rows=0*](https://api.europeana.eu/record/v2/search.json?query=*&facet=LANGUAGE&profile=facets&rows=0)

</details>

<details>
<summary>Example: Requesting the default plus an additional individual facet</summary>

Request:

> [https://api.europeana.eu/record/v2/search.json?query=\*&facet=DEFAULT+proxy\_dc\_rights+proxy\_dcterms\_medium&profile=facets&rows=0](https://api.europeana.eu/record/v2/search.json?query=*&facet=DEFAULT+proxy_dc_rights+proxy_dcterms_medium&profile=facets&rows=0)

</details>

### Multiple Individual Facets

A client can request one or more facets in a single query. This can be done by either duplicating the facet parameter or by combining all the fields needed for faceting as a comma-separated String.

<details>
<summary>Example: requesting multiple facets by duplicating the facet parameter.</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=\*&facet=skos\_concept&facet=proxy\_dcterms\_medium&profile=facets&rows=0*](https://api.europeana.eu/record/v2/search.json?query=*&facet=skos_concept&facet=proxy_dcterms_medium&profile=facets&rows=0)

</details>

<details>
<summary>Example: requesting multiple facets using a comma-separated list.</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=\*&facet=skos\_concept,proxy\_dcterms\_medium&profile=facets&rows=0*](https://api.europeana.eu/record/v2/search.json?query=*&facet=skos_concept,proxy_dcterms_medium&profile=facets&rows=0)

</details>

### Offset and limit for Facets

A client can request how many facet values to retrieve, and which should be the first one. These parameters can be used to page over all facet values without requesting too many facet values at a time. The table below explains these two parameters. The FACET\_NAME constant stands for the field for which the limit applies.

<details>
<summary>facet offset and limit parameters</summary>

|  Parameter                   |  Datatype    |  Description                                                                                                                                                                                                                                                        |
|:-----------------------------|:-------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| f.[FACET\_NAME].facet.limit  | Number       | Number of values an individual facet should contain. Set a limit of "0" to not return anything for that facet. By default, the limit of values of an individual facet is 50. This can be overriden by setting a custom limit e.g. via `&f.DEFAULT.facet.limit=100`. |
| f.[FACET\_NAME].facet.offset | Number       | The offset of the first value in an individual facet. The default offset value is "0", starting from the first item in the list while value "1" offsets the list by one, so the first item to return is the second and so on.                                       |

</details>

<details>
<summary>Example: Requesting for faceting on the PROVIDER field using offset and limit.</summary>

Request:

> [*https://api.europeana.eu/record/v2/search.json?query=paris&profile=facets&facet=PROVIDER&f.PROVIDER.facet.offset=10&f.PROVIDER.facet.limit=30&rows=0*](https://api.europeana.eu/record/v2/search.json?query=paris&profile=facets&facet=PROVIDER&f.PROVIDER.facet.offset=10&f.PROVIDER.facet.limit=30&rows=0)

</details>

## Pagination

The Search API offers two ways of paginating through the result set: basic and cursor-based pagination. The basic pagination is suitable for smaller or user-facing browsing applications which allows for the iteration over the first 1000 results using the start parameter. For larger and/or harvesting applications, the API offers the capability to use cursor-based pagination which allows for a quick iteration over the entire result set.

|  Pagination    |  Capabilities                                                                                                                                                                                                                                                 |  Implementation                                                                                                                                                                                                                                                                                                                     |
|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Basic          | Allows to go to a specific offset/page (start=X). Limited to the first 1000 results (start + rows).                                                                                                                                                           | Use the start parameter to set the search result offset, default value is 1.                                                                                                                                                                                                                                                        |
| Cursor-based   | Quickly iterate over the entire result set. Does not allow you to go to a specific offset. Cannot be used in conjunction with the start parameter. Based on [Solr Cursor Pagination](https://cwiki.apache.org/confluence/display/solr/Pagination+of+Results). | Set the cursor parameter to \* to start cursor-based pagination at page 1. Take the nextCursor value from the response and pass it to the cursor parameter to paginate to the next page (you will need to urlescape the key). When the nextCursor value is not returned anymore, you have reached the end of the search result set. |

## Query Syntax

Europeana uses the Apache Solr platform to index its data and therefore Apache Lucene Query Syntax is inherently supported by the Search API, although the Solr eDismax query parser is the one currently used by default in the search engine. Advanced users are encouraged to use Lucene and Apache SOLR guides to get the most out of the Europeana repository. For others, we supply a basic guide for querying Europeana.

### Basic and phrase search

To look for records that contain a search term in one of the data fields, provide the term as a **query** parameter:

Syntax: "Mona Lisa"

> [*https://api.europeana.eu/record/v2/search.json?query="Mona Lisa"*](https://api.europeana.eu/record/v2/search.json?query=%22Mona%20Lisa%22)

Note that like in many other search applications omitting the quotes will result in searching for records that contain the term *Mona* and the term *Lisa* but not necessarily both of them together or in that order. We can allow the existence of a number of other words in between by adding that number after the quotes. For example, searching by “Peter Rubens”~1 will return objects about Peter Rubens but also about Peter Paul Rubens.

### **Search by fields**

If you want to limit your search to a specific data field you should provide the name of the field using the following syntax. Use parentheses ( ) to group the keywords to search for in that field. For example, to look for objects whose creator is *Leonardo da Vinci*:

Syntax: who:("Leonardo da Vinci")

> [*https://api.europeana.eu/record/v2/search.json?query=who:("Leonardo da Vinci")*](https://api.europeana.eu/record/v2/search.json?query=who:(%22Leonardo%20da%20Vinci%22))

### Boolean Search

To combine several terms in one search one can use boolean operators AND, OR, and NOT (note the case-sensitivity). Use parentheses to group logical conditions. Note that two consecutive terms without any boolean operator in between default to the AND operator.

Syntax: mona AND lisa

> [*https://api.europeana.eu/record/v2/search.json?query=mona+AND+lisa*](https://api.europeana.eu/record/v2/search.json?query=mona+AND+lisa)

Boolean operators can also be combined with the search by fields. The following example searches for objects whose location is in *Paris* or in *London*:

Syntax: where:(Paris OR London)

> [*https://api.europeana.eu/record/v2/search.json?query=where:(Paris+OR+London)*](https://api.europeana.eu/record/v2/search.json?query=where:(Paris+OR+London))

The boolean NOT operator excludes results that contain the specified word/s after it. For example, looking for objects which contain the term *Lisa* but do not contain the term *Mona* is done by the following:

Syntax: lisa NOT mona

> [*https://api.europeana.eu/record/v2/search.json?query=lisa+NOT+mona*](https://api.europeana.eu/record/v2/search.json?query=lisa+NOT+mona)

### Wildcard search

If you are not sure of the spelling of the search terms, you can use wildcards such as \* or ? These will work on all words, but not in the first letter of the word.

- Wildcard - \* - will find words with any number of letters in the place of the asterisk, for example ca\* will find cat, cap, cane, cable, and canary.
- Wildcard - ? - a single letter wildcard, for example ca?e will find cane, care, case etc.
- You can use the tilde symbol - ~ - to find results with a similar spelling. For example, searching Nicolas~ will also include words Nicholaus, Nicolaas, Nikolaus, Nicola, Nicolai

Syntax: Nicolas~

> [*https://api.europeana.eu/record/v2/search.json?query=Nicolas~*](https://api.europeana.eu/record/v2/search.json?query=Nicolas~)

### Range search

To execute range queries, the range operator should be used. This example will search for objects whose field values fall between **a** and **z**:

Syntax: [a TO z]

> [*https://api.europeana.eu/record/v2/search.json?query=[a TO z]*](https://api.europeana.eu/record/v2/search.json?query=%5Ba%20TO%20z%5D)

As well as for textual fields it can also be used for numeric values, date ranges, or geographical areas, as shown below. Make sure you URLEncode these queries before putting them in a browser, since the square brackets cannot be part of a URL without being encoded first!

### Geographical Bounding Box Search

To search for objects by their geographic location you should specify the bounding box of the area. You need to use the range operator and the **pl\_wgs84\_pos\_lat** (latitude position) and **pl\_wgs84\_pos\_long** (longitude position) field. The following example will bring all the objects found between the latitude of 45° and 47° and between the longitude of 7° and 8°:

Syntax: pl\_wgs84\_pos\_lat:[45 TO 47] AND pl\_wgs84\_pos\_long:[7 TO 8]

> [*https://api.europeana.eu/record/v2/search.json?query=pl\_wgs84\_pos\_lat:[45 TO 47] AND pl\_wgs84\_pos\_long:[7 TO 8]*](https://api.europeana.eu/record/v2/search.json?query=pl_wgs84_pos_lat%3A%5B45%20TO%2047%5D%20AND%20pl_wgs84_pos_long%3A%5B7%20TO%208%5D)

### Timestamp Search

One can also search objects by date. Currently, full-fledge date search is supported only for the fields storing the creation (timestamp\_created) and update (timestamp\_update) dates of the objects in our database, which are available in two formats: the UNIX epoch timestamp and the ISO 8601 formatted date. To search for objects created or updated on a given date, use the following query:

Syntax: timestamp\_created:"2013-03-16T20:26:27.168Z"

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_created:"2013-03-16T20:26:27.168Z"*](https://api.europeana.eu/record/v2/search.json?query=timestamp_created:"2013-03-16T20:26:27.168Z")

Syntax: timestamp\_update:"2013-03-16T20:26:27.168Z"

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_update:"2013-03-16T20:26:27.168Z"*](https://api.europeana.eu/record/v2/search.json?query=timestamp_update:"2013-03-16T20:26:27.168Z")

### Searching for date range (as [date1 TO date2]):

Syntax: timestamp\_created:[2013-11-01T00:00:0.000Z TO 2013-12-01T00:00:00.000Z]

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_created:[2013-11-01T00:00:0.000Z TO 2013-12-01T00:00:00.000Z]*](https://api.europeana.eu/record/v2/search.json?query=timestamp_created%3A%5B2013-11-01T00%3A00%3A0.000Z%20TO%202013-12-01T00%3A00%3A00.000Z%5D)

Syntax: timestamp\_update:[2013-11-01T00:00:0.000Z TO 2013-12-01T00:00:00.000Z]

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_update:[2013-11-01T00:00:0.000Z TO 2013-12-01T00:00:00.000Z]*](https://api.europeana.eu/record/v2/search.json?query=timestamp_update%3A%5B2013-11-01T00%3A00%3A0.000Z%20TO%202013-12-01T00%3A00%3A00.000Z%5D)

### Date mathematics

With date mathematics you can formulate questions such as "in the last two months" or "in the previous week". The basic operations and their symbols are addition (+), substraction (-) and rounding (/). Some examples:

- now = NOW
- tomorrow: NOW+1DAY
- one week before now: NOW-1WEEK
- the start of current hour: /HOUR
- the start of current year: /YEAR

The date units are: YEAR, YEARS, MONTH, MONTHS, DAY, DAYS, DATE, HOUR, HOURS, MINUTE, MINUTES, SECOND, SECONDS, MILLI, MILLIS, MILLISECOND, MILLISECONDS (the plural, singular, and abbreviated forms refer to the same unit).

Let's see how to apply it in Europeana's context.

From xxx up until now

Syntax: timestamp\_created:[xxx TO NOW]

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_created:[2014-05-01T00:00:00.000Z TO NOW]*](https://api.europeana.eu/record/v2/search.json?query=timestamp_created%3A%5B2014-05-01T00%3A00%3A00.000Z%20TO%20NOW%5D)

From xxx up until yesterday

Syntax: timestamp\_created:[xxx TO NOW-1DAY]

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_created:[2014-05-01T00:00:00.000Z TO NOW-1DAY]*](https://api.europeana.eu/record/v2/search.json?query=timestamp_created%3A%5B2014-05-01T00%3A00%3A00.000Z%20TO%20NOW-1DAY%5D)

Changes in the last two months

Syntax: [NOW-2MONTH/DAY TO NOW/DAY]

> [*https://api.europeana.eu/record/v2/search.json?query=timestamp\_created:[NOW-2MONTH/DAY TO NOW/DAY]*](https://api.europeana.eu/record/v2/search.json?query=timestamp_created%3A%5BNOW-2MONTH%2FDAY%20TO%20NOW%2FDAY%5D)

You can find more about date mathematics at [Solr's API documentation](http://lucene.apache.org/solr/4_6_0/solr-core/org/apache/solr/util/DateMathParser.html)

### Query Refinements

So far we have dealt with examples where there was only one query parameter. Sometimes it is useful to split a query into a variable and a constant part. For instance, for an application that accesses only objects located in London, it is possible to have the constant part of the query pre-selecting London-based objects and the variable part selecting objects within this pre-selection.

This can be done using the refinement parameter **qf** which is appended to the request, besides the **query** parameter. This example looks for objects which contain the term *Westminster* and their location is in *London*:

Syntax: query=Westminster & qf=where:London

> [*https://api.europeana.eu/record/v2/search.json?query=Westminster&qf=where:London*](https://api.europeana.eu/record/v2/search.json?query=Westminster&qf=where:London)

Currently, we can also filter the results by distance using the function *distance* in the parameter *qf.* This example will look for objects with the words *world war* that are located (the object itself or the spatial topic of the resource) in a distance of 200 km to the point with latitude 47 and longitude 12.

Syntax: query=world+war & qf=distance(location,47,12,200)

> [*https://api.europeana.eu/record/v2/search.json?query=world+war&qf=distance(location,47,12,200)*](https://api.europeana.eu/record/v2/search.json?query=world+war&qf=distance(location,47,12,200))

We can also use more specific fields instead of location: currentLocation (with coordinates from edm:currentLocation), and coverageLocation (with coordinates from dcterms:spatial and dc:coverage). For example, *qf=distance(currentLocation,47,12,200)* will filter the results to those actually located within 200 km of the coordinates indicated.

### Sorting

The search results are, by default, ranked by relevance according to their similarity with the contents of the query parameter. It is possible however to use the parameter ***sort*** to arrange them according to one or more fields, in ascending or descending order. This example looks for objects containing the words *mona* and *lisa*, but sort them according to the field YEAR in ascending order:

Syntax: query=mona+lisa & sort=YEAR+asc

> [*https://api.europeana.eu/record/v2/search.json?query=mona+lisa&sort=YEAR+asc*](https://api.europeana.eu/record/v2/search.json?query=mona+lisa&sort=YEAR+asc)

When we refine by distance (i.e., qf=distance(...)), we can also include *distance+asc* or *distance+desc* in the sorting parameter in order to rank the results by the distance to the coordinates.

Syntax: query=world+war & qf=distance(location,47,12,200) & sort=distance+asc

> [*https://api.europeana.eu/record/v2/search.json?query=world+war&qf=distance(location,47,12,200)&sort=distance+asc*](https://api.europeana.eu/record/v2/search.json?query=world+war&qf=distance(location,47,12,200)&sort=distance+asc)

Refinement and sorting parameters can be concatenated. Each such parameter and the mandatory query parameter contributes a [breadcrumb](#breadcrumb) object if breadcrumbs are specified in the search profile.

## Open Search

Basic search function following the [OpenSearch](http://www.opensearch.org/) specification, returning the results in XML (RSS) format. This method does not support facet search or profiles. The names of parameters are different from other API call methods, because they match the OpenSearch standard. The OpenSearch response elements can be used by search engines to augment existing XML formats with search-related metadata. The signature of the method is as follows:

> [*https://api.europeana.eu/record/opensearch.rss?searchTerms=TERMS&count=COUNT&startIndex=START*](https://api.europeana.eu/record/opensearch.rss?searchTerms=TERMS&count=COUNT&startIndex=START)

The following parameters are supported by this method:

<details>
<summary>List of OpenSearch parameters</summary>

|  **Parameter**    |  **Datatype**    |  **Description**                                                                                                                                                                                                  |
|:------------------|:-----------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| searchTerms       | String           | The search terms used to query the Europeana repository, similar to the query parameter in the search method.                                                                                                     |
| count             | Number           | The number of search results to return; possible values can be any integer up to 100 [default = 12].                                                                                                              |
| startIndex        | Number           | The first object in the search result set to start with (first item = 1), e.g., if a result set is made up of 100 objects, you can set the first returned object to the specific object in the set [default = 1]. |

</details>

For the response, see [OpenSearch](http://www.opensearch.org/Specifications/OpenSearch/1.1#OpenSearch_response_elements) specification.

## Libraries and Plugins

Apart from the console, there is a multitude of other ways you can interact with the API. On the libraries and plugins page, you can find libraries that allow you to develop applications with the API in your programming language of choice. Plugins make it easy to integrate the Europeana API into existing applications, such as Wordpress or Google Docs.

<https://pro.europeana.eu/page/api-libraries-and-plugins>

### Deprecation Information

The following will be deprecated per the given date, ensure that your API clients are updated accordingly:

|  Date        |  Deprecation Details                                                                                                                                                                                      |
|:-------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| January 2018 | As the API supports HTTPS now for a while, we will start to redirect all non-HTTPS traffic for the API to HTTPS. Ensure your applications follow redirects if needed or adjust the hostname to use HTTPS. |

### Roadmap and Changelog

We deploy new versions of this API quite regularly, but not all new versions result in changes in the interface. To see the changes made for this version and also all previous releases, see the [API changelog in the project GitHub](https://github.com/europeana/api2/releases/).

![image-20260209-173522.png](../../../attachments/2f04fb30-2a35-4b53-93d6-ccf9f09669e6.png)
