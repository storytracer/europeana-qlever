---
tags:
  - '#content'
  - '#quality'
  - '#3d'
  - '#epf'
  - '#framework'
  - '#tiers'
---

# ContentTier 1: 3D type

3D content refers to a digital object with 3D geometry. 2D representations (images) of three-dimensional real-world objects (e.g. sculptures) should not be given the type 3D in Europeana records.

The quality of 3D content depends on a number of factors, including but not limited to the number of points and vertices, the underlying research and production methods, and the choices made in processing the data. For users the quality of their experience of 3D also depends on high speed connectivity, load times and their set up. The ability to reuse 3D content depends on the availability of metadata that describes how the content has been created.

If you are contributing 3D material because you want it to be discoverable via the Europeana website then you need to provide, as a minimum, a landing page where the object can be seen in full informational context (**in the edm:isShownAt property**). This landing page (in edm:isShownAt) must include a working 3D viewer or link to the viewer/file.

You must also provide a link to a 2D image file large enough to create a preview image (in the edm:object property) to illustrate search results on the Europeana collections website, for example a scene within a model which could be offered as a preview.

|          |                                                                                                                                                                                                      |                                                                                                     |
|:---------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|
| **Tier** | **edm:type=3D**                                                                                                                                                                                      | **Rights**                                                                                          |
| **1**    | <ul><li><p>Working edm:isShownAt with 3D viewer or link to viewer/file</p></li><li><p>Thumbnail is available*</p></li><li><p>No other media resources (edm:isShownBy or edm:hasView)**</p></li></ul> | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements) |

\*Thumbnail is available: true only if the "edm:EuropeanaAggregation/edm:preview" is filled and the associated edm:WebResource exists with technical metadata (ie. ebucore:hasMimetype filled)

\*\*Note that if there are other media resources available, the following must be true: at least one working edm:WebResource associated via edm:isShownBy and/or edm:hasView exists that is not an image (“image/...”) or PDF (“application/pdf”). Otherwise the record will be classified as content tier 0.

### Related articles

- Page:

  [ContentTier 2-4: 3D type](../Tier%202-4%20requirements%20per%20edm_type/ContentTier%202-4_%203D%20type.md)
- Page:

  [Twin it! 3D for Europe’s culture webinar series (part I)](../../../Publishing%20guide%20for%203D%20content/Twin%20it!%203D%20for%20Europe’s%20culture%20webinar%20series%20(part%20I).md)
- Page:

  [ContentTier 1: 3D type](ContentTier%201_%203D%20type.md)
