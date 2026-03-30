---
tags:
  - '#portal-queries'
  - '#search-api'
  - '#api-queries'
---

[User Guides & Training](../User%20Guides%20&%20Training.md)

# How to search Europeana website and API

# Introduction

Searching for specific metadata records or datasets across the Europeana website and APIs may not always be fully self explanatory. For the Europeana website, there is [a dedicated page](https://www.europeana.eu/en/help/search-tips) that explains how to search on the <http://europeana.eu> . The [Europeana APIs Documentation](../Europeana%20APIs%20Documentation.md) also explaining and listing all the possible search terms. But for some specific cases it is handy to have a few shortcuts, some specific queries to help solving a specific problem. In addition, we would like to also help you to search across our production website and APIs in the same way as on our preview website and APIs. This is what this page is aiming to achieve.

# Production vs preview

[Europeana.eu](http://Europeana.eu) is the website you are familar with, which is where everything that is published will be visible. But we also have a [preview environment](https://metis-preview-portal.eanadev.org/en), where everything will be before its published. You can work with this preview environment in the same way as with the production environment, but it is not really public as it is also not indexed by Google. Here you also find datasets that are depublished (e.g. because of broken links). This is also the staging environment we use to pause for feedback, before publishing the datasets. Same as for the websites, also APIs are available for production and preview.

When using the production Europeana APIs, it always starts with https://api.europeana.eu/, while for preview it starts with https://metis-preview-api-prod.eanadev.org/. In both environments, searching works in the exact same way.

# Searching on europeana.eu

When searching on the Europeana website, the URL always starts with https://www.europeana.eu/en/search?, followed by the actual query, e.g. query=who%3AVermeer. Looking for everything from Vermeer will then lead to this URL: <https://www.europeana.eu/en/search?query=who%3AVermeer&view=grid>. With this in mind, more search queries can be developed and also search queries on our preview environment can be developed. The corresponding URL in Europeana preview is <https://metis-preview-portal.eanadev.org/en/search?query=who%3AVermeer&view=grid> .

Below we list a few more queries that you asked us about in the past:

- content and metadata tiers combined [query=edm\_datasetName%3A08604%2A%20contentTier%3A2%20AND%20metadataTier%3AB](https://www.europeana.eu/en/search?query=edm_datasetName%3A08604%2A%20contentTier%3A2%20AND%20metadataTier%3AB&view=grid)
- by agents

  - [query=who%3AVermeer](https://www.europeana.eu/en/search?query=who%3AVermeer&view=grid)
  - [query=who%3ARembrandt%20OR%20who%3AVermeer](https://www.europeana.eu/en/search?query=who%3ARembrandt%20OR%20who%3AVermeer&view=grid)
- by year

  - [query=YEAR%3A1910&view=grid](https://www.europeana.eu/en/search?query=YEAR%3A1910&view=grid)
  - [query=YEAR%3A%5B1525%20TO%201527%5D](https://www.europeana.eu/en/search?query=YEAR%3A%5B1525%20TO%201527%5D)
- by specific file extension in isShownBy

  - .wmv extension: [view=grid&query=provider\_aggregation\_edm\_isShownBy%3A%2a.wmv%2a](https://www.europeana.eu/en/search?view=grid&query=provider_aggregation_edm_isShownBy%3A%2a.wmv%2a)
  - .jpg extension: [view=grid&query=provider\_aggregation\_edm\_isShownBy%3A%2a.jpg%2a](https://www.europeana.eu/en/search?view=grid&query=provider_aggregation_edm_isShownBy%3A%2a.jpg%2a)
- IIIF items in Europeana [query=sv\_dcterms\_conformsTo%3A%2Aiiif%2A](https://www.europeana.eu/en/search?query=sv_dcterms_conformsTo%3A%2Aiiif%2A&view=grid&page=1)
- provider\_aggregation\_edm\_isShownAt [?query=provider\_aggregation\_edm\_isShownAt%3A%2Aperiodicals.lib.unideb.hu%2Flista.php%3Fc%3Drege%2A](https://www.europeana.eu/en/search?query=provider_aggregation_edm_isShownAt%3A%2Aperiodicals.lib.unideb.hu%2Flista.php%3Fc%3Drege%2A&view=grid)
- has\_media:\* OR DATA\_PROVIDER:"The British Library" [?query=has\_media%3A%2A%20AND%20DATA\_PROVIDER%3A%22The%20British%20Library%22&](https://www.europeana.eu/en/search?query=has_media%3A%2A%20AND%20DATA_PROVIDER%3A%22The%20British%20Library%22&view=grid)
- has\_thumbnails [?query=has\_thumbnails%3Atrue&qf=IMAGE\_SIZE%3Alarge&qf=IMAGE\_SIZE%3Amedium&qf=IMAGE\_SIZE%3Aextra\_large&qf=TYPE%3A%22IMAGE%22&locale=en&](https://www.europeana.eu/en/search?query=has_thumbnails%3Atrue&qf=IMAGE_SIZE%3Alarge&qf=IMAGE_SIZE%3Amedium&qf=IMAGE_SIZE%3Aextra_large&qf=TYPE%3A%22IMAGE%22&locale=en&view=grid)
- NOT(has\_media:\*) [?query=NOT%28has\_media%3A%2A%29&qf=DATA\_PROVIDER%3A%22The%20Trustees%20of%20the%20Natural%20History%20Museum%2C%20London%22&qf=PROVIDER%3A%22OpenUp%5C%21%22](https://www.europeana.eu/en/search?query=NOT%28has_media%3A%2A%29&qf=DATA_PROVIDER%3A%22The%20Trustees%20of%20the%20Natural%20History%20Museum%2C%20London%22&qf=PROVIDER%3A%22OpenUp%5C%21%22&locale=en&view=grid)
- timestamp\_created [?query=timestamp\_created%3A%5B2016-01-01T00%3A00%3A0.000Z%20TO%202016-08-28T00%3A00%3A00.000Z%5D](https://www.europeana.eu/en/search?query=timestamp_created%3A%5B2016-01-01T00%3A00%3A0.000Z%20TO%202016-08-28T00%3A00%3A00.000Z%5D&qf=IMAGE_SIZE%3Alarge&qf=IMAGE_SIZE%3Amedium&qf=IMAGE_SIZE%3Aextra_large&view=grid&page=1)
- […..]

# Searching using the Europeana APIs

You can use the Europeana APIs to search for and retrieve information about your collections. Before getting started, you will need to request a personal API key and configure your browser to make API calls using your key. You can find detailed instructions on how to request and use a personal key [Accessing the APIs](../Europeana%20APIs%20Documentation/Accessing%20the%20APIs.md).

We have also prepared a dedicated [API FAQ](../Europeana%20APIs%20Documentation/API%20FAQ.md) on the Europeana APIs FAQ page to help you get started.
