
[Semantic enrichments](../Semantic%20enrichments.md)

# Workflow for supporting new vocabularies

Controlled vocabularies are powerful tools to consistently describe and categorise  things primarily to enhance access to cultural heritage collections by standardising the representation of concepts. To make use of their benefits,  Europeana supports vocabularies used by data providers that meet criteria defined by the Europeana Tech Task Force. When providers include URIs of supported vocabularies in their data, Europeana retrieves their information directly from the source through mappings between the vocabulary’s data model and the contextual classes of the Europeana Data Model (EDM). This process, known as dereferencing, enriches the records with contextual information obtained from the vocabularies.

> [!IMPORTANT]
> You can find the full list of supported vocabularies in this [spreadsheet](https://docs.google.com/spreadsheets/d/1BoDNolkcp_qfvVShdOZyGcf61XslcwKF2MdGcjgYs20/edit?usp=sharing).
>
> If you use a vocabulary that is not yet supported, follow the steps below to request its inclusion.

## Step 1

> [!TIP]
> Data provider fills out the request form: <https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/96>

## Step 2

Metadata coordinator reviews the vocabulary based on the information provided in the request form.

This information follows the recommendations outlined by the Europeana Tech Task Force on Enrichment and Evaluation (see [chapter 2.4. about selecting targets for semantic enrichment](https://pro.europeana.eu/files/Europeana_Professional/EuropeanaTech/EuropeanaTech_taskforces/Enrichment_Evaluation/EvaluationEnrichment_SelectingDatasets_102015.pdf)), namely:

> [!TIP]
> - Vocabulary must [How to confirm if your vocabulary supports content negotiation?](How%20to%20confirm%20if%20your%20vocabulary%20supports%20content%20negotiation_.md) to RDF/XML
> - It must be openly licensed (CC BY, or CC BY-SA by exception) or dedicated to the public domain
> - It has to follow the recommendations for structure and representation of values and languages described in 2.4.4. sub-section about quality
> - High level of semantic relationships, especially incoming and outgoing links with other vocabularies like, for example, Wikidata is a crucial criteria. Equivalence can be expressed using, for example, owl:sameAs or skos:exactMatch.
> - Priority is given to vocabularies with multilingual coverage of metadata as they improve language accessibility of information published in Europeana

## Step 3

After the initial review, Europeana Operations team is consulted.

Europeana reserves the right to turn down the request if the vocabulary is not fulfilling the specified criteria and is not suitable for Europeana dereferencing efforts. Data provider is informed about the decision and reasoning behind it.

## Step 4

If vocabulary is fulfilling the criteria, metadata coordinator checks which RDF/XML data profile the vocabulary content negotiates to - we make a request to URI with the Accept header “application/rdf+xml” - and creates a crosswalk between the format and EDM. It is possible that the vocabulary supports more than one data profile (preferably, vocabulary is based on standard data models, like, for example, SKOS). [Library of Congress Subject Headings (LCSH)](https://id.loc.gov/authorities/subjects.html), for example, supports [SKOS](https://id.loc.gov/authorities/subjects/sh85085171.skos.xml) as well as [MADS](https://id.loc.gov/authorities/subjects/sh85085171.madsrdf.xml), as is evident from [this response](https://id.loc.gov/authorities/subjects/sh85085171.rdf.xml). It is under the discretion of the Metadata Coordinator to select the data format that is most suitable for transformation.

## Step 5

Metadata coordinator creates the contextual mapping (i.e. crosswalk) that focuses on overlaps between selected data profile and EDM contextual class. This can be done in partnership with the data provider who submitted the request.

## Step 6

Metadata coordinator uses the contextual mapping as a general guidance for creating XSL stylesheet with a template for transforming vocabulary to EDM.

Data providers should note that some fields in vocabulary might not have an equivalent in EDM, and vice versa. In addition, there might be fields Europeana will omit from EDM output if, for example, they contain duplicated or information that is redundant in the light of Europeana’s wider enrichment goals. Such fields might be:

- Narrower relationships defined by skos:narrower and skos:narrowMatch
- Concept scheme information defined by skos:inScheme

If language coverage of the vocabulary goes beyond the languages supported by Europeana, the XSL stylesheet will leave out any unsupported values.

## Step 7

The Manager of Aggregation Systems team adds the XSL stylesheet to Metis and publishes it on [GitHub](https://github.com/europeana/metis-vocabularies/tree/develop/src/main/resources/vocabularies). All supported vocabularies are also listed in [this spreadsheet](https://docs.google.com/spreadsheets/d/1BoDNolkcp_qfvVShdOZyGcf61XslcwKF2MdGcjgYs20/edit?usp=sharing).

## Example - Dereferencing of LCSH vocabulary

Because LCSH vocabulary is in line with Europeana’s criteria for supported vocabularies, [contextual mapping](https://docs.google.com/spreadsheets/d/1tqa_lfE6fSYjCj2oqauOsDObh3qnmnUqX9Dm90_H2Fw/edit#gid=0) between [SKOS](https://id.loc.gov/authorities/subjects/sh85085171.skos.xml) and EDM contextual class skos:Concept was created.

Based on the crosswalk, [XSL stylesheet](https://github.com/europeana/metis-vocabularies/blob/develop/src/main/resources/vocabularies/concept/lcsh.xsl) was written and it is now used for LCSH dereferencing.

For example, when you run the XSLT process on [this record](https://id.loc.gov/authorities/subjects/sh85085171.rdf.xml) this is the output:

```java
<?xml version="1.0" encoding="UTF-8"?>
<skos:Concept xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
              xmlns:skos="http://www.w3.org/2004/02/skos/core#"
              xmlns:skosxl="http://www.w3.org/2008/05/skos-xl#"
              rdf:about="http://id.loc.gov/authorities/subjects/sh85085171">
   <skos:prefLabel xml:lang="en">Military ceremonies, honors, and salutes</skos:prefLabel>
   <skos:altLabel xml:lang="en">Military courtesy</skos:altLabel>
   <skos:altLabel xml:lang="en">Military honors</skos:altLabel>
   <skos:altLabel xml:lang="en">Military salutes</skos:altLabel>
   <skos:altLabel xml:lang="en">Salutes, Military</skos:altLabel>
   <skos:broader rdf:resource="http://id.loc.gov/authorities/subjects/sh85045446"/>
   <skos:narrower rdf:resource="http://id.loc.gov/authorities/subjects/sh85090372"/>
   <skos:narrower rdf:resource="http://id.loc.gov/authorities/subjects/sh2012001521"/>
   <skos:narrower rdf:resource="http://id.loc.gov/authorities/subjects/sh2003009031"/>
   <skos:narrower rdf:resource="http://id.loc.gov/authorities/subjects/sh85145907"/>
   <skos:narrower rdf:resource="http://id.loc.gov/authorities/subjects/sh85085200"/>
   <skos:narrower rdf:resource="http://id.loc.gov/authorities/subjects/sh2018002201"/>
   <skos:closeMatch rdf:resource="http://id.worldcat.org/fast/1021060"/>
   <skos:closeMatch rdf:resource="http://data.bnf.fr/ark:/12148/cb12129082c"/>
   <skos:closeMatch rdf:resource="http://data.bnf.fr/ark:/12148/cb12129082c"/>
   <skos:closeMatch rdf:resource="http://id.worldcat.org/fast/1021060"/>
   <skos:inScheme rdf:resource="http://id.loc.gov/authorities/subjects"/>
</skos:Concept>

```

> [!NOTE]
> You need to specify **$targetId parameter in <xsl:if> element of XSL stylesheet** like so:
>
> `<xsl:if test="@rdf:about='http://id.loc.gov/authorities/subjects/sh85085171'">`

Once XSL stylesheet is added to Metis, the following happens during Enrichment step:

*Metis finds dereferenceable URI in the data:*

```java
<ore:Proxy rdf:about="/proxy/provider/14/UEDIN_214">

  <dc:subject rdf:resource="http://id.loc.gov/authorities/subjects/sh85085171"/>

  [ OTHER PROVIDER PROXY DATA ]

</ore:Proxy>
```

*Using XSL stylesheet Metis converts entity to EDM structure and adds it to the record. The link now resolves within the record:*

```java
<ore:Proxy rdf:about="/proxy/provider/14/UEDIN_214">
   <dc:subject rdf:resource="http://id.loc.gov/authorities/subjects/sh85085171"/>

  [ OTHER PROVIDER PROXY DATA ]

</ore:Proxy>


<skos:Concept rdf:about="http://id.loc.gov/authorities/subjects/sh85085171">
   <skos:prefLabel xml:lang="en">Military ceremonies, honors, and salutes</skos:prefLabel>
   <skos:altLabel xml:lang="en">Military courtesy</skos:altLabel>
   <skos:altLabel xml:lang="en">Military honors</skos:altLabel>
   <skos:altLabel xml:lang="en">Military salutes</skos:altLabel>
   <skos:altLabel xml:lang="en">Salutes, Military</skos:altLabel>
   <skos:broader rdf:resource="http://id.loc.gov/authorities/subjects/sh85045446"/>

  [ OTHER PROPERTIES OF CONTEXTUAL OBJECT ]

</skos:Concept>
```

> [!NOTE]
> **This process only happens if the data provider did NOT create a contextual class for dereferenceable URI.**
>
> This is because Europeana does not overwrite any conceptual classes during the Enrichment step in Metis. They are retained even if the source data is poor.
