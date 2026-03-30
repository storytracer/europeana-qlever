---
tags:
  - '#quality'
  - '#image'
  - '#tiers'
  - '#epf'
  - '#framework'
  - '#content'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier 1 requirements per edm:type](../Tier%201%20requirements%20per%20edm_type.md)

# ContentTier 1: Image type

Images are visual resources for users to look at. It is best practice for image files to be published in a quality for a user to tell what the image is about. Image quality is also expected to reflect the changes in technologies over the last years: displays’ screen resolutions have increased significantly since then. Correspondingly, user expectations have changed too, which requires image quality to be significantly higher than in 2008 when Europeana started.

If you are contributing image material because you want it to be discoverable in the Europeana website, then you must provide a direct link to an image file of at least 0.1 megapixel in size to have the means to create ~400 pixel-wide preview images to illustrate search results in the Europeana website (edm:isShownBy). In addition, we strongly recommend to also provide a link to a website on which the image file can be accessed in its full information context (edm:isShownAt).

|          |                                                                                                                                           |                                                                                                     |
|:---------|:------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|
| **Tier** | **edm:type=IMAGE**                                                                                                                        | **Rights**                                                                                          |
| **1**    | <ul><li><p>Thumbnail is available*</p></li><li><p>An image is available** with resolution &gt;= 0.1megapixel (&gt;=300x350)</p></li></ul> | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements) |

**\*Thumbnail is available**: **true** only if the "edm:EuropeanaAggregation/edm:preview" is filled and the associated edm:WebResource exists with technical metadata (ie. ebucore:hasMimetype filled)

**\*\*An image is available** with resolution >= 0.1mp: **true** if one of the edm:WebResource associated via edm:isShownBy or edm:hasView exists AND technical metadata (ie. ebucore:hasMimetype filled) is extracted from that media resource. To calculate the size of the image use this megapixel calculator <https://www.pixelscalculator.com/megapixel-calculator/>

For example records per edm:type = IMAGE, see page [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .

### Related articles

- Page:

  [ContentTier 1: Image type](ContentTier%201_%20Image%20type.md)
- Page:

  [ContentTier 2-4: Image type](../Tier%202-4%20requirements%20per%20edm_type/ContentTier%202-4_%20Image%20type.md)
