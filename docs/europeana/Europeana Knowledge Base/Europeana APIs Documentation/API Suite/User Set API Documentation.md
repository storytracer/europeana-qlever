
# User Set API Documentation

The User Set API allows users to create and maintain their own collection of items (sets) that are available in Europeana. Besides creating sets, users can also search for sets that were created by other users and are available for public viewing. This API supports the gallery functionality that is available in the Europeana website for logged-in users but also, favorite items and curated items for “entity” collections.

|                                                                 |                                            |
|:----------------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] [Get your API Key here](#get-your-api-key-here) <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                           |                                                                                              |
|:--------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/set) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

- [Notice](#notice)
- [Retrieval](#retrieval)
  - [Retrieving user set metadata](#retrieving-user-set-metadata)
  - [Retrieving items within a user set](#retrieving-items-within-a-user-set)
- [Discovery](#discovery)
  - [Search for items within a user set](#search-for-items-within-a-user-set)
  - [Search for user sets](#search-for-user-sets)
- [Provision](#provision)

# **Notice**

We have been working towards a first official version of this API.

As part of this process, as of 23rd April 2025, we have release the beta version of this API.

The following changes were made to this API which are not backwards compatible:

- The creation, retrieval and update of a set no longer allows items to be included. These methods are now expected to manipulate the metadata of a set. It is now expected that the dedicated methods for retrieval, insertion, update or deletion of items are used to access or manage the items within a set. This differentiation was made to prevent inadvertitly making changes to the contents of the set. If you need to create a set with items, you will need to make 2 requests: one to create the empty set and a second request to insert the items.
- The profiles used for determining the extent of the metadata returned in the response to a retrieval or search requests have been reviewed and changed to make them more intuitive to users.
- The numbering of pages for pagination requests and search results now start at 1 (instead of 0) to follow a more natural and intuitive numbering.

# Retrieval

Methods for accessing either the metadata of a user set or the metadata of the items that are part of the user set. Considering that the number of items that are part of the user may be relatively high, it was decided to separate the user set metadata from the item metadata retrieval and to offer a paginated approach to accessing the information about the items that are part of the user set.

## Retrieving user set metadata

Retrieves all metadata available for a specific user set. This includes all descriptive metadata but leaves out the contents of the set.

### Request

```java
https://api.europeana.eu/set/[IDENTIFIER]
Accept: [ACCEPT]
```

```java
https://api.europeana.eu/set/[IDENTIFIER].[FORMAT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                |
|:------------------|:-----------------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| `IDENTIFIER`      | path             | The local identifier of the user set.                                                                                                           |
| `ACCEPT`          | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported. |
| `FORMAT`          | path             | Convenience method where the format is indicated as a path parameter instead of via the Accept header.                                          |

### Response

On success, the method returns a HTTP 200 with the metadata of the user set.

<details>
<summary>The response is a JSON-LD structure composed of the following fields:</summary>

|  **Field**    |  **Datatype**        |  **Description**                                                                                                                                                                                                                                                                                  |
|:--------------|:---------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **User Set**  |                      |                                                                                                                                                                                                                                                                                                   |
| `@context`    | String (URL)         | The JSON-LD context                                                                                                                                                                                                                                                                               |
| `id`          | String (URI)         | The unique identifier of the user set                                                                                                                                                                                                                                                             |
| `type`        | String               | The type of the user set. By default all user sets are classified as 'Collection'. <br/> The 'BookmarkFolder' and 'EntityBestItemsSet' are types that are used to support specific functionality in the Europeana Website.                                                                        |
| `visibility`  | String               | Access visibility of the user set. The possible states are “private”, “public” and “published”. The default value assigned at the creation of the set when omitted is “private”. For “BookmarkFolder” sets, the visibility is immutable and cannot be changed to another value besides “private”. |
| `title`       | Object (LangMap)     | Name given by the user to the set.                                                                                                                                                                                                                                                                |
| `description` | Object (LangMap)     | A summary of the content and topics of the user set.                                                                                                                                                                                                                                              |
| `subject`     | Array (String (URI)) | Overall topical content of the items in the set. These topics are restricted to URIs of the Europeana Entities. This property is repeatable when several subjects apply to the whole set.                                                                                                         |
| `pinned`      | Integer              | The number of pinned items in the “EntityBestItemsSet” (only applicable for this kind of set). This is a temporary field while a more suitable option is found to handle user suggestions for Entities.                                                                                           |
| `creator`     | Object (User)        | Refers to a registered user which is the creator and owner of the set.                                                                                                                                                                                                                            |
| `contributor` | Array (String (URI)) | Refers to the registered users which have requested changes to the set. The API will list the URIs of all users that co-created the set.                                                                                                                                                          |
| `provider`    | Object (Provider)    | Holds a reference to an Organisation entity in Europeana or the URL of the project page in Europeana Pro together with the project name.                                                                                                                                                          |
| `created`     | String (Datetime)    | The time at which the set was created by the user. The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'.                                                                                                                                                  |
| `modified`    | String (Datetime)    | The time at which the set was modified, after creation. The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'.                                                                                                                                             |
| `issued`      | String (Datetime)    | The time at which the set was published for a wider audience in the Europeana website. The value must be a Literal expressed as xsd:dateTime with the UTC timezone expressed as 'Z'.                                                                                                              |
| `isDefinedBy` | String (URL)         | Defines a search request to the Search API which selects the items that are part of the Set (only relevant for open sets).                                                                                                                                                                        |
| `total`       | Integer              | A non-negative integer specifying the total number of items that are contained within this set.                                                                                                                                                                                                   |
| `first`       | String (URL)         | Indicates the first preceding page of items in the set.                                                                                                                                                                                                                                           |
| `last`        | String (URL)         | Indicates the furthest proceeding page of the set.                                                                                                                                                                                                                                                |
| **User**      |                      |                                                                                                                                                                                                                                                                                                   |
| `id`          | String (URI)         | The unique identifier of the user in Europeana.                                                                                                                                                                                                                                                   |
| `type`        | String               | The type of the resource. Always set to "Person".                                                                                                                                                                                                                                                 |
| `nickname`    | String               | The username of the user. For privacy reasons, this is the only personal information made publicly available.                                                                                                                                                                                     |
| **Provider**  |                      |                                                                                                                                                                                                                                                                                                   |
| `id`          | String (URI)         | Holds a reference to an Organisation entity in Europeana or the URL of the project page in Europeana Pro.                                                                                                                                                                                         |
| `type`        | String               | The type of the resource. Always set to "Organization".                                                                                                                                                                                                                                           |
| `name`        | String               | The name of the project that contributed the set.                                                                                                                                                                                                                                                 |

</details>

## Retrieving items within a user set

Retrieves a limit number of items contained within a specific user set. This method is used to traverse through the complete list of items within the user set by requesting each page of items at a time. Use the 'page' and 'pageSize' parameters to navigate or follow the links in the 'next' or 'prev' properties to navigate respectively to the next or previous page.

### Request

```java
https://api.europeana.eu/set/[IDENTIFIER]?page=[PAGE]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:------------------|:-----------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `IDENTIFIER`      | path             | The local identifier of the user set.                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `page`            | query            | The number of the page starting with page 1 (defaults to 1).                                                                                                                                                                                                                                                                                                                                                                                               |
| `pageSize`        | query            | The number of items to retrieve, maximum is 100, defaults to 10.                                                                                                                                                                                                                                                                                                                                                                                           |
| `profile`         | query            | A parameter used to define the extent of the response. The following profiles are available: <br/> `meta`: Presents the information about the set and set page except for the items. <br/> `items`(default): Presents the information of the set page plus the identifiers of the items (ie. Records) that are part of the Set page. <br/> `items.default`: Presents the same information as for `items` but applying the default profile for the records. |
| `ACCEPT`          | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported.                                                                                                                                                                                                                                                                                                            |

### Response

On success, the method returns a HTTP 200 with a subset of items of the user set.

<details>
<summary>The response is a JSON-LD structure composed of the following fields:</summary>

|  **Field**                                                                               |  **Datatype**                        |  **Description**                                                                                               |
|:-----------------------------------------------------------------------------------------|:-------------------------------------|:---------------------------------------------------------------------------------------------------------------|
| **User Set Page**                                                                        |                                      |                                                                                                                |
| @context                                                                                 | String (URL)                         | The JSON-LD context                                                                                            |
| id                                                                                       | String (URI)                         | The unique identifier of the page of items                                                                     |
| type                                                                                     | String                               | The type of the page of items. Always set to 'CollectionPage'.                                                 |
| partOf                                                                                   | Object (Collection)                  | The user set to which this page belongs. Only the subset of information for navigating the itens is presented. |
| startIndex                                                                               | Integer                              | A non-negative integer specifying the position in sequence of the first item in the user set page.             |
| total                                                                                    | Integer                              | A non-negative integer specifying the total number of items in the user set page.                              |
| items                                                                                    | Array (String(URI) or Object(Item) ) | The metadata for, or a reference to, the items that are part of the set page.                                  |
| prev                                                                                     | String (URL)                         | A reference to the previous page in the sequence of pages that make up the set.                                |
| next                                                                                     | String (URL)                         | A reference to the next page in the sequence of pages that make up the set.                                    |
| **Collection**                                                                           |                                      |                                                                                                                |
| id                                                                                       | String (URI)                         | The unique identifier of the user set.                                                                         |
| type                                                                                     | String                               | The type of the resource. Always set to "Collection".                                                          |
| total                                                                                    | Integer                              | A non-negative integer specifying the total number of items that are contained within this set.                |
| first                                                                                    | String (URL)                         | Indicates the first preceding page of items in the set.                                                        |
| last                                                                                     | String (URL)                         | Indicates the furthest proceeding page of the set.                                                             |
| **Item**                                                                                 |                                      |                                                                                                                |
| id                                                                                       | String (URI)                         | The unique identifier of a record in Europeana                                                                 |
| … metadata for the item (see Search API documentation for an overview of the metadata) … |                                      |                                                                                                                |

</details>

# Discovery

Methods for searching for items that are part of a user set or to search across all user sets that are available in Europeana.

## Search for items within a user set

Search for items contained within a user set based on a given selection criteria. This method is paginated similar to the listing method. Use the 'page' and 'pageSize' parameters to navigate or follow the links in the 'next' or 'prev' properties to navigate, respectively, to the next or previous page.

**Fields available for search:**

- `item`: using local identifier of the record contained within the set

**No sort or faceting is available**

### Request

```java
https://api.europeana.eu/set/[IDENTIFIER]/search?query=[QUERY]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|:------------------|:-----------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `IDENTIFIER`      | path             | The local identifier of the user set.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `query`           | query            | The text to be used for searching. Always set to the wildcard value (ie. '\*') for content search.                                                                                                                                                                                                                                                                                                                                                                                                        |
| `qf`              | query            | A search query filter. This parameter can be used multiple types if more than one query filter is needed.                                                                                                                                                                                                                                                                                                                                                                                                 |
| `profile`         | query            | A parameter used to define the extent of the response. The following profiles are available: <br/> `meta`: Presents the information about the search result list without the actual results (only the size). <br/> `items`(default): Presents the information about the search result list plus the identifiers of the items (ie. Records) that are part of the search result page. <br/> `items.default`: Presents the same information as for `items` but applying the default profile for the records. |
| `page`            | query            | The number of the page starting with page 1 (defaults to 1).                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `pageSize`        | query            | The number of items to retrieve, maximum is 100, defaults to 10.                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `ACCEPT`          | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported.                                                                                                                                                                                                                                                                                                                                                           |

### Response

On success, the method returns a HTTP 200 with a subset of items that are part of the user set and match the search criteria.

<details>
<summary>The response is a JSON-LD structure composed of the following fields:</summary>

|  **Field**               |  **Datatype**        |  **Description**                                                                                                                                         |
|:-------------------------|:---------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------|
| **(Search) Result Page** |                      |                                                                                                                                                          |
| @context                 | String (URL)         | The JSON-LD context                                                                                                                                      |
| id                       | String (URI)         | The identifier of the search results page.                                                                                                               |
| type                     | String               | The type of the page of items. Always set to 'ResultPage'.                                                                                               |
| partOf                   | Object (ResultList)  | The complete list of items that match the search query. Only the subset of information for navigating the items in the search results list is presented. |
| total                    | Integer              | A non-negative integer specifying the total number of items in the search results page.                                                                  |
| items                    | Array (String (URI)) | The reference to the items that are part of the search results page.                                                                                     |
| prev                     | String (URL)         | A reference to the next page in the sequence of pages that make up the search results.                                                                   |
| next                     | String (URL)         | A reference to the previous page in the sequence of pages that make up the search results.                                                               |
| **(Search) Result List** |                      |                                                                                                                                                          |
| id                       | String (URI)         | The identifier of the search results.                                                                                                                    |
| type                     | String               | The type of the resource. Always set to "ResultList".                                                                                                    |
| total                    | Integer              | The total number of items matching the search query.                                                                                                     |
| first                    | String (URL)         | Indicates the first preceding page of items in the result list.                                                                                          |
| last                     | String (URL)         | Indicates the furthest proceeding page of items in the result list.                                                                                      |

</details>

## Search for user sets

Search for user sets based on a given selection criteria. This method is paginated similar to the listing method. Use the 'page' and 'pageSize' parameters to navigate or follow the links in the 'next' or 'prev' properties to navigate, respectively, to the next or previous page.

**Fields available for search (query and filter):**

- `set_id`: the local identifier of the Set
- `creator`: using local identifier or URI
- `contributor`: using local identifier or URI
- `visibility`: with value `published`, `public`, `private`
- `type`: with value `Collection` or `BookmarkFolder`, or `EntityBestItemsSet`)
- `item`: with the local identifier of the record contained within the set)
- `subject`: with the URI
- `lang`: a two-letter code reflecting the language in which the Set is described

### Request

```java
https://api.europeana.eu/set/search?query=[QUERY]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|:------------------|:-----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `IDENTIFIER`      | path             | The local identifier of the user set.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `query`           | query            | The text to be used for searching.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `qf`              | query            | A search query filter, ie. a filter is applied on the result list to remove unwanted results and therefore has no effect on ranking. This parameter can be used multiple types if more than one query filter is needed.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `profile`         | query            | A parameter used to define the extent of the response. The following profiles are available: <br/> `meta`: Presents the information about the search result list without the actual results (only the size). <br/> `items`(default): Presents the information about the search result list including the identifier of the Sets that are part of the page. <br/> `items.default`: Presents the information about the search result list plus the metadata for the Sets that are part of the page. <br/> `facets`: Presents the facets. Only `items` value is supported which returns the nr of times each item is shared accross the result list. |
| `sort`            | query            | A comma separated list of fields used for sorting the results. The field can be suffixed with the order in which the results are sorted, either 'asc' or 'desc' by the following: <field\_name>+<sort\_order>. The special keyword 'score' can be used to order by the ranking as determined by the search engine (which is the default). <br/> Only the following fields are available for sorting: <br/><ul><li><p><code>modified</code></p></li><li><p><code>score</code></p></li></ul>                                                                                                                                                        |
| `page`            | query            | The number of the search result page (defaults to 1).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `pageSize`        | query            | The number of user sets to retrieve, maximum is 100, defaults to 10.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `ACCEPT`          | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

### Response

On success, the method returns a HTTP 200 with a subset of user sets that match the search criteria.

<details>
<summary>The response is a JSON-LD structure composed of the following fields:</summary>

|  **Field**               |  **Datatype**                       |  **Description**                                                                                                                                             |
|:-------------------------|:------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **(Search) Result Page** |                                     |                                                                                                                                                              |
| `@context`               | String (URL)                        | The JSON-LD context                                                                                                                                          |
| `id`                     | String (URI)                        | The identifier of the search results page.                                                                                                                   |
| `type`                   | String                              | The type of the page of items. Always set to 'ResultPage'.                                                                                                   |
| `partOf`                 | Object (ResultList)                 | The complete list of user sets that match the search query. Only the subset of information for navigating the items in the search results list is presented. |
| `total`                  | Integer                             | A non-negative integer specifying the total number of user sets in the search results page.                                                                  |
| `items`                  | Array (String (URI) or Object(Set)) | The sets that are part of this search results page.                                                                                                          |
| `prev`                   | String (URL)                        | A reference to the next page in the sequence of pages that make up the search results.                                                                       |
| `next`                   | String (URL)                        | A reference to the previous page in the sequence of pages that make up the search results.                                                                   |
| **(Search) Result List** |                                     |                                                                                                                                                              |
| `id`                     | String (URI)                        | The identifier of the search results.                                                                                                                        |
| `type`                   | String                              | The type of the resource. Always set to "ResultList".                                                                                                        |
| `total`                  | Integer                             | The total number of user sets matching the search query.                                                                                                     |
| `first`                  | String (URL)                        | Indicates the first preceding page of user sets in the result list.                                                                                          |
| `last`                   | String (URL)                        | Indicates the furthest proceeding page of user sets in the result list.                                                                                      |

</details>

# Provision
