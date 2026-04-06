
# Management of organisation entities (for aggregators)

One of the features we offer to Europeana website users is the ability to browse our vast collection through providing organisations. For instance, if you are interested in materials from a specific research center, you can easily access all relevant records from its dedicated page. You can explore the list of contributing organisations sharing their data [here](https://www.europeana.eu/en/collections/organisations).

<details>
<summary>Dedicated page for Naturalis Biodiversity Center</summary>

![Screenshot 2024-06-21 at 13.15.53.png](https://europeana.atlassian.net/wiki/download/attachments/2617442393/Screenshot%202024-06-21%20at%2013.15.53.png?version=5&modificationDate=1718973560496&cacheVersion=1&api=v2)

</details>

Even if you choose not to browse by contributing organisations, you will still learn about them from the individual record pages. We enhance the provided data with Europeana entities for organisations, allowing you to learn about providers when viewing individual records. By clicking on the entity, you can access each organisation's dedicated page with additional information, including its location, website, and other provided records. This additional information is coming from Europeana’s customer relationship management tool, Zoho CRM.

<details>
<summary>Record page for a preserved specimen provided by Naturalis Biodiversity Center</summary>

![Screenshot 2024-06-24 at 10.50.55.png](https://europeana.atlassian.net/wiki/download/attachments/2617442393/Screenshot%202024-06-24%20at%2010.50.55.png?version=3&modificationDate=1719223292793&cacheVersion=1&api=v2)

</details>

<details>
<summary>Screenshot of the Naturalis Biodiversity Center record in Zoho CRM</summary>

![Screenshot 2024-06-21 at 13.53.26.png](https://europeana.atlassian.net/wiki/download/attachments/2617442393/Screenshot%202024-06-21%20at%2013.53.26.png?version=4&modificationDate=1718975874323&cacheVersion=1&api=v2)

</details>

API users can retrieve specific organisation entities by referring to the [Entity API Documentation](../Europeana%20APIs%20Documentation/API%20Suite/Entity%20API%20Documentation.md) that specifies the request format.

<details>
<summary>Example request and response to retrieve metadata available for Naturalis Biodiversity Center</summary>

**Request**

`GET https://api.europeana.eu/entity/organization/4513.json`

**Response**

```java
{
@context: "http://www.europeana.eu/schemas/context/entity.jsonld",
id: "http://data.europeana.eu/organization/4513",
type: "Organization",
prefLabel: {
en: "Naturalis Biodiversity Center"
},
hiddenLabel: [
"Library of the Netherlands Entomological Society, Naturalis Biodiversity Center"
],
description: {
de: "Niederländisches Naturkundemuseum und Forschungsinstitut in Leiden",
ru: "Музей в Голландии",
en: "Natural history museum and research center in the Leiden, The Netherlands",
it: "Museo di storia naturale e centro di ricerca neerlandese",
fr: "Musée et centre de recherche néerlandais",
da: "Naturhistorisk museum og forskningscenter i Nederlandene",
nl: "Museum en onderzoekscentrum in Leiden",
es: "Museo de historia natural y centro de investigación neerlandés"
},
europeanaRole: [
{
id: "http://data.europeana.eu/vocabulary/role/ProvidingInstitution",
type: "Concept"
}
],
country: {
id: "http://data.europeana.eu/place/106",
type: "Place"
},
language: [
"nl"
],
homepage: "https://www.naturalis.nl/",
hasAddress: {
id: "https://crm.zoho.eu/crm/org20085137532/tab/Accounts/486281000000923816#address",
type: "Address",
locality: "Leiden",
countryName: "Netherlands"
},
identifier: [
"486281000000923816"
],
sameAs: [
"https://crm.zoho.eu/crm/org20085137532/tab/Accounts/486281000000923816",
"http://www.wikidata.org/entity/Q641676",
"http://isni.org/isni/000000012159802X",
"http://data.europeana.eu/organization/1482250000000370517",
"http://viaf.org/viaf/132063008",
"http://viaf.org/viaf/305227246",
"http://d-nb.info/gnd/5025979-9",
"http://id.loc.gov/authorities/names/n92025427",
"http://www.idref.fr/157896315/id",
"https://www.freebase.com/m/08jgn7",
"https://g.co/kg/m/08jgn7",
"https://livedata.bibsys.no/authority/90313667",
"http://nlg.okfn.gr/resource/authority/record241821",
"http://dbpedia.org/resource/Naturalis_Biodiversity_Center"
],
isAggregatedBy: {
id: "http://data.europeana.eu/organization/4513#aggregation",
type: "Aggregation",
created: "2024-02-22T17:19:25Z",
modified: "2024-05-23T13:17:13Z",
pageRank: 22,
recordCount: 5200216,
score: 586313,
aggregates: [
"http://data.europeana.eu/organization/4513#aggr_europeana",
"http://data.europeana.eu/organization/4513#aggr_source_1",
"http://data.europeana.eu/organization/4513#aggr_source_2"
]
}
}
```

*Note that the entity includes data from Zoho CRM, enriched with additional information available for this organisation in Wikidata.*

</details>

---

Table of contents:

- [Europeana organisation entities](#europeana-organisation-entities)
- [Enriching data with organisation entities](#enriching-data-with-organisation-entities)
- [Providing information about organisations in EDM](#providing-information-about-organisations-in-edm)

---

# Europeana organisation entities

Over the years, we have created records in Zoho CRM for our existing data partners. These records include information such as the organisation's name in its original language and English translation, website, location, and more. Going forward, we aim to rely on aggregators for gathering information about new data providers. As you are in direct contact with your providers, you can ensure they are represented in Europeana with accurate and up-to-date information. We have included a spreadsheet in the [Jira submission form](https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/72) for new datasets, and we ask you to fill it in for all new providers. This will allow us to import information from the spreadsheet to the Zoho CRM and to create an entity for any new organisation based on the provided details.

The spreadsheet contains two tabs. In the first one, you will find descriptions of the information about providing organisations that we need. The second tab contains columns where we ask you to record the information.

> [!WARNING]
> If you come across any inaccurate or outdated information about organisations while browsing Europeana, please inform us directly by contacting the DPS team or using the feedback feature in the portal. We will promptly update the necessary information in Zoho CRM.
>
> The feedback widget is located in the bottom right corner of your screen when using Europeana.

# Enriching data with organisation entities

During the ingestion process, one of the steps involves semantic enrichment of provided data. As part of this process, a match between provided data and organisation entities is established. You can find more details about the process [here](https://europeana.atlassian.net/wiki/x/AYDeiw).

<details>
<summary>Excerpt from the record enriched with organisation entity</summary>

```java
[...]
<ore:Aggregation rdf:about="/aggregation/provider/Example_01#Aggregation">
        <edm:aggregatedCHO rdf:resource="#Example_01"/>
        <edm:dataProvider rdf:resource="http://data.europeana.eu/organization/4513"/>
        [ other Provider’s Aggregation data ]
 </ore:Aggregation>
[...]
<foaf:Organization rdf:about="http://data.europeana.eu/organization/4513">
        <skos:prefLabel xml:lang="en">Naturalis Biodiversity Center</skos:prefLabel>
        [ other properties of Organisation entity]
</foaf:Organization>
```

*Note the prefLabel from the contextual class is displayed on the record page as clickable entity.*

</details>

# Providing information about organisations in EDM

To ensure successful enrichment, all providers should make sure to supply correct providing organisations in relevant EDM fields:

- [ore:Aggregation](../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/ore_Aggregation.md)
- [ore:Aggregation](../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/ore_Aggregation.md)
- [ore:Aggregation](../EDM%20-%20Mapping%20guidelines/EDM%20Core%20classes/ore_Aggregation.md)

Organisation can either be provided as a literal value or URI:

|  **Datatype**                                                                                                                               |  **Example**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |  **Keep in mind**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|:--------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Literal value** <br/> [Name of providing organisation in its original language or English, <br/> acronyms are also accepted] <br/>  <br/> | `<edm:dataProvider>Naturalis Biodiversity Center</edm:dataProvider>`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | > [!TIP] Ensure that the values provided in the data match those supplied in the spreadsheet. <br/> When submitting multiple datasets from the same organisation, please maintain consistency by using the same names for the same organisations. <br/>                                                                                                                                                                                                                                                                                            |
| **URI** <br/> [Vocabulary URIs and persistent identifiers (PID) for organisations, <br/> as well as Europeana organisation entity URI]      | `<edm:dataProvider rdf:resource="http://data.europeana.eu/organization/4513"/>` <br/> In addition to the Europeana organisation entity, other appropriate URIs include (note this list is not exhaustive): <br/><ul><li><p>Virtual International Authority File (VIAF): <code>http://viaf.org/viaf/[ENTITY_ID]</code></p></li><li><p>The Getty - Union List of Artist Names (ULAN): <code>http://vocab.getty.edu/ulan/[ENTITY_ID]</code> </p></li><li><p>Gemeinsame Normdatei (GND): <code>https://d-nb.info/gnd/[ENTITY_ID]</code></p></li><li><p>International Standard Name Identifier (ISNI): <code>https://isni.org/isni/[ENTITY_ID]</code></p></li><li><p>Archival Resource Key (ARK): <code>https://[Name Mapping Authority]/ark:/[Name Assigning Authority Number]/[assigned Name with optional Qualifiers]</code></p></li><li><p>The Research Organization Registry (ROR): <code>https://ror.org/[ENTITY_ID]</code></p></li><li><p>Wikidata: <code>http://www.wikidata.org/entity/[ENTITY_ID]</code></p></li></ul> | > [!TIP] Ensure you provide the correct URI pattern and notify Europeana by either recording the URI in the SameAs column of the spreadsheet or adding it to the Data Provider field in the Jira submission form. This allows us to record it in Zoho CRM. <br/> Currently, you can only supply a Europeana entity URI for existing data providers. If you wish to do so, you will need to know the Europeana identifier for the organisation, which is the last part of the entity URI: `http://data.europeana.eu/organization/[ENTITY_ID]` <br/> |

> [!TIP]
> **Europeana identifiers for organisations**

<details>
<summary>Finding existing providing organisations</summary>

To search for existing organisations that have already provided data to Europeana, you can use [this tool](https://rnd-2.eanadev.org/share/entities/search.html). Simply focus your search on organisation entities by ticking the "Organisation" option and add keywords in the search bar:

![Screenshot 2024-06-21 at 18.40.05.png](https://europeana.atlassian.net/wiki/download/attachments/2617442393/Screenshot%202024-06-21%20at%2018.40.05.png?version=2&modificationDate=1718991677444&cacheVersion=1&api=v2)

When you click on one of the results, you will be taken to the entity page for this specific organisation on Europeana website: `https://www.europeana.eu/en/collections/organisation/4513-naturalis-biodiversity-center`

The last segment of the URL after "/organisation/" contains the Europeana identifier for this specific organisation. In this case, the identifier is 4513.

When submitting URIs in EDM, follow this pattern: `http://data.europeana.eu/organization/[ENTITY_ID]`

</details>
