
# Thumbnail API Documentation

The Thumbnail API was developed to give access to the cached thumbnails that are generated upon aggregation of the items in Europeana. Thumbnails are generated for all image resources that are referred through by [Page not accessible (ID: 2385313809)], edm:hasView or [Page not accessible (ID: 2385313809)] properties. Only one of these thumbnails is chosen for the [Page not accessible (ID: 2385313809)] property, however, all are accessible via the Thumbnail API using the URL of the media resources they were extracted from.

To know whether thumbnails have been generated for a record, you can use the [Search API Documentation](Search%20API%20Documentation.md) and add *has\_thumbnail=true* to your search criteria (preferrably in the qf parameter), or check if the *edmPreview* field in either Search or Record API responses have a value (which is the URL of the thumbnail).

|                                                         |                                            |
|:--------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] You don’t need an API key for this API! <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                                 |                                                                                              |
|:--------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/thumbnail) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

## Retrieving thumbnails from content resources

The Thumbnail API is able to retrieve a thumbnail for any content resource that has been processed by Europeana.

### Request v3

The Thumbnail API doesn't require any form of authentication, providing your [API key](https://pro.europeana.eu/page/get-api) is optional.

A call to v3 of the Thumbnail API is an HTTPS request following the structure:

```java
GET https://api.europeana.eu/thumbnail/v3/[SIZE]/[MEDIA].[FORMAT]
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                          |
|:------------------|:-----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| SIZE              | path             | The width size of the thumbnail. There are only two width sizes for thumbnails, namely: “200” and “400” px.                                                               |
| MEDIA             | path             | The identifier of the media resource from which the thumbnail was generated. It corresponds to the hash value of the URL where the original media resource is accessible. |
| FORMAT            | path             | The format of the image. Only “jpg“ is supported.                                                                                                                         |

### Response

A image resource, corresponding to the thumbnail, is returned in the requested size.

<details>
<summary>A v3 example for a 200px wide thumbnail of the image "http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg"</summary>

`https://api.europeana.eu/thumbnail/v3/200/820911931db3ccb20e1b7a022ee6dd33.jpg`

</details>

### Request v2

Similarly to v3, v2 doesn't require any form of authentication, providing your [API key](https://pro.europeana.eu/page/get-api) is optional. As opposed to v3, v2 always returns an image, whether the thumbnail exists or not.

A call to v3 of the Thumbnail API is an HTTPS request following the structure:

```java
GET https://api.europeana.eu/thumbnail/v2/url.json
```

|  **Parameter**    |  **Location**    |  **Description**                                                                                                                                                                        |
|:------------------|:-----------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| url               | query            | The URL of the content resource from which a thumbnail was generated. Note that the URL must be encoded.                                                                                |
| size              | query            | The width size of the thumbnail. There are only two width sizes for thumbnails, namely: “w200” or “w400”.                                                                               |
| type              | query            | Type of the record which informs, in case the thumbnail does not exists, which default thumbnail should be returned. Acceptable options are: “IMAGE”, “SOUND”, “VIDEO”, “TEXT” or “3D”. |

### Response

A image resource, corresponding to the thumbnail, is returned in the requested size or, if no thumbnail is found matching the URL, a default thumbnail corresponding to the requested type is returned.

<details>
<summary>A v2 example for a 400px wide thumbnail of the image "https://www.dropbox.com/s/8gpbipwr4ipwj37/Austria_Gerstl.jpg"</summary>

```java
https://api.europeana.eu/thumbnail/v2/url.json?uri=https%3A%2F%2Fwww.dropbox.com%2Fs%2F8gpbipwr4ipwj37%2FAustria_Gerstl.jpg%3Fraw%3D1&type=IMAGE&size=w400
```

</details>
