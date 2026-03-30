---
tags:
  - '#tiers'
  - '#content'
  - '#framework'
  - '#quality'
  - '#text'
  - '#epf'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier 2-4 requirements per edm:type](../Tier%202-4%20requirements%20per%20edm_type.md)

# ContentTier 2-4: Text type

- [Content Tier 2 (Europeana as a showcase)](#content-tier-2-europeana-as-a-showcase)
- [Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)](#content-tier-3-europeana-as-a-distribution-platform-for-non-commercial-reuse)
- [Content Tier 4 (Europeana as a free reuse platform)](#content-tier-4-europeana-as-a-free-reuse-platform)
  - [Overview of Content tier 2-4 requirements for text files](#overview-of-content-tier-2-4-requirements-for-text-files)
- [Related articles](#related-articles)

### Content Tier 2 (Europeana as a showcase)

If you want to enable Europeana to present your text materials as part of thematic collections and make them more accessible on the Europeana website then you need to provide at least a direct link to the file(s) of the document, in PDF file format, which will be made directly available on thematic collections pages via a PDF viewer. Although Europeana currently does not support a full-text search across documents, we recommend adding an embedded text layer in PDF files to allow for searching inside the document. Additionally, the International Image Interoperability Framework (IIIF) is also supported by Europeana and can be used for displaying text materials on Europeana to allow text collections to qualify as Tier 2. For single page text material (e.g. manuscripts, letters), providing direct links to an image file of at least 0.42 megapixel in size is also an option.

### Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)

If you want to make use of Europeana as a distribution platform that enables the use of your text materials by private individuals, educators and researchers then, in addition to the criteria described for Tier 2 above, you also need to make sure that the text documents come with one of the seven rights statements that allow reuse

- **4 Creative Commons licenses: CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND;**
- **3 RightsStatements.org's statements: NoC-NC, NoC-OKLR, InC-EDU).**

If you provide text as image files, they need to be at least 0.95 megapixel in size.

### Content Tier 4 (Europeana as a free reuse platform)

If you want to make use of Europeana as a platform that enables the free reuse of your text materials then, in addition to the criteria described for Tier 2 above, you also need to make sure that the text documents come with a rights statement that allows **free reuse (CC BY, CC BY-SA, CC0 or PDM).**

#### Overview of Content tier 2-4 requirements for text files

|          |                                                                                                                                                                                       |                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|:---------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **TIER** | **edm:type=TEXT**                                                                                                                                                                     | **Rights** *\*\**                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **2**    | <ul><li><p>A text resource is available with mimetype "application/pdf" *</p></li></ul> OR <br/><ul><li><p>image is available with resolution &gt;= 0.42mpx</p></li></ul>             | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements)                                                                                                                                                                                                                                                                                                                                                 |
| **3**    | <ul><li><p>A text resource is available with mimetype "application/pdf" *</p></li></ul> OR <br/><ul><li><p>image is available  with resolution &gt;= 0.95mpx (1200x800)</p></li></ul> | Associated text resource has either **open** or **restricted** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md): <br/><ul><li><p>4 creative commons CC-BY-NC, CC BY-ND, CC-BY-NC-ND, CC-BY-NC-SA</p></li><li><p>3 http://rightstatements.org NC-OKLR, NoC-NC, InC-EDU</p></li></ul> |
| **4**    | <ul><li><p>A text resource is available with mimetype "application/pdf"*</p></li></ul> OR <br/><ul><li><p>image with resolution &gt;= 0.95mp (1200x800)</p></li></ul>                 | Associated text resource has **only open** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md): <br/> PDM, CC-0, CC-BY, CC-BY-SA                                                                                                                                                       |

 \***A text resource is available**=true if one of the edm:WebResource associated via edm:isShownBy or edm:hasView exists AND technical metadata (ie. ebucore:hasMimetype filled) is extracted from that media resource.

\*\***Rights: Important note on your willingness to open up for reuse relevant for contentTier:3 and contentTier:4.** Only content of the highest quality that can be freely reused or reused to some degree can reach the highest content tiers. If the content quality is too low to reach content tiers 3 or 4, the rights statement is not taken into account by the algorithm that calculates content tiers, meaning that you can use any of the available rights statements supported by Europeana, as the chosen rights statement will not play a role.

> [!IMPORTANT]
> For guidelines on which URI for specific rights statement you should use when providing EDM, consult [Providing copyright metadata to Europeana](../../Licenses%20&%20Rights%20statements/Providing%20copyright%20metadata%20to%20Europeana.md).
>
> More information about identifying whether a work is subject to copyright or not is available [here](https://pro.europeana.eu/page/identifying-copyright-in-collection-items).

> [!TIP]
> Example records for **edm:type = TEXT** are listed here [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .

### Related articles

- Page:

  [ContentTier 1: Text type](../Tier%201%20requirements%20per%20edm_type/ContentTier%201_%20Text%20type.md)
- Page:

  [ContentTier 2-4: Text type](ContentTier%202-4_%20Text%20type.md)
