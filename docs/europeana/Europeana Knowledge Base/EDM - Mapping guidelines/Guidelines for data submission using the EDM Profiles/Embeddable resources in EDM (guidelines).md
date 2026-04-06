
# Embeddable resources in EDM (guidelines)

Data partners are encouraged to provide direct links to media files. However, content from platforms such as Flickr, YouTube, Vimeo or others, which can be embedded in Europeana, is also accepted. This exception applies to organisations that are hosting media on external platforms due to hosting limitations, when Europeana does not support the display of specific file formats (e.g. 3D models), or when copyright restrictions prevent direct online access to media.

To streamline the provision of embeddable resources, we have implemented EDM profile that utilises [oEmbed](https://oembed.com/), the de facto recognised standard for facilitating the embedding of content from one website on platforms like Europeana. The profile requires data providers to supply more than just a link to an oEmbed-compatible media page. This guide outlines the necessary information about embeddable web resources that must be included in EDM metadata to ensure seamless integration and proper display on Europeana.

> [!TIP]
> The full definition of the EDM profile for embeddable resources (potentially including elements not to be contributed by data providers) is available [here](https://europeana.atlassian.net/wiki/x/BgAoq).

> [!IMPORTANT]
> [About oEmbed](https://oembed.com/)
>
> When you want to embed a particular piece of content from a platform that supports oEmbed, you send a request to the oEmbed endpoint with the URL of the resource you wish to embed. An oEmbed endpoint is a URL that enables other websites to retrieve information about a specific content item using the oEmbed format.
>
> For example, if you wish to embed a Flickr image, Flickr’s oEmbed endpoint takes the image’s URL and returns the appropriate embed code that you can use on your website. The response usually also includes additional details, such as the image’s title, author, technical metadata, and thumbnail, as shown in the example below.

<details>
<summary>Example oEmbed Request and Response</summary>

**Request**

```java
GET https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json
```

**Response**

```java
{
type: "photo",
flickr_type: "photo",
title: "British Library digitised image from page 96 of "A Historical Geography of the British Colonies (of the British Empire)"",
author_name: "The British Library",
author_url: "https://www.flickr.com/photos/britishlibrary/",
width: 1024,
height: 671,
url: "https://live.staticflickr.com/3689/11197949844_a597c92047_b.jpg",
web_page: "https://www.flickr.com/photos/britishlibrary/11197949844/",
thumbnail_url: "https://live.staticflickr.com/3689/11197949844_a597c92047_q.jpg",
thumbnail_width: 150,
thumbnail_height: 150,
web_page_short_url: "https://flic.kr/p/i4wqmL",
license: "No known copyright restrictions",
license_url: "https://www.flickr.com/commons/usage/",
license_id: "7",
html: "<a data-flickr-embed="true" href="https://www.flickr.com/photos/britishlibrary/11197949844/" title="British Library digitised image from page 96 of &quot;A Historical Geography of the British Colonies (of the British Empire)&quot; by The British Library, on Flickr"><img src="https://live.staticflickr.com/3689/11197949844_a597c92047_b.jpg" width="1024" height="671" alt="British Library digitised image from page 96 of &quot;A Historical Geography of the British Colonies (of the British Empire)&quot;"></a><script async src="https://embedr.flickr.com/assets/client-code.js" charset="utf-8"></script>",
version: "1.0",
cache_age: 3600,
provider_name: "Flickr",
provider_url: "https://www.flickr.com/"
}
```

</details>

# Steps for providing oEmbed-compliant content as a web resource

- [Step 1: Provide the embeddable resource as an edm:WebResource](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2820177937#Step-1%3A-Provide-the-embeddable-content-as-an-edm%3AWebResource)
- [Step 2: Flag the WebResource as oEmbed compliant](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2820177937#Step-2%3A-Flag-the-WebResource-as-oEmbed-compliant)
- [Embeddable resources in EDM (guidelines)](Embeddable%20resources%20in%20EDM%20(guidelines).md)
- [Embeddable resources in EDM (guidelines)](Embeddable%20resources%20in%20EDM%20(guidelines).md)

Each step includes a mapping example, showing how the provision evolves and builds on the previous step towards the final mapping. The same image hosted on Flickr is used throughout to illustrate the provision of embeddable media.

> [!IMPORTANT]
> The definitions of the terms **MUST**, **MUST NOT**, **SHOULD**, etc. used in this document can be found at <https://tools.ietf.org/html/rfc2119>.

## **Step 1: Provide the embeddable resource as an edm:WebResource**

Embeddable media can be either used as the main or secondary digital representation of the cultural object. In line with EDM Definitions and[EDM - Mapping guidelines](../../EDM%20-%20Mapping%20guidelines.md), this means embeddable resource SHOULD be supplied in:

- `edm:isShownBy`
- OR `edm:hasView` (if there is already an `edm:isShownBy` present)

The URI of the WebResource MUST be supplied as the **oEmbed URL** containing all required parameters to retrieve embeddable content and metadata about a specific resource.

> [!IMPORTANT]
> An **oEmbed URL** is composed of an oEmbed provider's endpoint combined with the URL of the resource you want to embed, for example: `https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json`
>
> You can append additional parameters, such as `maxwidth` and `maxheight`, as long as they are supported by the provider. You may also include the format parameter if you prefer the response in a specific format. Information about the required and optional parameters can be found in [section 2.2 of the oEmbed specification](https://oembed.com/#section2.2).
>
> If the oEmbed URL includes the format parameter (e.g. `format=json` or `format=xml`), the mime type assigned during ingestion (`ebucore:hasMimeType`) will reflect the specified format: `application/json+oembed` for JSON and `text/xml+oembed` for XML. It is recommended to use oEmbed URLs that return a JSON response, as these endpoints are primarily consumed by web-based agents and applications, where JSON is the preferred format.
>
> For more information on how to obtain oEmbed URLs, refer to the [oEmbed discovery](https://europeana.atlassian.net/wiki/x/FAAnq).

Example:

```java
<ore:Aggregation rdf:about="[ … ]">
[…]
    <edm:isShownBy rdf:resource="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json"/>
[…]
</ore:Aggregation>
[…]

<edm:WebResource rdf:about="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json">
[…]
</edm:WebResource>
```

## **Step 2: Flag the WebResource as oEmbed compliant**

Connect the web resource containing an oEmbed URL to a resource of type `svcs:Service` using `svcs:has_service` property. The identifier of the Service MUST be the oEmbed endpoint.

> [!IMPORTANT]
> An **oEmbed endpoint** is a URL that serves as an interface between the content provider and the website embedding the content. Provided by an oEmbed-compliant service, it processes requests for embedding content.

Additionally:

- Indicate the `edm:WebResource` conforms to the oEmbed standard by using the `dcterms:conformsTo` property. The value of `dcterms:conformsTo` MUST be the URI with value `https://oembed.com/`
- The `svcs:Service` class SHOULD also have an `rdfs:label` property with the name of the service (e.g. “Flickr”, “Vimeo”, “YouTube”, “SoundCloud”, “Sketchfab” etc.)

Example:

```java
<ore:Aggregation rdf:about="[ … ]">
[…]
    <edm:isShownBy rdf:resource="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json"/>
[…]
</ore:Aggregation>
[…]

<edm:WebResource rdf:about="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json">
    <svcs:has_service rdf:resource="http://www.flickr.com/services/oembed/"/>
[…]
</edm:WebResource>

<svcs:Service rdf:about="http://www.flickr.com/services/oembed/">
    <dcterms:conformsTo rdf:resource="https://oembed.com/"/>
    <rdfs:label>Flickr</rdfs:label>
</svcs:Service>
```

## Step 3: Provide a thumbnail for the embeddable resource

For embeddable content, Europeana cannot generate a thumbnail directly from the embedded resource. Therefore, it is strongly recommended that you either:

- Supply **an image** in `edm:object` (*currently the only reliable option*)
- OR include the **thumbnail\_url** parameter in the oEmbed service response (*at the moment, Europeana cannot automatically extract the thumbnail\_url from the oEmbed response and map it to* `edm:object`*, so providing* `edm:object` *is recommended*)

> [!IMPORTANT]
> Information about **thumbnail\_url** parameter is available in [section 2.3 of the oEmbed specification](https://oembed.com/#section2.3).

> [!WARNING]
> Note that an embeddable `edm:WebResource` MUST NOT be used as the value of an `edm:object` property, since it may not be possible to generate a small image from an embeddable resource for use in the portal.

Example:

```java
<ore:Aggregation rdf:about="[ … ]">
[…]
    <edm:isShownBy rdf:resource="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json"/>
    <edm:object rdf:resource="https://farm4.staticflickr.com/3689/11197949844_4bdfcaa7d6_o.jpg"/>
[…]
</ore:Aggregation>
[…]

<edm:WebResource rdf:about="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json">
    <svcs:has_service rdf:resource="http://www.flickr.com/services/oembed/"/>
[…]
</edm:WebResource>

<svcs:Service rdf:about="http://www.flickr.com/services/oembed/">
    <dcterms:conformsTo rdf:resource="https://oembed.com/"/>
    <rdfs:label>Flickr</rdfs:label>
</svcs:Service>
```

## Step 4 (optional): Include a direct media representation of the same content

In some cases, providers may wish to supply a “simple” media representation alongside the embeddable version of the same content. In such cases, the relationship between the “simple” and embeddable `edm:WebResource` SHOULD be established using the `dcterms:isFormatOf` property.

> [!IMPORTANT]
> Providers should note:
>
> - The URL in the `dcterms:isFormatOf` MUST exactly match the URL of the corresponding `edm:WebResource` (e.g. if the URL in `dcterms:isFormatOf` points to the embeddable `edm:WebResource`, it must match the base URL and all the oEmbed parameters used in the URL of the `edm:WebResource`)
> - Provision of the `edm:WebResource` representing the embeddable content MUST follow the [Embeddable resources in EDM (guidelines)](Embeddable%20resources%20in%20EDM%20(guidelines).md) for providing embeddable resources

Example (we use the same image hosted on Flickr as in the previous steps. In this case, a traditional JPEG image is supplied as the primary representation and mapped to `edm:isShownBy`, while the embeddable Flickr image is provided as an additional, higher-resolution view in `edm:hasView`):

```java
<ore:Aggregation rdf:resource="[ … ]">
[…]
  <edm:isShownAt rdf:resource="https://flickr.com/photos/britishlibrary/11197949844/"/>
  <edm:isShownBy rdf:resource="https://farm4.staticflickr.com/3689/11197949844_4bdfcaa7d6_o.jpg"/>
  <edm:hasView rdf:resource="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json"/>
  <edm:object rdf:resource="https://farm4.staticflickr.com/3689/11197949844_4bdfcaa7d6_o.jpg"/>
</ore:Aggregation>

<edm:WebResource rdf:about="https://farm4.staticflickr.com/3689/11197949844_4bdfcaa7d6_o.jpg">   
[…]  
</edm:WebResource>

<edm:WebResource rdf:about="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json">
  <dcterms:isFormatOf rdf:resource="https://farm4.staticflickr.com/3689/11197949844_4bdfcaa7d6_o.jpg"/>
  <svcs:has_service rdf:resource="http://www.flickr.com/services/oembed/"/>
[…]
</edm:WebResource>

<svcs:Service rdf:about="http://www.flickr.com/services/oembed/">
    <dcterms:conformsTo rdf:resource="https://oembed.com/"/>
    <rdfs:label>Flickr</rdfs:label>
</svcs:Service>
```

# What happens during ingestion?

When providers supply embeddable media content following the steps described above, Europeana will also generate extra technical metadata (`edm:type` and `ebucore:hasMimeType`) from the provided oEmbed URL and add it to the provided webResource.

> [!IMPORTANT]
> To support features on embeddable resources, such as generating IIIF resources and improving tier calculations in the Europeana Publishing Framework, Europeana will classify content into the main media categories: text, image, sound, video, or 3D. This classification is indicated using the `edm:type` property on each `edm:WebResource`.
>
> More details on the technical metadata extracted by Europeana from webResources are available in the [EDM profile for technical metadata](https://europeana.atlassian.net/wiki/x/A4DJr).

<details>
<summary>Example of technical metadata added during ingestion by Europeana</summary>

```java
<edm:WebResource rdf:about="https://www.flickr.com/services/oembed/?url=http%3A%2F%2Fwww.flickr.com%2Fphotos%2Fbritishlibrary%2F11197949844%2F&format=json">
   <svcs:has_service rdf:resource="http://www.flickr.com/services/oembed/"/>
   <ebucore:hasMimeType>application/json+oembed</ebucore:hasMimeType>
   <ebucore:width rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">1024</ebucore:width>
   <ebucore:height rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">671</ebucore:height>
   <edm:type>IMAGE</edm:type> 
</edm:WebResource>
```

</details>
