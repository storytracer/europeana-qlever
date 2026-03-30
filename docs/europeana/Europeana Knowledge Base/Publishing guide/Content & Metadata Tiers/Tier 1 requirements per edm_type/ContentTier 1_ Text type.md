---
tags:
  - '#quality'
  - '#framework'
  - '#text'
  - '#tiers'
  - '#epf'
  - '#content'
---

[Publishing guide](../../../Publishing%20guide.md) > [Content & Metadata Tiers](../../Content%20&%20Metadata%20Tiers.md) > [Tier 1 requirements per edm:type](../Tier%201%20requirements%20per%20edm_type.md)

# ContentTier 1: Text type

Text materials are meant to be read and not looked at; therefore, best practice for text-based materials is to publish documents in full, scanned in an adequate resolution to support their legibility, and, if possible, with an added plain-text layer to allow for searching within the content of a document. For easy reuse of your text materials it is recommended to allow users to download the documents in file formats that allow users to extract text.

If you are contributing text documents to Europeana because you want them to be discoverable in the Europeana website, then you need to provide at least a link to the file(s) of the document, a document viewer or a website on which the document can be accessed (edm:isShownAt). We recommend that a link to a still image file is at least 0.1 megapixel in size to have the means to create ~400 pixels preview images to represent the text material on the Europeana website.

|          |                                                              |                                                                                                     |
|:---------|:-------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|
| **Tier** | **edm:type=TEXT**                                            | **Rights**                                                                                          |
| **1**    | An image is available\* with 0.1mpx OR working edm:isShownAt | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements) |

**\*An image is available** with resolution >= 0.1mp: **true** if one of the edm:WebResource associated viaedm:isShownBy or edm:hasView exists AND technical metadata (ie. ebucore:hasMimetype filled) is extracted from that media resource

For example records per edm:type = TEXT, see page [Example records - content & metadata tiers](../Example%20records%20-%20content%20&%20metadata%20tiers.md) .

Related articles

- Page:

  [ContentTier 1: Text type](ContentTier%201_%20Text%20type.md)
- Page:

  [ContentTier 2-4: Text type](../Tier%202-4%20requirements%20per%20edm_type/ContentTier%202-4_%20Text%20type.md)
