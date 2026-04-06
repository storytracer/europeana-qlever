
# Documentation update and edit history

2025-06-02 **Antoine Isaac, Adina Ciocoiu**

- Amended edm:object recommendation for distinction with edm:isShownBy.
- Distinction made clearer between information in properties dcterms:spatial and edm:currentLocation

2025-01-28 **Nuno Freire**

- Link added from the [Technical metadata in EDM (definitions)](../Europeana%20Data%20Model/EDM%20profiles/Technical%20metadata%20in%20EDM%20(definitions).md) to the [Media policy](../Media%20policy.md).
- Added a note about the incorrect usage of “rdf:resource” with “xml:lang”.

2024-05-23 **Nuno Freire, Adina Ciocoiu**

- skos:notation information added on edm:TimeSpan class

2023-11-30 **Henning Scholz, Adina Ciocoiu**

- Note on the strongly recommended IsShownAt property

2023-03-06 V2.5 - **Adina Ciocoiu, Antoine Isaac, Nuno Freire**

- Added missing hyphen to date related information YYYY-MMDD into YYY-MM-DD in dc:date, dcterms:temporal, dcterms:created, dcterms:issues properties of edm:providedCHO, edm:Webresource, edm:Agent, edm:Timespan classes.
- Amended dc:type in edm:ProvidedCHO
- Table listing for edm:WebResource
- Closing tag for edm:ugc
- Properties in the record alligned
- Explanation on the order of EDM classes and properties
- Added missing rda2Gr namespace
- Overall update of links where they were outdated
- Corrected reference on cc:deprecatedOn
- Clarification on display of edm:rights
- Merged example record explanations with the respective XML snippets
- Moved Annex 3 Mapping for RDA Group 2 properties to edm:Agent class, and note amended
- Removed the "anomaly" concerning the use of some Dublin Core properties with literals while they allow only non-literal values. Since then, DCMI has changed the specification of these properties, turning the formal "range" specifications into less formal "range includes" recommendations.

2017-10-06 V2.4 - **Kirsten de Hoog, Valentine Charles**

- Inclusion of the recommendations from the DataQuality Committee( Clarifications of the conditions for mandatory elements; Language tags made recommended for most of the properties; New recommendation in dc:language for no-­linguistic content, Additional data quality recommendations for contextual resources)
- Change of value constraints for edm:currentLocation and clarification of the property definition.
- Addition of edm:type in edm:WebResource.
- Change of cardinalities for rdaGr2:professionOrOccupation

2016-11-18 V2.3 - **Kirsten de Hoog, Valentine Charles**

- Several minor edits, including updates of references,layout changes
- All references to Europeana rights statements replaced by statements from <http://rightsstatements.org>
- Differences between mandatory and recommended properties made clearer in the summary table.
- Addition of edm:isReferencedBy to edm:Webresource.
- Addition of edm:intermediateProvider to ore:Aggregation as a recommended property

2012-12-17 V2.2 - **Robina Clayphan**

Changes since v2.1

- Several minor edits from Dan Matei
- Addition of owl:sameAs to WebResource to create a lightbox track.
- Addition of cc:License class and corresponding amendments to WebResource and Aggregation.
- Addition of summary list of properties per class and related adjustments.
- Removal of table of M and R properties
- Rearrangement of place of birth and death to match schema.
- Removal of edm:unstored
- Retained wgs84\_pos: form although schema uses only wgs84:

**Acknowledgements**

This documentation was the result of the combined efforts of Robina Clayphan, Valentine Charles and Antoine Isaac. It was reviewed by Dimitra Atsidis, Francesca Morselli, Marie-­‐Claire Dangerfield, Cecile Devarenne, Kirsten de Hoog and Go Sugimoto who suggested useful improvements. Thanks are extended to Rodolphe Bailly for providing the example MIMO data and giving his assistance, and to the members of the Data Quality Committee for their recommendations. [ 2014-10-31 ]
