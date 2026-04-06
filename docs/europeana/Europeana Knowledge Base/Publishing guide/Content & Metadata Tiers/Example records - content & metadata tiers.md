---
tags:
  - '#example-record'
  - '#content-tiers'
  - '#edm-type'
  - '#metadata-tiers'
---

# Example records - content & metadata tiers

In addition to the written requirements and recommendations for each of the content and metadata tiers, we have developed example records to show what these requirements mean in practice.

The idea behind the example records was to show Europeana data providers what is required to reach each tier of the EPF (both metadata and content), with clear examples [in the Europeana preview portal](https://metis-preview-portal.eanadev.org/en/search?page=1&query=%20proxy_dcterms_isPartOf%3A%22Europeana%20Foundation%20Example%20Records%22%2A&view=grid) which are [also available as xml](https://drive.google.com/drive/folders/13ieByNLQBAjGgpJBM25QffZxGhVSzzp7).

They show the minimum requirements for the higher tiers to encourage data providers to reach for a higher quality so they are not meant to look the best but rather to show the lowest barrier to entry.

The **example records** are arranged into six datasets, as follows:

- one dataset displaying [**metadata quality**](https://metis-preview-portal.eanadev.org/en/search?query=edm_datasetName%3A587_%2A), where:

  - the records represent each metadata tier (A, B, C) also tier 0 and the EDM recommendations. They show the properties that are required to create a record of that specific metadata tier.
- one dataset per digital **content type** (as represented in the EDM property edm:type as either [IMAGE](https://metis-preview-portal.eanadev.org/en/search?query=edm_datasetName%3A586_%2A&page=1&view=grid), [VIDEO](https://metis-preview-portal.eanadev.org/en/search?query=edm_datasetName%3A584_%2A&page=1&view=grid), [SOUND](https://metis-preview-portal.eanadev.org/en/search?query=edm_datasetName%3A585_%2A&page=1&view=grid), [TEXT](https://metis-preview-portal.eanadev.org/en/search?query=edm_datasetName%3A583_%2A&page=1&view=grid)) where:

  - For the records where the digital content is image based (with **edm:type IMAGE**) there are example records for each tier using objects directly linked from the metadata, in this case jpeg files, but also examples for each tier using IIIF links.
  - For video items (records with **edm:type VIDEO**) the examples for each tier include those with an object directly linked from the metadata and those with a link to an embeddable video.
  - For records with sounds (**edm:type SOUND**) there are examples for directly linked and embeddable items.
  - For text objects (**edm:type TEXT**), 3 lots of example records were created in one dataset, one for direct links to a text object such as a PDF, one set for metadata containing links to an image, e.g. jpeg, and finally one set of records containing IIIF links.
