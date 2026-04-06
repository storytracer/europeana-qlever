
# oEmbed discovery

The oEmbed specification includes the [concept of discovery](https://oembed.com/#section4), which allows oEmbed providers (e.g. YouTube, Vimeo, Flickr, among others) to make their oEmbed endpoints discoverable through link elements in the HTML of their web pages and link headers in HTTP responses. As a Europeana data provider contributing embeddable media in EDM, you can inspect link elements and headers to find the correct oEmbed URL for a specific WebResource.

> [!TIP]
> If you are, or plan to become, an oEmbed service provider, we encourage you to make your oEmbed support discoverable and to register your service in the [oEmbed registry](https://oembed.com/providers.json), as described here <https://oembed.com/#section7>.

# oEmbed URL retrieval

For data partners looking to find oEmbed URLs, we suggest using simple tools (for example, [Postman](https://www.postman.com/)):

- [Step 1: Input resource URL](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2821128212?draftShareId=5b79ac42-d9da-4bfa-966b-b99a3f3b6c4b#Step-1%3A-Input-resource-URL)
- [Step 2: Discovery process](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2821128212?draftShareId=5b79ac42-d9da-4bfa-966b-b99a3f3b6c4b#Step-2%3A-Discovery-process)

  - [Using link elements](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2821128212?draftShareId=5b79ac42-d9da-4bfa-966b-b99a3f3b6c4b#1.-Using-link-elements)
  - [Using link header](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2821128212?draftShareId=5b79ac42-d9da-4bfa-966b-b99a3f3b6c4b#2.-Using-link-header)

## **Step 1: Input resource URL**

Enter the URL of the resource you want to request (e.g. `https://www.youtube.com/watch?v=mQ-bOapw9XA&ab_channel=CINEMATEK`) in the address bar.

Then use the "Send" button to submit the request.

## **Step 2: Discovery process**

### 1. Using link elements

Scroll down to the Response Body and inspect HTML link elements:

look for link elements with `rel="alternate"` attribute and type attributes specifying the oEmbed format (`type="application/json+oembed"` or `type="text/xml+oembed"`).

The URLs contained within the `href` attributes point to the oEmbed URL that consists of the full oEmbed endpoint plus URL of the embeddable resource.

Link element example:

```java
<link rel="alternate" type="application/json+oembed" href="https://www.youtube.com/oembed?format=json&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DmQ-bOapw9XA"title="La fée aux fleurs (Gaston Velle - 1905)">
<link rel="alternate" type="text/xml+oembed" href="https://www.youtube.com/oembed?format=xml&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DmQ-bOapw9XA"title="La fée aux fleurs (Gaston Velle - 1905)">
```

### 2. Using link header

Alternatively, scroll to the Headers section in the response panel and look for the Link header in the list of headers. If it exists, expand it to view its contents. Similar to the HTML link elements, the Link headers might contain URLs to the oEmbed endpoints.

Header example:

```java
Link:<https://www.youtube.com/oembed?format=json&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DmQ-bOapw9XA>; rel="alternate"; type="application/json+oembed"; title="La fée aux fleurs (Gaston Velle - 1905)"
Link:<https://www.youtube.com/oembed?format=xml&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DmQ-bOapw9XA>; rel="alternate"; type="text/xml+oembed"; title="La fée aux fleurs (Gaston Velle - 1905)"
```

> [!NOTE]
> For developers working on an oEmbed-compliant platform, integrating the discovery feature is strongly recommended, though not mandatory. Consequently, data partners may need to use alternative methods to locate oEmbed endpoints and construct oEmbed URLs. Here are some approaches to consider in these cases:
>
> - The oEmbed registry lists (some) providers and their endpoints in a [JSON file](https://oembed.com/providers.json).
> - Consult documentation from oEmbed providers, which should list supported endpoints and parameters.
> - We have compiled a list of the most frequently used oEmbed endpoints among Europeana partners. It can be used to construct oEmbed URLs by combining the oEmbed endpoint with the media URL (e.g., a YouTube video page).

<details>
<summary>List of popular oEmbed providers and their endpoints</summary>

|  **Provider**    |  **oEmbed endpoint**                            |
|:-----------------|:------------------------------------------------|
| YouTube          | <https://www.youtube.com/oembed>                |
| Vimeo            | <https://vimeo.com/api/oembed>                  |
| SoundCloud       | <https://soundcloud.com/oembed>                 |
| EUscreen         | <https://oembed.euscreen.eu/services/oembed>    |
| Sketchfab        | <https://sketchfab.com/oembed>                  |
| Eureka3D         | <https://eureka3d.vm.fedcloud.eu/oembed>        |
| WEAVE            | <https://weave-3dviewer.com/api/core/v1/oembed> |

</details>
