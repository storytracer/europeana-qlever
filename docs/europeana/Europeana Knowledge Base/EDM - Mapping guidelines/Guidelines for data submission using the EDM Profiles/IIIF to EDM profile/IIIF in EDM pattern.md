---
tags:
  - '#iiif'
  - '#edm'
  - '#kb-how-to-article'
  - '#iiif-pattern'
---

# IIIF in EDM pattern

- [Step 1: Providers MUST identify the type of link between the IIIF resource for the object and the object.](#step-1-providers-must-identify-the-type-of-link-between-the-iiif-resource-for-the-object-and-the-object)
- [Step 2: Providers SHOULD supply an identifier for the WebResource referenced as a 'view' of the object.](#step-2-providers-should-supply-an-identifier-for-the-webresource-referenced-as-a-view-of-the-object)
- [Step 3: Providers MUST flag the WebResource as a IIIF-compliant resource](#step-3-providers-must-flag-the-webresource-as-a-iiif-compliant-resource)
- [Step 4: The identifier of the Service MUST be the 'base URI' of the IIIF resource.](#step-4-the-identifier-of-the-service-must-be-the-base-uri-of-the-iiif-resource)
- [Step 5: The provider MAY provide access to a IIIF Manifest](#step-5-the-provider-may-provide-access-to-a-iiif-manifest)
- [Step 6: The provider MAY indicate a level of IIIF implementation.](#step-6-the-provider-may-indicate-a-level-of-iiif-implementation)

The International Image Interoperability Framework (IIIF) is a standard for serving and consuming high quality images online, with the ability to instruct a server about the desired resolution, or image manipulations such as rotation and zooming and it enables institutions in the cultural heritage sector to share better quality digital content.

[Discussions with partners in the IIIF community](https://github.com/IIIF/api/issues/558) have lead us to identify a pattern that Europeana providers can use to submit IIIF resources from their own services in a simple way, using a small extension to the WebResource element from the Europeana Data Model. The first draft recommendations were published in the deliverable D4.4 Recommendations for enhancing EDM to represent digital content as part of the [Europeana Cloud project](https://pro.europeana.eu/project/europeana-cloud).

In EDM, IIIF resources showing as cultural object are represented as instances of the class [edm:WebResource](../../EDM%20Core%20classes/edm_WebResource.md)**.**

This guide explains how providers can include suitable descriptions for these IIIF WebResources in the EDM metadata they send to Europeana. We include a formal definition of the new EDM elements used to submit IIIF resources according to the pattern explained here.

> [!IMPORTANT]
> The definitions of the terms **MUST**, **MUST NOT**, **SHOULD**, etc. used in this document can be found at <https://tools.ietf.org/html/rfc2119>

## Step 1: Providers MUST identify the type of link between the IIIF resource for the object and the object.

EDM uses the general property [ore:Aggregation](../../EDM%20Core%20classes/ore_Aggregation.md) about a provided cultural object to the "views" of this object on the web. In the case of IIIF resources, the suitable property **SHOULD** be

- [ore:Aggregation](../../EDM%20Core%20classes/ore_Aggregation.md)
- [ore:Aggregation](../../EDM%20Core%20classes/ore_Aggregation.md) OR [ore:Aggregation](../../EDM%20Core%20classes/ore_Aggregation.md) (if there is already an edm:isShownBy present).

See the EDM Definitions and [EDM - Mapping guidelines](../../../EDM%20-%20Mapping%20guidelines.md) for more information on the semantics of these properties.

## Step 2: Providers SHOULD supply an identifier for the WebResource referenced as a 'view' of the object.

EDM doesn't strictly require that the WebResource for a IIIF 'view' have a specific identifier. In a pure RDF context it could in fact be left without any identifier.

A IIIF viewer can generate views from the information supplied in the following steps. However, a non-IIIF viewer will not be able to do this.

For wider consumption of IIIF resources by Europeana data re-users, we recommend that providers SHOULD supply URIs for the IIIF 'view', that can be consumed by any traditional web client. The most natural way to do this is to use URLs that employ appropriate IIIF parameters on the base IIIF service so that clients obtain a good image, as in <https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1/full/full/0/native.jpg>

> [!NOTE]
> Note that in version 3.0 of the IIIF image API (<https://iiif.io/api/image/3.0/> ), the parameter “max”: will replace the “full” parameter to request the biggest allowable image as opposed to biggest image available.
>
> Note that Europeana encourages data providers to link to an image of the highest resolution as possible. It will allow Europeana to better serve its users by enabling the download of the images and browsing by technical features (e.g. pixel dimensions, MIME-type, colour palette).

> [!IMPORTANT]
> More details on the technical metadata extracted by Europeana from images are available in[Technical metadata in EDM (definitions)](../../../Europeana%20Data%20Model/EDM%20profiles/Technical%20metadata%20in%20EDM%20(definitions).md)

The URI for the WebResource MUST be the one of the media view and MUST NOT be the one of a IIIF manifests. Manifests are metadata files and not (media) views for a cultural object. The manifest resource represents a single object and any intellectual work or works embodied within that object <http://iiif.io/api/presentation/2.0/#manifest>.

> [!TIP]
> In practice:
>
> - Supply an identifier for the webResource referenced as ‘view’ for the object
> - Identify the type of link between the IIIF resource for the object and the object.

Example:

```java
<ore:Aggregation rdf:about="[ … ]">
[…]
    <edm:isShownBy rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1/full/full/0/native.jpg"/>
[…]
</ore:Aggregation>
[…]
<edm:WebResource rdf:about="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1/full/full/0/native.jpg"/>
[…]
```

> [!TIP]
> From IIIF v3.0 guidelines: [https://iiif.io/api/image/3.0/#uri-syntax](https://iiif.io/api/image/2.1/#uri-syntax): The IIIF Image API URI for requesting an image must conform to the following URI Template:
>
> {scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
>
> e.g. <http://www.example.org/image-service/abcd1234/info.json>

## Step 3: Providers MUST flag the WebResource as a IIIF-compliant resource

This is done by connecting the WebResource to a resource of type **svcs:Service** using svcs:has\_service and by indicating that the WebService conforms to ([dcterms:conformsTo](http://iiif.io/api/image/2.0/index.html#image-information)) the IIIF profile. The value of dcterms:conformsTo MUST be the URI <http://iiif.io/api/image>

## Step 4: The identifier of the Service MUST be the 'base URI' of the IIIF resource.

See the IIIF specifications for the definition of the base URI: <https://iiif.io/api/image/2.0/#uri-syntax>

> [!TIP]
> In practice:
>
> - Connect the [edm:WebResource](../../EDM%20Core%20classes/edm_WebResource.md) to a resource of type svcs:Service using svcs:has\_service (the identifier of the Service must be the ‘base URI’ of the IIIF resource)
> - Indicate that the WebService conforms to ([dcterms:conformsTo](https://iiif.io/api/image/2.0/index.html#image-information)) the IIIF profile. The value of [edm:WebResource](../../EDM%20Core%20classes/edm_WebResource.md) MUST be the URI <http://iiif.io/api/image>

Example:

```java
<edm:WebResource rdf:about="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1/full/full/0/native.jpg">
    <dcterms:isReferencedBy rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/manifest.json"/>
    <svcs:has_service rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1"/>
</edm:WebResource>
[…]
<svcs:Service rdf:about="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1">
[…]
```

> [!TIP]
> Make sure that you have enabled CORS [Cross Origin Resource Sharing=security feature for browsers] to enable Europeana to display the images

## Step 5: The provider MAY provide access to a IIIF Manifest

Optional: provide access to a IIIF manifest using [edm:WebResource](../../EDM%20Core%20classes/edm_WebResource.md).

Manifests are highly nested JSON documents that indicate what is the preferred way to render the IIIF resources. They can give information on how images are related to each other like the order that images should display, the structure of a document like a table of contents, and descriptive information for the resource and individual images.

The 'base' WebResource from steps 1 and 2 can be connected to a manifest URI using the property [edm:WebResource](../../EDM%20Core%20classes/edm_WebResource.md).

Specifications of the WebService URI (`<svcs:has_service rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1"/>`) should follow the recommendation made at

[http://iiif.io/api/image/2.0/#uri-syntax](http://iiif.io/api/image/2.0/#uri-syntax-):

> [!NOTE]
> *"When the base URI is dereferenced, the interaction SHOULD result in the Image Information document. It is RECOMMENDED that the response be a 303 status redirection to the Image Information document’s URI."*

```java
<edm:WebResource rdf:about="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1/full/full/0/native.jpg">
    <dcterms:isReferencedBy rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/manifest.json"/>
    <svcs:has_service rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1"/>
</edm:WebResource>
```

## Step 6: The provider MAY indicate a level of IIIF implementation.

A IIIF Manifest allow a IIIF viewer to render the image in a relevant setting. The 'base' WebResource from steps 1 and 2 can be connected to a manifest URI using the property dcterms:isReferencedBy.

The definition of a IIIF “protocol”, for example <http://iiif.io/api/image/2/level1.json>, can be added with a **doap:implements** as this property corresponds to the “protocol” element in the IIIF JSON context. However, Europeana itself will not exploit it now. But data re-users with specific needs might benefit from the availability of this information.

Example:

```java
<svcs:Service rdf:about="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1"/>
    <dcterms:conformsTo rdf:resource="http://iiif.io/api/image"/>
    <doap:implements rdf:resource="http://iiif.io/api/image/2/level2.json">
</svcs:Service>
```

> [!TIP]
> Specifications of the WebService URI should follow the recommendation made at <http://iiif.io/api/image/2.0/#uri-syntax> - *"When the base URI is dereferenced, the interaction SHOULD result in the Image Information document. It is RECOMMENDED that the response be a 303 status redirection to the Image Information document’s URI."*
