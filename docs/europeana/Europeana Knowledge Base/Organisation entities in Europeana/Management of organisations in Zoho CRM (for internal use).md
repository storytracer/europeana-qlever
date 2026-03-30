
[Organisation entities in Europeana](../Organisation%20entities%20in%20Europeana.md)

# Management of organisations in Zoho CRM (for internal use)

DPS team is managing information about organisations that publish data with Europeana in Institutions and Aggregators module in [Zoho CRM](https://crm.zoho.eu). This guide covers three main types of operations: creating records for new organisations (individually or in bulk), updating existing records, and handling duplicate entries.

Each section provides a step-by-step approach to streamline these processes and ensure appropriate data management:

- [1 New record(s) creation process](#key-1-new-record-s-creation-process)
  - [Creating records for new organisations: step-by-step guide](#creating-records-for-new-organisations-step-by-step-guide)
    - [1. Use DPS team account and go to Institutions module](#key-1-use-dps-team-account-and-go-to-institutions-module)
    - [2. Add information about organisation](#key-2-add-information-about-organisation)
    - [3. If organisation is an accredited aggregator, add additional information in Aggregators module](#key-3-if-organisation-is-an-accredited-aggregator-add-additional-information-in-aggregators-module)
  - [Creating records for new organisations in bulk: step-by-step guide](#creating-records-for-new-organisations-in-bulk-step-by-step-guide)
    - [1. Gather information in a spreadsheet and import it in Zoho](#key-1-gather-information-in-a-spreadsheet-and-import-it-in-zoho)
    - [2. Add information from the spreadsheet as new organisations](#key-2-add-information-from-the-spreadsheet-as-new-organisations)
    - [3. Map the fields from the spreadsheet to Zoho fields](#key-3-map-the-fields-from-the-spreadsheet-to-zoho-fields)
- [2 Existing record(s) update process](#key-2-existing-record-s-update-process)
- [3 Merging duplicate records process](#key-3-merging-duplicate-records-process)
  - [Scenario 1: step-by-step guide](#scenario-1-step-by-step-guide)
    - [1. Go to the record you have identified as being a duplicate and deploy Find & Merge Duplicates tool](#key-1-go-to-the-record-you-have-identified-as-being-a-duplicate-and-deploy-find-merge-duplicates-tool)
    - [2. In the “Find and Merge Duplicates” section, enter the matching criteria](#key-2-in-the-find-and-merge-duplicates-section-enter-the-matching-criteria)
    - [3. Select fields to keep in the Master record](#key-3-select-fields-to-keep-in-the-master-record)
  - [Scenario 2: step-by-step guide](#scenario-2-step-by-step-guide)
    - [1. Mark the Deprecated organisation for deletion](#key-1-mark-the-deprecated-organisation-for-deletion)
    - [2. Add organisation ID of the Master record](#key-2-add-organisation-id-of-the-master-record)
    - [3. Merge the duplicates](#key-3-merge-the-duplicates)

# 1 New record(s) creation process

Before processing data, including new dataset submissions or updates with added records, DPS team must record new providing organisation(s) in Zoho. This can be done by either creating individual records directly in Zoho or by using a spreadsheet to import the data. For bulk record creation via spreadsheet, please use the fields in the [provided template](https://docs.google.com/spreadsheets/d/1NSWzlACCzFIUu1xPKFzzLvs9_G852gMWV9MkoJUKaRE/edit?usp=sharing).

> [!NOTE]
> Only entities perceived as organisations are recorded in CRM. This means not all values from the source data have a corresponding organisation entity.
>
> For example, values referring to individuals (e.g. *Peter Sanderson*), city names that do not present formal administrative bodies or government entities (e.g. *City of Subotica, Serbia*), or privately owned collections (e.g. *Private collection*) are not considered organisations.

## Creating records for new organisations: step-by-step guide

> [!WARNING]
> When creating new records, ensure you avoid duplicating existing entries. Instead of solely searching for the full name of the new organisation, perform additional searches using keywords or partial names. This method will help determine if the institution has already been recorded under a different name variation. If you discover that the institution already exists, please remember to update the Institution Owner to the DPS Team.

### 1. Use DPS team account and go to Institutions module

<details>
<summary>Select “Create Institution”</summary>

![Institution_module.png](../../attachments/04d0a581-78cd-48d5-938c-74bd3b8cf997.png)

</details>

### 2. Add information about organisation

> [!IMPORTANT]
> Make sure to follow EDM profile for organisations: for example, if the source data contains both organisation name and the city, e.g. *Gömöri Múzeum - Putnok*, record them separately in *Institution name*/*Alternative* and *City*. Unless the city is part of the official name, e.g. *London City Museum*. The same goes for acronyms, which should also be recorded separately, e.g. *Istituto Centrale per il Catalogo e la Documentazione (ICCD)*: *ICCD* should be recorded in the *Acronym* field.
>
> The **mandatory properties** are marked in **dark blue.**
>
> The **recommended properties** are marked in **dark red.**
>
> The **optional properties** are left in **black**.

<details>
<summary>List of available fields and their definitions</summary>

|                                                                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|:---------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *Institution Information*                                                  |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Institution Name & Lang Institution Name**                               | English translation of the organisation’s name, along with the corresponding language tag (preferably in English). It should be populated alongside the “Alternative Institution Names” fields, where the organisation’s name in its native language is recorded. <br/> Exceptions: <br/><ul><li><p>If the organisation explicitly prefers to be referred to only by its native language and does not wish to use an English name, the native language name must be recorded in this field. </p></li><li><p>If the native name is not in one of the <a class="external-link" href="https://docs.google.com/spreadsheets/d/1f9mNrmL8DNwKGXEQLsdu6SLLrDBQ7Gy6ko_kIaJLLwg/edit#gid=0" rel="nofollow">Europeana-supported languages</a>, an English translation of the name is mandatory. This is because labels in unsupported languages (e.g. Serbian, Icelandic, Latin) are filtered out and not included in the entity.</p></li></ul> |
| Acronym & Lang Acronym                                                     | Acronym of organisation in English or native language & corresponding language tag.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Sector**                                                                 | Area in which organisation operates (select the most appropriate option from the drop-down menu).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Subsector**                                                              | Sub-area type organisation falls under (select the most appropriate option from the drop-down menu).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Subsector other**                                                        | *Sub-area type organisation falls under (free-text field: use it only in case none of the options from the drop-down menu apply).*                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Website**                                                                | Official website of organisation (should always start with protocol http or https).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Official Language**                                                      | Language of the organisation’s native name.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| *Participation level*                                                      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Is aggregated via**                                                      | If the organisation is not an aggregator, select the accredited aggregator from the drop-down menu through which it provides data. You can select multiple aggregators as needed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| *Address Information*                                                      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Street                                                                     | <br/> *Physical address of organisation*                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Country**                                                                |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ZIP code                                                                   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| City                                                                       |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| *Alternative Institution Names*                                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Alternative 1, 2, 3, 4, 5 & Lang Alternative 1, 2, 3, 4, 5**             | The official name of the organisation if an English translation is provided in the "Institution Name" field. Includes the corresponding language tag, not in English. If you provided a non-English name in "Institution Name," leave this field empty.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Alternative Acronym 1 & Lang Acronym 1                                     | Acronym of the organisation in a language different from the one recorded in the Acronym field & corresponding language tag.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| *Hidden names of the institution*                                          |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Hidden names                                                               | Unofficial names of organisations from the source data that will not be displayed but will be used for matching                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Coreferences**                                                           |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| SameAs 1, 2, 3, 4                                                          | Another URI of the same organisation (e.g. wikidata URI: “[http://www.wikidata.org/entity/{entityID}”](#http-www-wikidata-org-entity-entityid)) <br/> URI can be an entity from LD vocabulary or a persistent identifier for organisation. If recorded URI is an entity from a vocabulary Europeana is dereferencing, it must follow the pattern that is [dereferenceable by Europeana](https://docs.google.com/spreadsheets/d/1BoDNolkcp_qfvVShdOZyGcf61XslcwKF2MdGcjgYs20/edit#gid=0).                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| *DEA (used for recording details about Europeana Data Exchange Agreement)* |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

</details>

### 3. If organisation is an accredited aggregator, add additional information in Aggregators module

Additional information about accredited aggregators is stored in the Aggregators module. Each accredited aggregator is first added to the Institutions module, after which a new record is created in the Aggregators module and linked to the corresponding Institution record via the “Corresponding Institution” field.

> [!IMPORTANT]
> The **mandatory properties** are marked in **dark blue.**
>
> The **recommended properties** are marked in **dark red.**
>
> The **optional properties** are left in **black**.

<details>
<summary>List of available fields and their definitions</summary>

|                               |                                                                                                                                                                             |
|:------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *Aggregator Information*      |                                                                                                                                                                             |
| **Aggregator Name**           | The official name of the aggregator that must always match the name of the corresponding institution.                                                                       |
| **Corresponding Institution** | This is a lookup field that links the records for the same organisation in both the Aggregators and Institutions modules.                                                   |
| **Geographic scope**          | Geographic area in which organisation operates (select the most appropriate option from the drop-down menu).                                                                |
| **Heritage domain**           | Sub-domains of the materials aggregated by the organisations (select the most appropriate option from the drop-down menu).                                                  |
| **Public email**              | Email address for audiences to contact the organisation.                                                                                                                    |
| *Support data provider with*  |                                                                                                                                                                             |
| Capacity Building             | Types of capacity building activities provided by the aggregator (select the most appropriate option from the drop-down menu).                                              |
| Media Type                    | Additional support provided by the aggregator for this specific media type, beyond it being merely aggregated (select the most appropriate option from the drop-down menu). |
| Data Activity                 | Data-related activities carried out by aggregators (select the most appropriate option from the drop-down menu).                                                            |
| Audience Engagement Activity  | Initiatives to connect with and involve audiences (select the most appropriate option from the drop-down menu).                                                             |

</details>

Do not forget to save the record when you are done!

## Creating records for new organisations in bulk: step-by-step guide

DPS team account has sufficient permissions to perform batch import of new organisations in Zoho, as well as batch update of existing organisations (in this case, the spreadsheet with data must contain Zoho ID of organisation).

### 1. Gather information in a spreadsheet and import it in Zoho

Convert the spreadsheet to a .csv file. Go to “Create Institution” drop-down menu in the Institutions module and select “Import Institutions”.

<details>
<summary>Import institutions</summary>

![](../../attachments/b58b3b74-e7fb-4f73-959b-a9e3f272e3c9.png)

Then select “From File” option:

![](../../attachments/d11297cc-ca31-493f-88d6-d8e8ad308f3d.png)

Upload .csv file and click Next:

![](../../attachments/d71af37f-a0ff-4033-b458-57584fbe4dc6.png)

</details>

### 2. Add information from the spreadsheet as new organisations

Zoho will ask what you wish to do with the records in the file and will offer three different options:

1. **Add as new institutions:** if you are importing information about new organisations that do not yet exist in Zoho, select this option.

From the drop-down menu for “Skip existing institutions based on” select “Institution Name”. This will create new records and cross-reference records from the spreadsheet with the rest of the organisations in Zoho based on the Institution Name values. Depending on the data in the spreadsheet, you may choose any other option that suits your needs (e.g. select the website option if all organisations in the spreadsheet have a website). If duplicate records in Zoho are found, duplicates from the spreadsheet will not be imported. You will learn about these duplicate records from the final report (see Skipped records tab).

<details>
<summary>Select "Institution name" in the drop-down menu</summary>

![](../../attachments/236e6207-668a-4f36-9e4b-31afcc5fdb11.png)

</details>

2. **Update existing institutions only:** to update existing records in Zoho, select this option.

Choose “Institution  Id” from the drop-down menu under “Find existing institutions based on”. This means new data from the spreadsheet will override already existing Zoho data for the specific organisation based on the Institution ID match. Note that your import spreadsheet has to contain a column with Institution IDs. Take time to understand the data you intend to overwrite and determine whether “Don’t update empty values for existing institutions” should be ticked or not (select “?” to understand the consequences).

<details>
<summary>Choose "Institution ID" from the drop-down menu</summary>

![](../../attachments/19c2f77c-39de-47d2-9204-55c34e907aca.png)

</details>

3. **Both:** opting for this choice will result in duplicate records in Zoho being updated with information from the spreadsheet (refer to the “Updated records” tab in the final report). **This option is not recommended,** as you could overwrite existing information in Zoho that is still relevant.

### 3. Map the fields from the spreadsheet to Zoho fields

Map the columns from the spreadsheet to the corresponding Zoho fields. If column titles are using the names of Zoho fields, you can try “Apply Auto Mapping”. Once you are satisfied with how the information from the spreadsheet is mapped to Zoho fields, proceed by clicking Next.

<details>
<summary>Mapping tool in Zoho</summary>

![](../../attachments/64769d77-83e5-4729-ae15-1fe951c2ba74.png)

Tick “Assign owner based on assignment rules” and select “DPS Ownership assignment” which was pre-set and will set Institution owner of all newly created Zoho records as DPS Team. Also tick “Trigger configured automations and processes for new and updated records” which will apply pre-set rules for checking duplicates and mandatory fields.

![](../../attachments/5602f73d-5e6e-4922-88b0-56df42a1f806.png)

</details>

It will take a few minutes before the import is finished. When it is finished, you will receive a pop-up message at the right-bottom corner.

<details>
<summary>Import status report pop-up message</summary>

![](../../attachments/a18b9489-bdf5-48ce-8390-5a6eb29d39ed.png)

</details>

Access the report by clicking on the link in the pop-up message. Have a good look to decide if you are happy with the result. If not, you can still undo changes by selecting “Undo this import” at the bottom left corner.

<details>
<summary>Import status report</summary>

In this case, Zoho correctly recognised that spreadsheet contained two organisations for which we already have records in Zoho and it did not create duplicates. It only imported the two remaining organisations. To see more information about Skipped records, download the list of records with errors, which will provide more information about errors. In my case, the error is “*Duplicate records exist in system. - Institution Name (ideally in English, or in original language if no English translation is available).*”

![](../../attachments/bbe0db19-9c00-477e-a039-5d3f2932891f.png)

</details>

Once the import is finished, Zoho will send report to [content@europeana.eu](mailto:content@europeana.eu). Alternatively, you can go to the Import History in zoho to review the completed actions. You can undo the import by selecting “Undo Import”.

<details>
<summary>Undo import</summary>

![](../../attachments/291308d8-1fc4-4458-889c-262920557bf8.png)

</details>

# 2 Existing record(s) update process

During enrichment, we match organisations from the source data with the corresponding organisation entities (find more information about matching rules [here](https://europeana.atlassian.net/wiki/x/AYDeiw)). Europeana Entity API has integration with Zoho and collects information about new, updated or deleted records from Institutions module that have *Institution Owner* set to DPS Team. Organisation entities are updated with new information from Zoho daily.

When reprocessing existing datasets, it is good practice to look at the source data (i.e. values mapped to metadata fields for capturing information about providing organisations: *edm:dataProvider*, *edm:Provider*, *edm:intermediateProvider*), and cross-check it with the corresponding records in Zoho. Values from the source data will only be enriched with the organisation entity when source data matches the Zoho labels (see [Management of organisations in Zoho CRM (for internal use)](Management%20of%20organisations%20in%20Zoho%20CRM%20(for%20internal%20use).md) for more details).

If the existing Zoho labels do not match the source data, update Zoho record accordingly, but be careful not to overwrite any of the labels that are used for matching during enrichment.

In many cases, we have more than one dataset by the same provider and datasets may contain different name variations for the same provider. Because we do not retain original providers' values in EDM Internal, it is challenging to trace which labels are used for matching. If you are not certain which labels are safe to overwrite, you can use *Hidden names* field to add a new name variation there. If you think that the name of organisation we currently store is incorrect, move it to *Hidden names* and update *Institution Name*, or one of *Alternative Name* fields with the correct name version.

# 3 Merging duplicate records process

> [!IMPORTANT]
> You might encounter duplicate Zoho records for the same organisation. If you discover any, you might be able to merge them, depending on whether all **duplicates have items associated with them, or not**:
>
> - If only one of the Zoho duplicates has items associated with it, you can merge them following the steps outlined in **Scenario 1: A step-by-step guide.**
> - If all Zoho duplicates have items associated with them, they cannot be merged immediately, so follow the steps outlined in **Scenario 2: A step-by-step guide**.

<details>
<summary>Checking how many items are associated with the organisation entity:</summary>

To analyse how many items are associated with a specific Zoho record, use this API query that lists IDs of all Europeana records (if any) associated with the specific organisation:

```java
https://api.europeana.eu/api/v2/search.json?query=foaf_organization:"http://data.europeana.eu/organization/[OrgID]"&facet=europeana_id&profile=facets&rows=0&wskey=api2demo
```

> [!IMPORTANT]
> OrgID is recorded in the *Europeana org. ID* field. Please note that new IDs were introduced when we switched from Zoho US to Zoho EU. Records processed before this migration will contain old OrgIDs, which are recorded in the *Zoho old ID* field. It is recommended to do two searches: one with the old OrgID and one with the new OrgID.

</details>

## Scenario 1: step-by-step guide

When only one of the Zoho duplicates has items associated with it, use ***Find & Merge Duplicates*** tool that allows you to fetch all duplicated records and merge them into one Master record (this should be the record that has items associated with it). You can merge a maximum of three records at a time.

### 1. Go to the record you have identified as being a duplicate and deploy Find & Merge Duplicates tool

<details>
<summary>Screen capture of this step</summary>

![FindingDuplicates.png](../../attachments/eb3bcaa0-f0e6-4501-a84e-a41054f21f79.png)

</details>

### 2. In the “Find and Merge Duplicates” section, enter the matching criteria

Specify the matching criteria for finding all duplicates in the *Search Criteria* section (you can remove criteria by selecting red *minus* sign, or add criteria by selecting green *plus*). Then click *Search* to fetch the list of duplicates that match the search criteria.

<details>
<summary>Screen capture of this step</summary>

![SearchCriteria.png](../../attachments/8b5c340e-3e35-4e1f-a94d-a84497935f43.png)

</details>

Once the list of duplicate records has been displayed, select the records from the list you wish to merge and click Next.

<details>
<summary>Screen capture of this step</summary>

![clickNext.png](../../attachments/af418895-c717-49e7-af83-ea64fd6f7739.png)

</details>

### 3. Select fields to keep in the Master record

On the Deduplicate Institutions page select the record that you wish to keep as a Master record and select all those field values that you wish to keep. The selected values will appear under Master record column. Click Merge when you are done.

<details>
<summary>Screen capture of this step</summary>

![DeduplicateInstitutions.png](../../attachments/9413c2b5-4c51-47ca-97fa-ea026a4ad094.png)

</details>

## Scenario 2: step-by-step guide

When all Zoho records have items associated with them, choose one of the duplicates as a (future) Master record.

### 1. Mark the Deprecated organisation for deletion

On the record page of the other (deprecated) organisation tick Scheduled for deletion so that the record will no longer be used for enrichment.

<details>
<summary>Screen capture of this step</summary>

![Screenshot 2024-10-02 at 13.11.39.png](../../attachments/e51ffa66-fdc7-4de3-bcc5-794e13ef067c.png)

</details>

### **2. Add organisation ID of the Master record**

To make sure deprecated organisation redirects to the Master record, add the OrgID (recorded in the Europeana org. ID field) of the chosen Master record in one of the SameAs fields.

> [!IMPORTANT]
> The URI has to follow the pattern: “[http://data.europeana.eu/organization/{identifier}”](#http-data-europeana-eu-organization-identifier)

<details>
<summary>Screen capture of this step</summary>

![Screenshot 2024-10-02 at 13.07.35.png](../../attachments/4221f486-ca59-4513-98f1-8b016f1ab673.png)

</details>

### **3. Merge the duplicates**

Once no items are associated with the deprecated organisation, duplicates can be merged following the Scenario 1
