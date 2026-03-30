---
tags:
  - '#tiers'
  - '#video'
  - '#content'
  - '#quality'
  - '#framework'
  - '#epf'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier 1 requirements per edm:type](../Tier%201%20requirements%20per%20edm_type.md)

# ContentTier 1: Video type

The quality of streaming video depends on a number of factors, such as the quality of the source file, the type of encoding chosen for compression, the frame rate and bitrate of the file, and the transfer rates that the network supports. Video streaming relies on a number of standards whose support varies across different browsers. The quality criteria of a video file are therefore as much dependent on the efficiency of the file compression as on the setup of the end-user. In equal parts the robustness and connectedness of the video playout service come into play.

Moving image cultural heritage materials should be offered in their original aspect ratio. The codec and file format used are preferably in an open format that can be played in a web browser without the need for specific proprietary software or plugins.

If you are contributing video material because you want it to be discoverable via the Europeana website then you need to provide at least a link to the video file or a website on which the video file can be accessed. It is recommended to provide both, the direct link to the video file and the link to the website on which the video file can be accessed in its full information context (edm:isShownAt). It is also recommended (not required) to also provide a link to a still image file to have the means to create preview images to illustrate search results on the Europeana website. Usually, this is a representative still from the video or, for example, a film poster.

|          |                                                             |                                                                                                     |
|:---------|:------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|
| **Tier** | **edm:type=VIDEO**                                          | **Rights**                                                                                          |
| **1**    | A video is available\* <br/> or <br/> working edm:isShownAt | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements) |

**A video is available:**  **true** if one of the edm:WebResource associated via edm:isShownBy or edm:hasView exists AND technical metadata (ie. ebucore:hasMimetype filled) is extracted from that media resource

For example records per edm:type = VIDEO, see page [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .

### Related articles

- Page:

  [ContentTier 1: Video type](ContentTier%201_%20Video%20type.md)
- Page:

  [ContentTier 2-4: Video type](../Tier%202-4%20requirements%20per%20edm_type/ContentTier%202-4_%20Video%20type.md)
