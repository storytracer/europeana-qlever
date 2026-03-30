


# Media policy

The Europeana Media Policy outlines the requirements for the links to the media resources that are part of the provided metadata. It complements the information provided with the [Publishing guide](Publishing%20guide.md) and the [EDM - Mapping guidelines](EDM%20-%20Mapping%20guidelines.md). By following these requirements, we can give audiences a better experience and a greater connection with your collections. Following these requirements we will:

- Extract technical metadata from media resources (e.g. mime-type, image size, duration, colour) to allow for a richer search and browse experience and to power functionalities such as enlarging and downloading images and other media.  An overview of all the technical metadata facets in Europeana website can be found on the[Europeana APIs Documentation](Europeana%20APIs%20Documentation.md)
- Generate thumbnail (preview) images based on media resources, and show these images as part of the search results to help users find what they are looking for.
- Display media resources on the item pages on the Europeana website for a user to get the best possible experience and be able to interact with the content.

> [!NOTE]
> Note that the content tiers, i.e. the quality of a media resource as specified in the Europeana Publishing Framework,[Publishing guide](Publishing%20guide.md).

- [Metadata and Media Links](#metadata-and-media-links)
- [Retrieving Media](#retrieving-media)
- [Supported Media Formats/Mime Types](#supported-media-formats-mime-types)
- [Generation of Thumbnail (Preview) Images](#generation-of-thumbnail-preview-images)
- [Display of Media Resources](#display-of-media-resources)
  - [CORS](#cors)
  - [HTTPS](#https)
  - [Embedding of media resources](#embedding-of-media-resources)
- [Extraction of Technical Metadata](#extraction-of-technical-metadata)

## Metadata and Media Links

We will process (links to) media resources in the following three EDM metadata fields:

- `edm:object`
- `edm:isShownBy`
- `edm:hasView` (for each - More than one instance of edm:hasView is possible when more than one media resource is provided.)

We will also process links provided with edm:isShownAt, but we will not generate any thumbnails. Processing the edm:isShownAt involves checking that the link is resolvable and storing the mime-type of the working link. For more details about these metadata fields and their definition, please consult the [EDM - Mapping guidelines](EDM%20-%20Mapping%20guidelines.md)

## **Retrieving Media**

Retrieving the links to media resources in the above mentioned metadata fields is required in order to access and download those media resources which is necessary in order to generate the technical metadata (and thumbnails, see below). Europeana will only temporarily download the media resource, which will be discarded after processing.

In order to successfully access and download a media resource, the following requirements must be met:

- The link to the media resource must be a valid URL (Complies with either [IETF RFC 3986: Uniform Resource Identifier (URI): Generic Syntax](https://tools.ietf.org/rfc/rfc3986.txt) or [IETF RFC 3987 Internationalized Resource Identifiers](https://www.ietf.org/rfc/rfc3987.txt) (IRIs)) and we recommend such URL to use the HTTPS protocol.
- The link must resolve to a media resource directly, not to a webpage (i.e. where the mime-type of the resource would be "text/html").
- The link must not return more than three redirects before ending up on the media resource.
- The media resource must be able to be downloaded within a time span of 20 minutes.
- The media resource must have a valid mime-type. We have established a list of valid mime-types that we support from ingestion to display in Europeana website based on the mime-types maintained by the [Internet Assigned Numbers Authority](http://www.iana.org/assignments/media-types/media-types.xhtml).
- Large PDF files should be [optimised for Fast Web View](https://helpx.adobe.com/acrobat/using/optimizing-pdfs-acrobat-pro.html#EnableFastWebViewinaPDF) so they take less time to download. An exception from these requirements are media resources that are embedded in the Europeana website (see the section below).

## Supported Media Formats/Mime Types

A MIME type (also known as a Multipurpose Internet Mail Extension) is a standard that indicates the format of a file. It is a fundamental characteristic of a digital resource that influences its ability to be accessed and used over time. The purpose of this section is to provide a list of MIME types corresponding to different types of content/media that are supported or not by Europeana.

Europeana includes the media resources and metadata provided via EDM into [IIIF Manifests at Europeana](Europeana%20and%20IIIF/IIIF%20Manifests%20at%20Europeana.md) that power the display of media resources. The mime type associated with the web resources specified in edm:isShownBy and edm:hasView determines if and how these resources are included in the manifest. Here you can find the[Media Formats/Mime Types](Europeana%20and%20IIIF/Media%20Formats_Mime%20Types.md).

## Generation of Thumbnail (Preview) Images

Thumbnails are a small image of the digital object. They directly on the [europeana.eu](http://europeana.eu) webiste directly affects the user click-through rate. Requirements and recommendations about the quality of thumbnails are provided in the [Publishing guide](Publishing%20guide.md).

We will generate thumbnails from the media resources provided via the above metadata fields, if the MIME type of the media resources is valid (see also above). Note that for media resources with the MIME type “application/pdf” we only generate a thumbnail when we find an image in the pdf.

We will generate the following thumbnails:

- An image with a width of at maximum 200 pixels.
- An image with a width of at maximum 400 pixels.

The following must be noted:

- The height of the thumbnail will be proportional in accordance with the aspect ratio.
- If an image is smaller than 200 or 400 pixels, the original width of the image will be used as the size of the thumbnail (Europeana does not recommend to use images which are smaller than 400 pixels in width).

All thumbnails that we generate can be retrieved via [Thumbnail API Documentation](Europeana%20APIs%20Documentation/API%20Suite/Thumbnail%20API%20Documentation.md). Note that for the thumbnail used for display in the search results of the Europeana website, we have a specific metadata field: edm:preview. The value for edm:preview will be the thumbnail corresponding to either the media resource obtained from edm:object if available, otherwise the image with the highest resolution of either edm:isShownBy or the first edm:hasView.

## Display of Media Resources

### CORS

In order for the Europeana website portal to access and display media resources coming from providers’ servers, the latter must support [Cross-Origin Resource Sharing](https://www.w3.org/TR/cors/) (CORS). This is because web browsers restrict resources on a web page to be requested from another domain outside the domain it was served (Europeana website in this case). The CORS standard is needed because it allows servers to specify not only who can access its resources but also how these resources can be accessed.

> [!WARNING]
> This is especially important for providers who share resources via IIIF as CORS is essential for our IIIF viewer to perform the image information requests and to obtain the presentation manifests. Without CORS, although the IIIF resources will be displayed in the provider’s website, it won’t be possible to be viewed in the Europeana Collections portal. For more information about [CORS](https://enable-cors.org/).

### HTTPS

Providers of IIIF resources are encouraged to deliver their resources over HTTPS so that they can be included in our web page without issue.

### Embedding of media resources

In order for an item to be embedded on the Europeana website, there must be a valid [oEmbed](https://oembed.com/) endpoint (see example from [SketchFab](https://sketchfab.com/oembed?url=https%3A%2F%2Fsketchfab.com%2F3d-models%2Fsaint-laurentius-church-of-ename-around-1500-9e5f19f6416942e49f1a7360d3043503)) available where the media referred to in the item is displayed using a third party viewer or player. An exception is made for some data partners that do not support oEmbed.

On the metadata side, a link to a webpage where the item can be displayed and which can be mappable to an oEmbed URL is provided within edm:isShownBy. In order to do this and because there is no information in the metadata that relates the webpage link to the oEmbed endpoint, the Europeana website has to apply additional logic to convert the URL provided in edm:isShownBy into an oEmbed URL that can be used for embedding. For this, it uses an [internal registry of oEmbed endpoints](https://github.com/europeana/europeana-portal-collections/blob/develop/config/initializers/oembed.rb) which consists of both a public list and manual additions made by the Service Experience development team (which also includes the Europeana oEmbed implementations to cover the exceptions). This means that whenever a new dataset is added that uses a different oEmbed endpoint it will need to be added to this registry.

## Extraction of Technical Metadata

Europeana will extract metadata from the media resources provided via the above metadata fields. This is what we refer to as technical metadata (e.g. the image size, image colours, duration of audio clips). EDM was extended with a [Technical metadata in EDM (definitions)](Europeana%20Data%20Model/EDM%20profiles/Technical%20metadata%20in%20EDM%20(definitions).md) was developed. It specifies what applies to the five media types which Europeana currently supports, namely: Sound, Video, Text, Image and 3D objects. This profile lists the properties that will apply to the WebResource class (and an additional class) which were defined to support the functionality presented in the introduction.
