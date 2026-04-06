
# Semantic enrichments

During Europeana’s data ingestion process, the received metadata undergoes semantic enrichment — a process in which more data is added to records by linking (or exploiting existing links) to contextual resources such as places, concepts, agents, time periods and organisations.

The first type of semantic enrichment is triggered by providers using links to vocabularies published as Linked Open Data. The [Europeana Data Model (EDM)](https://pro.europeana.eu/page/edm-documentation) gives support for contextual resources - the so-called ‘semantic layer'. This means that data partners can includ references from open (and multilingual) vocabularies like thesauri, authority lists, classifications, etc. in the metadata they send to Europeana. Note that these vocabularies can come either from the Europeana's partners or from third parties.

Europeana has developed a tool that ‘dereferences' contextual resources’ URIs, i.e., that fetches all the multilingual and semantic data that are published as Linked Open Data for vocabulary references. Europeana currently dereferences [several vocabularies](https://docs.google.com/spreadsheets/d/1BoDNolkcp_qfvVShdOZyGcf61XslcwKF2MdGcjgYs20/edit#gid=0). Note that this process requires the vocabularies to be mapped to EDM contextual classes, using standard models like SKOS - see the configuration files used for dereferencing on [GitHub](https://github.com/europeana/metis-vocabularies). If you would like to have your own vocabulary dereferenced, please mention it to your Europeana contact. The following pages describe how Europeana supports the Linked Open Data vocabularies used by data partners.

[Workflow for supporting new vocabularies](Semantic%20enrichments/Workflow%20for%20supporting%20new%20vocabularies.md)

[How to confirm if your vocabulary supports content negotiation?](Semantic%20enrichments/How%20to%20confirm%20if%20your%20vocabulary%20supports%20content%20negotiation_.md)

The second type of enrichment results from Europeana’s automatically attempting to link values found in the metadata to controlled terms from the Europeana Entity Collection.

The following pages outline the semantic enrichment process currently used at Europeana, explaining both the rationale and the methods applied.

[Europeana automatic enrichment with contextual resources](Semantic%20enrichments/Europeana%20automatic%20enrichment%20with%20contextual%20resources.md)

[Europeana automatic enrichment with organisations](Semantic%20enrichments/Europeana%20automatic%20enrichment%20with%20organisations.md)
