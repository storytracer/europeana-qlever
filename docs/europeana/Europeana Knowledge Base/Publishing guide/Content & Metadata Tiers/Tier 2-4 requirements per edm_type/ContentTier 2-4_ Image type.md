---
tags:
  - '#framework'
  - '#content'
  - '#quality'
  - '#epf'
  - '#image'
  - '#tiers'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier 2-4 requirements per edm:type](../Tier%202-4%20requirements%20per%20edm_type.md)

# ContentTier 2-4: Image type

- [Content Tier 2 (Europeana as a showcase)](#content-tier-2-europeana-as-a-showcase)
- [Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)](#content-tier-3-europeana-as-a-distribution-platform-for-non-commercial-reuse)
- [Content Tier 4 (Europeana as a free reuse platform)](#content-tier-4-europeana-as-a-free-reuse-platform)
  - [Overview of Content tier 2-4 requirements for image files](#overview-of-content-tier-2-4-requirements-for-image-files)
    - [Before selecting one of the rights statements we list in this table, make sure that the work is in the Public Domain, that you hold the rights, or that you have the rights holders' permission](#before-selecting-one-of-the-rights-statements-we-list-in-this-table-make-sure-that-the-work-is-in-the-public-domain-that-you-hold-the-rights-or-that-you-have-the-rights-holders-permission)
- [Related articles](#related-articles)

### Content Tier 2 (Europeana as a showcase)

If you want to enable Europeana to use your image material as part of thematic collections and make it more accessible on the Europeana website, then you need to provide at least a direct link to an image file of at least 0.42 megapixel in size (e.g. ~800\*533 pixels). Additionally, the International Image Interoperability Framework (IIIF) is also supported by Europeana and can be used for displaying images on Europeana.

### Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)

If you want to make use of Europeana as a distribution platform that enables the use of your image files by private individuals, educators and researchers, then you need to provide at least a direct link to an image file of at least 0.95 megapixel in size (e.g. ~1,200\*800 pixels). In addition, you also need to make sure that the text documents come with one of the seven rights statements that allow reuse

- **4 Creative Commons licences: CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND;**
- **3 RightsStatements.org's statements: NoC-NC, NoC-OKLR, InC-EDU).**

### Content Tier 4 (Europeana as a free reuse platform)

If you want to make use of Europeana as a platform that enables the free reuse of your image files elsewhere then, in addition to the criteria described for Tier 3 above, you also need to make sure that the image file comes with a rights statement that allows **free reuse (CC BY, CC BY-SA CC0, or PDM)**.

#### Overview of Content tier 2-4 requirements for image files

|          |                                                                                                                                        |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|:---------|:---------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **TIER** | **edm:type=IMAGE**                                                                                                                     | **Rights\*\*\***                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **2**    | <ul><li><p>Thumbnail is available*</p></li><li><p>An image is available with resolution &gt;= 0.42megapixel (~800x533)**</p></li></ul> | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements)                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **3**    | <ul><li><p>Thumbnail is available*</p></li><li><p>An image is available with resolution &gt;= 0.95megapixel (1200x800)**</p></li></ul> | Associated image has either **open** or **restricted** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md): <br/><ul><li><p>4 creative commons CC-BY-NC, CC BY-ND, CC-BY-NC-ND, CC-BY-NC-SA</p></li><li><p>3 <a class="external-link" href="http://rightstatements.org" rel="nofollow">http://rightstatements.org</a>  NC-OKLR, NoC-NC, InC-EDU</p></li></ul> |
| **4**    | <ul><li><p>Thumbnail is available*</p></li><li><p>An image is available with resolution &gt;= 0.95megapixel (1200x800)**</p></li></ul> | Associated image has **only open** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md): <br/> PDM, CC-0, CC-BY, CC-BY-SA                                                                                                                                                                                                                                      |

\***Thumbnail is available** = true only if the "edm:EuropeanaAggregation/edm:preview" is filled and the associated edm:WebResource exists with technical metadata (ie. ebucore:hasMimetype filled)

**\*\*An image** =true if one of the edm:WebResource associated via edm:isShownBy or edm:hasView exists AND technical metadata (ie. ebucore:hasMimetype filled) is extracted from that media resource; To calculate the size of the image use this megapixel calculator <https://www.pixelscalculator.com/megapixel-calculator/>

**\*\*\*Rights: Important note on your willingness to open up for reuse relevant for contentTier:3 and contentTier:4**

Because copyright restrictions often prevent the public from using, sharing, and creatively engaging with digital collections, we encourage data providers to use rights statements that allow reuse where possible.

Stimulating reuse is at the core of the [Europeana Publishing Framework](https://pro.europeana.eu/post/publishing-framework):

The framework introduces [four tiers of criteria](https://pro.europeana.eu/files/Europeana_Professional/Publications/Publishing_Framework/Europeana_publishing_framework_content.pdf) for content by taking into account not just the quality of the content (e.g. resolution of photos of an object), but also the selected rights statement. The greater openness of the content you allow, the higher content tier can the provided object achieve, meaning it can benefit audiences in a more significant way, as we outline [here](https://pro.europeana.eu/page/open-and-reusable-digital-cultural-heritage).

Only **content of the highest quality that can be freely reused or reused to some degree** can reach the highest content tiers (i.e. content tier 3 and 4).

If the **content quality is too low** to reach content tiers 3 or 4, the rights statement is not taken into account by the algorithm that calculates content tiers, meaning that you can use any of the available rights statements supported by Europeana, as the chosen rights statement will not play a role.

|  **Content tier 3**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |  **Content tier 4**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <br/> Only rights statements that allow **some reuse**: <br/>[![](../../../../attachments/0547a851-98f5-4ad7-968a-ae1566e20132.png)](https://creativecommons.org/licenses/by-nc/4.0/)[![](../../../../attachments/791d4dc4-9517-4d8d-997a-a292579f3142.png)](https://creativecommons.org/licenses/by-nd/4.0/)[![](../../../../attachments/303d3a56-ec3e-4117-9c74-e3aaba239a75.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)[![](../../../../attachments/4a3ffdc0-f978-49a2-a086-b28696c62b3c.png)](https://creativecommons.org/licenses/by-nc-nd/4.0/)[![](../../../../attachments/4cfce39a-6816-4652-9a02-90af249444b1.png)](http://rightsstatements.org/vocab/InC-EDU/1.0/)[![](../../../../attachments/967484f4-40e0-4ec1-b0a9-709d2c2ce08b.png)](http://rightsstatements.org/vocab/NoC-OKLR/1.0/)[![](../../../../attachments/642d3713-5649-448c-9bf5-74ae359e162e.png)](http://rightsstatements.org/vocab/InC-NC/1.0/) | <br/> Only rights statements that allow **free reuse**: <br/>[![](../../../../attachments/9d0d4697-d41c-4744-8d07-b8cbfdba9ee4.png)](https://creativecommons.org/publicdomain/mark/1.0/)[![](../../../../attachments/b3d99ce6-b559-4c71-bf12-f9ec3cf4a2f3.png)](https://creativecommons.org/publicdomain/zero/1.0/)[![](../../../../attachments/f1c51cdd-b91b-4527-855d-5d3d6cd4eb8a.png)](https://creativecommons.org/licenses/by/4.0/)[![](../../../../attachments/bc3b1997-5b2a-4bdb-8d60-f31c05375b0e.png)](https://creativecommons.org/licenses/by-sa/4.0/)  <br/>*Before selecting one of the rights statements we list in this table, make sure that the work is in the Public Domain, that you hold the rights, or that you have the rights holders' permission* |

> [!IMPORTANT]
> The above table demonstrates the connection between the rights statement and the assigned content tier.
>
> Please note that the selected rights statement is only one of the criteria for the specific content tier.
>
> For guidelines on which URI for specific rights statement you should use when providing EDM, consult [Providing copyright metadata to Europeana](../../Licenses%20&%20Rights%20statements/Providing%20copyright%20metadata%20to%20Europeana.md).
>
> More information about identifying whether a work is subject to copyright or not is available [here](https://pro.europeana.eu/page/identifying-copyright-in-collection-items).

> [!TIP]
> Example records for **edm:type = IMAGE** are listed here [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .

.

### Related articles

- Page:

  [ContentTier 1: Image type](../Tier%201%20requirements%20per%20edm_type/ContentTier%201_%20Image%20type.md)
- Page:

  [ContentTier 2-4: Image type](ContentTier%202-4_%20Image%20type.md)
