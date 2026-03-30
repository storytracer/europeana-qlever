
[Europeana and IIIF](../Europeana%20and%20IIIF.md)

# IIIF Manifests at Europeana

Harnessing the capabilities of the [IIIF Presentation API](https://training.iiif.io/europeana/prezi-intro.html), we are making sharing and reusing digital objects published in Europeana even easier. Now, the great majority of records in Europeana contain a link to a IIIF manifest, powering the display of digital objects in the portal and unlocking new reuse possibilities.

Europeana is combining media resources and metadata from provided EDM into IIIF manifests. Each manifest is linked from edm:isShownBy and edm:hasView web resource(s) through the dcterms:isReferencedBy property and powers the display of media in the Europeana website. For providers who prefer to retain control over the display of their media resources, we continue to accept manifests created by them. In such cases, the provided manifest is preserved in the dcterms:isReferencedBy property and powers the display, taking precedence over the Europeana-created manifest.

- [Structure of the Europeana Manifest](#structure-of-the-europeana-manifest)
  - [1 Mime type is available](#key-1-mime-type-is-available)
  - [2 Mime type is not available](#key-2-mime-type-is-not-available)
- [Benefits for Europeana Providers and Users](#benefits-for-europeana-providers-and-users)

> [!IMPORTANT]
> Manifest is a central organising unit in IIIF and is accessible via URL that points to a document online (in JSON-LD format). We provide our manifests in [Presentation API 2.1](https://iiif.io/api/presentation/2.1/) (v2.1) by default. [Version 3.0](https://iiif.io/api/presentation/3.0/) (v3) manifests can be returned via content negotiation by sending an `Accept` header with the value: `application/ld+json;profile="http://iiif.io/api/presentation/3/context.json"`
>
> Each manifest contains information needed for IIIF-compatible viewers to display digital objects, such as the structure, grouping, and layout of media resources, as well as descriptive metadata and rights information. For the complete list of EDM properties included in Europeana manifests and how they are mapped to IIIF, please refer to the companion page [“EDM to IIIF Mapping”.](https://europeana.atlassian.net/wiki/x/IwABjw)

# Structure of the Europeana Manifest

Europeana manifests strongly depend on the technical metadata assigned to the provided web resources during the ingestion process, where Metis media service inspects media file(s) supplied in the EDM for technical metadata. If edm:WebResource class related to the processed media file is absent from the provided data, the media service creates it and then adds the technical metadata to it, as in the example below.

<details>
<summary>WebResource class excerpt from the record with video file mapped to edm:isShownBy</summary>

```java
<edm:WebResource rdf:about="https://zenodo.org/api/files/24ba47a0-41cb-46ad-b39e-8b63ded1a7a8/GR_PIOP_1219EMX034_ELMA_TV_ad_ARB.mp4">
   <edm:rights rdf:resource="http://creativecommons.org/licenses/by-sa/4.0/"/>
   <ebucore:hasMimeType>video/mp4</ebucore:hasMimeType>
   <ebucore:duration>39800</ebucore:duration>
   <ebucore:width rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">1920</ebucore:width>
   <ebucore:height rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">1080</ebucore:height>
   [...]
</edm:WebResource>
```

</details>

> [!IMPORTANT]
> Technical metadata is information about the technical qualities of the provided media resource, for example:
>
> - height of a video frame expressed as a number of pixels (ebucore:height)
> - width of a video frame expressed as a number of pixels (ebucore:width)
> - duration of a track or a signal expressed in ms (ebucore:duration)
> - the main mime type (ebucore:hasMimeType). Mime type is a standard that indicates the format of a file. It is a fundamental characteristic of a digital resource that influences its ability to be accessed and used over time.

The mime type associated with the edm:isShownBy and edm:hasView web resources determines if and how these resources are included in the Europeana manifest. This, in turn, affects how media resources associated with the provided object are displayed:

## 1 Mime type is available

When the edm:WebResource class contains a mime type, there are three possible scenarios for displaying media resources, depending on the mime type group.

We have categorised mime types present in Europeana into three distinct groups. For an overview of mime types associated with (browser) supported and specialised formats, please refer to this [companion page](https://europeana.atlassian.net/wiki/x/OID_jg). All other, non-listed mime types are not supported by Europeana.

The main difference between the groups is how they are presented in the canvas:

> [!IMPORTANT]
> Canvas is a virtual container for media resources (e.g. images, videos) and other presentation content (e.g. transcription, subtitles) that are “painted” onto it. It provides a frame of reference for the layout of the content.

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|:----------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ***Mime type group***       | ***v2***                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ***v3***                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| <br/> *(Browser) Supported* | Web resource(s) related to edm:isShownBy and edm:hasView(s) is included in the manifest as painting-type annotation(s) on canvas(es), except for Video and Sound types. <br/> [Example manifest for type image (v2)](https://iiif.europeana.eu/presentation/990/item_2456D7B6OEVQAB4ANOYHBG3WU5SZFENK/manifest) <br/> [Example manifest for type video (v2)](https://iiif.europeana.eu/presentation/08626/1037479000000331030/manifest)                                                                                                                                                                             | Web resource(s) related to edm:isShownBy and edm:hasView is included in the manifest as painting-type annotation(s) on canvas(es). <br/> [Example manifest for type image (v3)](https://iiif.europeana.eu/presentation/990/item_2456D7B6OEVQAB4ANOYHBG3WU5SZFENK/manifest?format=3) <br/> [Example manifest for type video (v3)](https://iiif.europeana.eu/presentation/08626/1037479000000331030/manifest?format=3)                                                                                                                                  |
| <br/> *Specialised*         | Thumbnail(s) (extracted during media processing and made available via the [Thumbnail API](https://pro.europeana.eu/page/record#thumbnails)) for the respective web resource(s) is included in the manifest as painting-type annotation(s) on canvas(es) & the actual (non-viewable) web resource(s) is added to the canvas as a rendering component, except for Video and Sound types. <br/> [Example manifest for type image (v2)](https://iiif.europeana.eu/presentation/262/C_DL_201000511/manifest) <br/> [Example manifest for type video (v2)](https://iiif.europeana.eu/presentation/08608/165284/manifest) | Thumbnail(s) (from the [Thumbnail API](https://pro.europeana.eu/page/record#thumbnails)) for the respective web resource(s) is included in the manifest as painting-type annotation(s) on canvas(es) & the actual (non-viewable) web resource(s) is added to canvas(es) as a rendering component. <br/> [Example manifest for type image (v3)](https://iiif.europeana.eu/presentation/262/C_DL_201000511/manifest?format=3) <br/> [Example manifest for type video (v3)](https://iiif.europeana.eu/presentation/08608/165284/manifest?format=3) <br/> |
| <br/> *Non-supported*       | No canvas is generated & manifest is not linked from the edm:WebResource class. <br/> [Example manifest for type text (v2)](https://iiif.europeana.eu/presentation/26/providedCHO_BBAW_18201/manifest)                                                                                                                                                                                                                                                                                                                                                                                                              | No canvas is generated & manifest is not linked from the edm:WebResource class. <br/> [Example manifest for type text (v3)](https://iiif.europeana.eu/presentation/26/providedCHO_BBAW_18201/manifest?format=3)                                                                                                                                                                                                                                                                                                                                       |

> [!NOTE]
> Note scenarios are applied per web resource, not per record. If a record has multiple web resource classes, all three scenarios may be applied during the manifest creation. For instance, this could mean some web resources are included in the manifest, while no canvas is created for the others.

## 2 Mime type is not available

When the edm:WebResource class does not contain a mime type, no canvas is created for this web resource. In the example below, the mime type of media resource provided in edm:isShownBy was not extracted during ingestion.

<details>
<summary>WebResource class excerpt from the record with image file mapped to edm:isShownBy. Notice the absence of technical metadata</summary>

```java
<edm:ProvidedCHO rdf:about="/632/_nnkqnsb"/>
  <edm:WebResource rdf:about="http://bc.wbp.lublin.pl/Content/23555/POCZ_U_247.jpg">
  <edm:rights rdf:resource="http://creativecommons.org/publicdomain/mark/1.0/"/>
</edm:WebResource>
```

</details>

There are several consequences of the missing mime type:

- Canvas is not added to [the manifest](https://iiif.europeana.eu/presentation/632/_nnkqnsb/manifest),
- The manifest is [not linked from the edm:WebResource class](https://api.europeana.eu/record/632/_nnkqnsb.json?wskey=) because the web resource (image in the example above) is not included in the manifest,
- Manifest dictates the display of media on the Europeana website: the web resources that are not linked to a manifest are also absent from the manifest. In our example, this results in the provided image [not being displayed](https://www.europeana.eu/en/item/632/_nnkqnsb) on the website,
- Ultimately, if no web resource is linked to a manifest, no manifest is available and no media is displayed in the portal.

# Benefits for Europeana Providers and Users

IIIF technologies provide numerous advantages for users and institutions working with digital resources. To enable our providers to benefit from them without needing to invest in developing their own solutions, we have made our manifests publicly available in the most up-to-date version of the IIIF Presentation API (v3). This eliminates the need for providers to create their own manifests to leverage IIIF technologies.

Our manifests enable users to view, manipulate, compare, and share digital objects that are published in Europeana. They can add annotations to media resources, mix up content from different providers, or even build new collections by organising manifests into groups. For instance, if a user wants to use an image from Europeana, they no longer need to search for the image URL in the data or download the image. Instead, they can simply use the manifest and load it into any IIIF-compliant viewer. Currently, all a user needs to retrieve the manifest is the Record ID, which is composed of the dataset and local identifier of the object: `https://iiif.europeana.eu/presentation/{DATATSET_ID}/{LOCAL_ID}/manifest` (you can test our IIIF API using [API Console](https://api.europeana.eu/console/index.html?url=docs/v3/iiif.json) that supports API calls, including manifest retrieval).

By generating IIIF manifests we are also providing an improved user experience in Europeana. Users are encouraged to interact with digital objects in new ways. This includes features such as zooming in and out of digital content and gaining access to additional information like transcriptions and multilingual subtitles through annotations.

> [!NOTE]
> Providers interested in supplying content enrichments (e.g. subtitles, transcriptions, etc.) are invited to get in touch with us to discuss the details of the provision.
>
> At the moment, it is only possible to include full-text resources in Europeana-generated manifests, as this would otherwise require changing the manifest from the provider.
