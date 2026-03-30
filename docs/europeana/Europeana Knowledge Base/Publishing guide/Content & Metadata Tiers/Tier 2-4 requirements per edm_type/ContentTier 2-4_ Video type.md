---
tags:
  - '#content'
  - '#epf'
  - '#framework'
  - '#video'
  - '#tiers'
  - '#quality'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier 2-4 requirements per edm:type](../Tier%202-4%20requirements%20per%20edm_type.md)

# ContentTier 2-4: Video type

- [Content Tier 2 (Europeana as a showcase)](#content-tier-2-europeana-as-a-showcase)
- [Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)](#content-tier-3-europeana-as-a-distribution-platform-for-non-commercial-reuse)
- [Content Tier 4 (Europeana as a free reuse platform)](#content-tier-4-europeana-as-a-free-reuse-platform)
  - [Overview of Content tier 2 -4 for video files](#overview-of-content-tier-2-4-for-video-files)
- [Related articles](#related-articles)

### Content Tier 2 (Europeana as a showcase)

If you want to enable Europeana to use your video material as part of thematic collections and make it more accessible on the Europeana website then the video needs to be **embeddable** (any [oEmbed](http://oembed.com/) compliant player is supported by Europeana) or you need to provide at least a **direct link to a video file** in a format that can be played directly by [modern browsers and supported in HTML5]( https://developer.mozilla.org/en-US/docs/Web/HTML/Supported_media_formats). The video file should have a minimum vertical resolution (height) of 480 pixels. Video files that meet these requirements will be accessible directly on the thematic collections pages as embedded videos.

### Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)

If you want to make use of Europeana as a distribution platform that enables the use of your video files by private individuals, educators and researchers then, in addition to the criteria described for Tier 2 above, you also need to make sure that the video file comes with one of the seven rights statements that allow **reuse:**

- **4 Creative Commons licences: CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND;**
- **3** [**RightsStatements.org**](http://RightsStatements.org)**'s statements: NoC-NC, NoC-OKLR, InC-EDU).**

### Content Tier 4 (Europeana as a free reuse platform)

If you want to make use of Europeana as a platform that enables the free reuse of your video files then, in addition to the criteria described for Tiers 2 and 3 above you also need to make sure that the video file comes with a rights statement that allows **free reuse (CC BY, CC BY-SA, CC0 or PDM).**

#### Overview of Content tier 2 -4 for video files

|          |                                                                                                                                    |                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
|:---------|:-----------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **TIER** | **edm:type=VIDEO**                                                                                                                 | **Rights\*\*\***                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **2**    | A video is available with vertical resolution equal <br/> or <br/> higher than 480 pixels OR embeddable media as edm:isShownBy\*\* | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements)                                                                                                                                                                                                                                                                                                                                                  |
| **3**    | A video is available with vertical resolution equal <br/> or <br/> higher than 480 pixels OR embeddable media as edm:isShownBy\*\* | Associated sound resource has either **open or restricted** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md)**:** <br/><ul><li><p>4 creative commons CC-BY-NC, CC BY-ND, CC-BY-NC-ND, CC-BY-NC-SA</p></li><li><p>3 http://rightstatements.org NC-OKLR, NoC-NC, InC-EDU</p></li></ul> |
| **4**    | A video is available with vertical resolution equal <br/> or <br/> higher than 480 pixels OR embeddable media edm:isShownBy\*\*    | Associated sound resource has **only open** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md)**:** <br/> PDM, CC-0, CC-BY, CC-BY-SA                                                                                                                                                   |

For display purposes the **edm:object** value can be used to represent an illustrative image for the video type records. Example [here](https://www.europeana.eu/en/search?page=1&qf=PROVIDER%3A%22EUscreen%22&query=edm_datasetName%3A2051943_%2A&view=grid) and [here](https://api.europeana.eu/record/2051943/data_euscreenXL_EUS_002032C1E82C4D919C81F218B2CA90E7.json?wskey=nLbaXYaiH).

**\*A video resource is available**=true if one of the edm:WebResource associated via edm:isShownBy or edm:hasView exists AND technical metadata (ie. ebucore:hasMimetype filled) is extracted from that media resource

**\*\*Embeddable media as edm:isShownBy - list of URLs validated for embedding**

The \* wildcard means that it can match any text within that section of the URL. Also note that anything after the end of the URL pattern is acceptable.

- SoundCould

  ```java
  http://soundcloud.com/*
  https://soundcloud.com/*
  ```
- Vimeo

  ```java
  https://vimeo.com/*
  https://vimeo.com/album/*/video/*
  https://vimeo.com/channels/*/*
  https://vimeo.com/groups/*/videos/*
  https://vimeo.com/ondemand/*/*
  https://player.vimeo.com/video/*
  http://vimeo.com/*
  http://vimeo.com/album/*/video/*
  http://vimeo.com/channels/*/*
  http://vimeo.com/groups/*/videos/*
  http://vimeo.com/ondemand/*/*
  http://player.vimeo.com/video/*
  ```
- YouTube

  ```java
  https://youtube.com/watch*
  https://youtube.com/v/*
  https://www.youtube.com/watch*
  https://www.youtube.com/v/*
  https://youtu.be/*
  ```
- Dismarc

  ```java
  http://www.dismarc.org/player/*
  http://eusounds.ait.co.at/player/*
  ```
- Europeana

  ```java
  http://archives.crem-cnrs.fr/archives/items/*/*
  http://www.ccma.cat/tv3/alacarta/programa/titol/video/*/*
  http://www.ina.fr/video/*
  http://www.ina.fr/*/video/*
  http://api.picturepipe.net/api/html/widgets/public/playout_cloudfront?token=*
  https://api.picturepipe.net/api/html/widgets/public/playout_cloudfront?token=*
  http://www.theeuropeanlibrary.org/tel4/newspapers/issue/fullscreen/*
  ```
- BritishLibrary

  ```java
  http://sounds.bl.uk/embed/*
  ```
- EUScreen

  ```java
   http://www.euscreen.eu/item.html*
  ```

\*\***Rights: Important note on your willingness to open up for reuse relevant for contentTier:3 and contentTier:4.** Only content of the highest quality that can be freely reused or reused to some degree can reach the highest content tiers. If the content quality is too low to reach content tiers 3 or 4, the rights statement is not taken into account by the algorithm that calculates content tiers, meaning that you can use any of the available rights statements supported by Europeana, as the chosen rights statement will not play a role.

> [!IMPORTANT]
> For guidelines on which URI for specific rights statement you should use when providing EDM, consult [Providing copyright metadata to Europeana](../../Licenses%20&%20Rights%20statements/Providing%20copyright%20metadata%20to%20Europeana.md).
>
> More information about identifying whether a work is subject to copyright or not is available [here](https://pro.europeana.eu/page/identifying-copyright-in-collection-items).

> [!TIP]
> Example records for **edm:type = VIDEO** are listed here: [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .

### Related articles

- Page:

  [ContentTier 1: Video type](../Tier%201%20requirements%20per%20edm_type/ContentTier%201_%20Video%20type.md)
- Page:

  [ContentTier 2-4: Video type](ContentTier%202-4_%20Video%20type.md)
