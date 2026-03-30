---
tags:
  - '#edm-mapping-guidelines'
---



# EDM - Mapping guidelines

The Europeana Data Model (EDM in short) is a theoretical data model that allows data to be presented in different ways according to the practices of the various domains which contribute data to Europeana. To create a practical implementation Europeana has not used all the classes and properties defined in the EDM model. In particular, the **ore:Proxy class** is not included because it is created within Europeana using data provided according to the Guidelines. Additionally, for its internal working Europeana utilises a different set of classes and properties. There are several [case studies](https://pro.europeana.eu/share-your-data/metadata#case-studies) that address particular aspects of using EDM.

If needed, these guidelines can be read in conjunction with the full EDM Definition and the EDM Primer, which explain the principles of how EDM works. You can also refer to the Europeana Semantic Element Specification (ESE), which has the full description of the Dublin Core elements and the ESE elements reused in EDM. These documents are available via the [EDM documentation page](https://pro.europeana.eu/page/edm-documentation).

The guidelines presented here describe only **the seven classes** from the full model that are currently implemented: the **three core classes** representing the cultural heritage object and the **four contextual classes** that may be associated with it.

The core classes are:

- [edm:ProvidedCHO](EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_ProvidedCHO.md) - the provided cultural heritage object
- [edm:WebResource](EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/edm_WebResource.md) -­ the web resource that is the digital representation
- [ore:Aggregation](EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/ore_Aggregation.md) -­ the aggregation that groups the classes together

Main contextual classes include:

- [edm:Agent](EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Agent.md) - who
- [edm:Place](EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_Place.md) - where
- [edm:TimeSpan](EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/edm_TimeSpan.md) -­ when
- [skos:Concept](EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/skos_Concept.md) - what
- [cc:License](EDM%20-%20Mapping%20guidelines/EDM%20Contextual%20classes/cc_License.md) - access and usage

> [!WARNING]
> Please note that the **EDM\_Mapping\_Guidelines\_v2.4\_102017 version in .pdf** is still available below. However, some sections in that version, are as of February 2023 outdated.
>
> The EDM Mapping Guidelines have been [Documentation update and edit history](EDM%20-%20Mapping%20guidelines/Documentation%20update%20and%20edit%20history.md)and you can get **the most recent version of this documentation via the following sections of the Europeana Knowledge Base.**

[EDM_Mapping_Guidelines_v2.4_102017 (1).pdf](../attachments/2dde35d1-b9fb-4601-bc51-1302be950148.pdf)
