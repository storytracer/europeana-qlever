
# Upgrading existing PIDs in the data

To make references to Europeana objects more stable, we have introduced a new [EDM profile](https://europeana.atlassian.net/wiki/x/OgC7ww) that allows cultural heritage institutions (CHIs) and aggregators to supply [persistent identifiers (PIDs)](https://europeana.atlassian.net/wiki/x/AgCowg) in a dedicated `edm:pid` field.

Before introducing the new profile, we have processed all the records in our database to identify the presence of PIDs in the data by looking into properties such as rdf:about of the edm:ProvidedCHO and edm:WebResource, or dc:identifier. We would now like to ask for your help to review our findings and confirm whether they can be used as persistent identifiers in the record, and which part of the record they persistently identify.

> [!NOTE]
> The topic of PIDs in the data space was presented at the Europeana Aggregators Forum (EAF) meeting in October 2025. For those who would like to watch the session, the recording is available on YouTube via [this link](https://www.youtube.com/watch?v=ZG8Aqw5UTVA&t=12030s).

# What does an upgrade of PIDs entail?

Upgrading a PID means retrospectively applying changes to records where we detected PIDs:

- We will normalise the existing PID and create an edm:PersistentIdentifier class with additional properties, such as the canonical version of the PID. More information about the normalisation process is available [here](https://europeana.atlassian.net/wiki/x/GAC7ww).
- Changes will only be applied after we receive confirmation from the aggregator responsible for the dataset. Once you give us permission, there is no need to remap already published datasets, we will handle the updates ourselves.

# What we need from you

## **Step 1: Familiarise yourself with the spreadsheet**

We have prepared a spreadsheet for each aggregator to guide this process. Please start by reviewing the information it contains:

- *Column A*: List of CHIs that provided data containing PIDs through your aggregator.
- *Column B*: Dataset IDs where the PIDs appear for each CHI.
- *Column C*: All PID schemes used by that CHI (e.g. ARKs, DOIs, Handles).
- *Column D*: Europeana.eu record URI that contains an example of a PID. The examples (up to 20 per CHI) were selected to show a variety of schemes from different datasets. This ensures the selection reflects the range of PID schemes and datasets in use by a specific CHI.
- *Column E*: The EDM class where the PID was detected (edm:ProvidedCHO or edm:WebResource).

This spreadsheet will be your main reference for the next steps.

## **Step 2: Contact the responsible CHI**

Since CHIs are best placed to confirm the correct PIDs for their cultural objects or web resources, please share the spreadsheet with them and invite them to review the examples of PIDs they have provided in their data.

If you are confident making the assessment yourself, you may do so on their behalf.

## **Step 3: Review the examples**

Review each example carefully. The review can be done by the CHI, by the aggregator, or jointly, and should cover the following:

- **PID correctly reflects the resource’s level:** The PID must correspond exactly to the specific resource it identifies, not to a broader or narrower one.

*Example: If the provided resource is a specific journal issue, and the PID identifies the entire journal series, that PID should not be upgraded, as it does not correctly identify the resource.*

- **PID is mapped to the correct EDM class:** The PID must be assigned to the appropriate EDM class for the resource it identifies.

*Example:* *If the ProvidedCHO describes a physical painting, the PID identifying the painting should be provided in edm:ProvidedCHO class. If the PID identifies a digital image of the painting, it should instead be mapped to the edm:WebResource.*

## **Step 4: Record your decision**

Record the outcome for each example in the spreadsheet using *columns F* to *I*:

1. Tick the checkbox in *column F* *(or column H for aggregators with PIDs that have issues)* if the PID can be upgraded while remaining in its current EDM class.
2. If the PID can be upgraded but must be remapped, indicate this in *column G* (remapped to edm:ProvidedCHO), *column H* (remapped to edm:WebResource), or columns *I* and *J* for aggregators with PIDs that have issues.
3. If a PID should not be upgraded, for example, because it does not identify the provided resource, tick the checkbox in *column I (or column K for aggregators with PIDs that have issues)*.

# Deadline

Our goal is to complete the upgrade of PIDs by the end of March 2026. To allow time for gathering changes, implementing and running the updates, please complete your reviews by the **end of January** **2026**. If meeting this timeline is not possible, contact us to discuss alternative arrangements.
