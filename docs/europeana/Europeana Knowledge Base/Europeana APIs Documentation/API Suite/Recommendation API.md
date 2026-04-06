
# Recommendation API

The Recommendation API offers users recommendations for items available in Europeana based on other items, entities or galleries (ie. user sets). It uses a technology from machine learning (a subfield in artificial inteligence), more specifically vector embeddings, to compute similarity between information resources based on a selective number of parameters/dimensions.

This API supports the recommendation functionality on the Europeana website and can be found next to the pages where these resources are available such as the Item Page, Entity Page and Gallery Page. It is only available for logged-in users on the Europeana Website but is available for all users at the API unless the resource has restricted access such as private user sets (galleries).

|                                                                 |                                            |
|:----------------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] [Get your API Key here](#get-your-api-key-here) <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                                      |                                                                                              |
|:-------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/recommendation) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

- [Recommendations](#recommendations)
  - [Retrieving recommendations for an item](#retrieving-recommendations-for-an-item)
  - [Retrieving recommendations for an entity](#retrieving-recommendations-for-an-entity)
  - [Retrieving recommendations for an user set](#retrieving-recommendations-for-an-user-set)

# Recommendations

Methods for obtaining item recommendations for another item, entity or user set (ie. gallery). Given that the response is always a list of items, for reasons of interoperabiltity, the same response as the Search API was adopted for these methods. See the documentation for reference.

## Retrieving recommendations for an item

Retrieves a list of recommended items for a specific item in Europeana.

### Request

```java
https://api.europeana.eu/recommend/record/[RECORD_ID]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                               |
|:------------------|:-----------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| RECORD\_ID        | path             | The identifier of the record which is composed of the dataset identifier plus a local identifier within the dataset in the form of "/DATASET\_ID/LOCAL\_ID", for more detail see Europeana ID. |
| page              | query            | The page number of the list of recommendations to allow for scrolling along the results (default is 1).                                                                                        |
| pageSize          | query            | The number of suggested items being returned. The default is 10 and limited to 50.                                                                                                             |
| seed              | query            | An integer number used as seed to randomise the top recommendations.                                                                                                                           |
| ACCEPT            | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported.                                                |

### Response

On success, the method returns a HTTP 200 with the metadata for a list of (recommended) items similarly to the Search API, see Search API documentation for reference.

## Retrieving recommendations for an entity

Retrieves a list of recommended items for a specific entity in Europeana.

### Request

```java
https://api.europeana.eu/recommend/entity/[ENTITY_TYPE]/[ENTITY_ID]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                |
|:------------------|:-----------------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| ENTITY\_TYPE      | path             | The type of the entity. One of: “agent“, “place“, “concept“, “timespan“, “organization“                                                         |
| ENTITY\_ID        | path             | The local identifier of the entity.                                                                                                             |
| page              | query            | The page number of the list of recommendations to allow for scrolling along the results (default is 1).                                         |
| pageSize          | query            | The number of suggested items being returned. The default is 10 and limited to 50.                                                              |
| seed              | query            | An integer number used as seed to randomise the top recommendations.                                                                            |
| ACCEPT            | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported. |

### Response

On success, the method returns a HTTP 200 with the metadata for a list of (recommended) items similarly to the Search API, see Search API documentation for reference.

## Retrieving recommendations for an user set

Retrieves a list of recommended items for a specific user set in Europeana.

### Request

```java
https://api.europeana.eu/recommend/set/[SET_ID]
Accept: [ACCEPT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                |
|:------------------|:-----------------|:------------------------------------------------------------------------------------------------------------------------------------------------|
| SET\_ID           | path             | The local identifier of the user set.                                                                                                           |
| page              | query            | The page number of the list of recommendations to allow for scrolling along the results (default is 1).                                         |
| pageSize          | query            | The number of suggested items being returned. The default is 10 and limited to 50.                                                              |
| seed              | query            | An integer number used as seed to randomise the top recommendations.                                                                            |
| ACCEPT            | header           | Indicates the preferred format via which the user set is to be represented if the format is accepted by the service. Only JSON-LD is supported. |

### Response

On success, the method returns a HTTP 200 with the metadata for a list of (recommended) items similarly to the Search API, see Search API documentation for reference.
