---
tags:
  - '#temporal-medatada'
  - '#edm'
---

[EDM - Mapping guidelines](../EDM%20-%20Mapping%20guidelines.md)

# Recommendations for providing temporal metadata

- [Scope of this documentation](#scope-of-this-documentation)
- [Date normalisation at Europeana](#date-normalisation-at-europeana)
  - [Normalisation goal](#normalisation-goal)
  - [Normalisation process](#normalisation-process)
  - [EDM properties normalised](#edm-properties-normalised)
- [Recommendations for providing dates](#recommendations-for-providing-dates)
  - [Formatting and conformance with standards](#formatting-and-conformance-with-standards)
  - [Other relevant recommendations](#other-relevant-recommendations)
- [Appendices](#appendices)
  - [Date patterns that can be normalised by Europeana](#date-patterns-that-can-be-normalised-by-europeana)
  - [Time periods in the Europeana Archaeology project](#time-periods-in-the-europeana-archaeology-project)
  - [Processing of timespans and concepts](#processing-of-timespans-and-concepts)
- [Credits and edit history](#credits-and-edit-history)

## Scope of this documentation

Dates are notoriously heterogenous in many types of resource cataloguing. Differences can arise, for example, where systems changed, or standards were either absent (i.e. free text fields were used for date entry) or changed over time, or even where responsible staff members left and new ones joined. In some cases where institutions use the same systems and standards, several dates can still be found associated with a particular item, which when aggregating data to a different source can result in some noise in the data and be unhelpful from a discovery perspective. Moreover, the process of aggregation can itself introduce issues when transforming data from one model into another that has fewer fields, or less specific fields for date values.

This section provides information on how dates are normalised by Europeana and includes recommendations for providers to submit (especially, format) dates so that they can work well with the data processing.

The recommendations also address the case of some date-related problems like lack of specificity in metadata elements used (cf the [DQC problem pattern](https://pro.europeana.eu/project/data-quality-committee#problem-patterns) "Generic property is used while there is a more specific appropriate one"), the impossibility to assign an exact date of creation or use of an item, or changes of calendars.

## Date normalisation at Europeana

### Normalisation goal

The Europeana Data Quality Committee has adopted the Extended Date/Time Format ([EDTF](https://www.loc.gov/standards/datetime/)) as the optimal standard for the representation of dates in Europeana. Europeana has set up a normalisation process that aims to convert as many original dates as possible to this format, so that they can be exploited by downstream processes (for example for including dates and time ranges to the search filter options).

> [!NOTE]
> Note: This process is different from the automatic generation of the edm:year field, which is a mere extraction and simplification of (4-digit) years that can be found in metadata for the purpose of advanced searches.

### Normalisation process

The normalisation process first checks if a provided date is valid against the EDTF or [ISO8601](https://en.wikipedia.org/wiki/ISO_8601) standards. EDTF is supported with level 1 compliance (consult the [EDTF Specification](https://www.loc.gov/standards/datetime/) for details), and ISO8601 is supported only in the “extended format”, which requires the use of the separator between the date components. The ISO8601 “basic format”, which omits separators (e.g. 20050924T100000), is not supported. If a date is not a valid EDTF or ISO8601 date, the process seeks to recognize patterns in the provided date values [cf appendix “[Date patterns that can be normalised by Europeana](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2603417619#Date-patterns-that-can-be-normalised-by-Europeana)”]

Normalised dates are attached to the equivalent element in the Europeana proxy in the EDM record for the object (while the original values remain on the provider proxy).  Proxies in EDM are meant to represent metadata on an object, from the perspective of a specific data provider (a CHI, an aggregator, Europeana Foundation). For more detail please see the EDM Primer at <https://pro.europeana.eu/page/edm-documentation> . A visual explanation can also be found at <https://pro.europeana.eu/page/linked-open-data#data-structure> .

The normalised value is then stored in an instance of the contextual class edm:TimeSpan whose label is the date represented in EDTF. Both the original value in the provider proxy and the EDTF conforming label resulting from the normalisation process are displayed in the front end. Furthermore, links to Europeana entities for time spans (centuries), that result from enrichment processes, can show up as temporal metadata in the front end.

Two examples of the result of the normalisation process are shown below:

**Example 1 - Original value**

```java
<dcterms:created>January, 1765</dcterms:created>
```

**Example 1 - Normalised value**

```java
<dcterms:created rdf:resource="#1765-01"/>
[...]
<edm:TimeSpan rdf:about="#1765-01">
  <skos:prefLabel xml:lang="zxx">1765-01<skos:prefLabel>
  <skos:notation rdf:datatype="http://id.loc.gov/datatypes/edtf/EDTF-level1">1765-01</skos:notation>
  <dcterms:isPartOf rdf:resource="http://data.europeana.eu/timespan/18">
  <edm:begin>1765-01-01</edm:begin>
  <edm:end>1765-01-31</edm:end>
</edm:TimeSpan>
```

**Example 2 - Original value**

```java
<dcterms:created>13th century</dcterms:created>
```

**Example 2 - Normalised value**

```java
<dcterms:created rdf:resource="#12XX"/>
[...]
<edm:TimeSpan rdf:about="#12XX">
  <skos:prefLabel xml:lang="zxx">12XX<skos:prefLabel>
  <skos:notation rdf:datatype="http://id.loc.gov/datatypes/edtf/EDTF-level1">12XX</skos:notation>
  <dcterms:isPartOf rdf:resource="http://data.europeana.eu/timespan/13">
  <edm:begin>1201-01-01</edm:begin>
  <edm:end>1300-12-31</edm:end>
</edm:TimeSpan>
```

> [!NOTE]
> Note: The zxx language tag reflects that the values of skos:prefLabel are meant to conform to a non-linguistic norm (here, EDTF), with possible values like 12XX (for the 13th century).

### EDM properties normalised

The date properties that are subject of normalisation are the following:

- [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md)
- [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md)
- [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md)
- [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md)

In addition to these date properties, there are the following generic properties that are subject of normalisation:

- [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md)
- [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md)

> [!NOTE]
> Note: the above two generic properties are normalised only with highly reliable methods to minimise the risk of matching non-date values with the date patterns [cf appendix “[Date patterns that can be normalised by Europeana](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2603417619#Date-patterns-that-can-be-normalised-by-Europeana)” and recommendations on generic fields]. The current date normalisation does not process properties from any contextual entity (edm:TimeSpan, edm:Agent) that the provider would have contributed. It only considers properties of the provided CHO from the provider ore:Proxy.

## Recommendations for providing dates

### Formatting and conformance with standards

Of course, temporal metadata would ideally be provided in EDTF/ISO8601, but if data providers use one of the patterns that are recognized in the normalisation process (cf appendix below “[Date patterns that can be normalised by Europeana](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2603417619#Date-patterns-that-can-be-normalised-by-Europeana)”), these data will be processed.

Note that we expect dates formatted according to a certain standard to be fully conformant with it. For example, many date values using DCMI Period in the Europeana data include a period name but omit ‘name=’, for example ‘Fayum Neolithic Period; start=-5300; end=-4000’ instead of ‘name=Fayum Neolithic Period; start=-5300; end=-4000’. Such values are not conformant with the DCMI Period specification and therefore will not be normalised.

> [!WARNING]
> **Keep in mind that normalisation is flexible but has limits**

Europeana's normalisation process handles many cases of dates, be they expressed in cardinal form, e.g., "1800-01-01" or in ordinal form, e.g., "18th century", or using BC/AD qualifiers. But it is not able to handle every possible variation, especially across languages.

Examples include cardinal forms like "1st of January 1800" and some BC/AD patterns that are ambiguous across languages.  For example, in the USA, dates are typically represented with the month first while most European countries represent the month in the middle. Also, the "eKr" abbreviation can refer to "BC" in Estonian and Finish (<https://en.wiktionary.org/wiki/eKr.>) and to "AD" in Danish and Norwegian (<https://en.wiktionary.org/wiki/e.Kr.>).

"Annotations" on dates, indicating for example a type of object lifecycle event, are also hard to process.

For example "ca. 1673 (Herstellung)" would require two steps: one for the annotation and one for 'ca.' Such annotations have benefits in terms of information communicated to website users who have found the item, especially when the class Event in EDM is still not yet implemented. But they make it more difficult to find it in the first place, as they are less machine-readable.

In the future, reporting about cases of failed normalisation could be included in the process of publishing metadata in Europeana or in a later step. In the meantime, providers who use specific formatting for dates should be cautious in what they assume for the normalisation process!

### Other relevant recommendations

> [!IMPORTANT]
> **Make sure to always use most specific metadata element applicable.**

In EDM there are several properties that can be used for expressing dates of different events in the life of the provided cultural heritage object. Between [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md) and the more specialised [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md), [edm:ProvidedCHO](EDM%20Core%20classes/edm_ProvidedCHO.md), always choose the most appropriate one. We know it is not always possible, but it is a pity to miss opportunities when existing information would lead to better (re-)user experience. [cf appendix “Use of specialised properties in the ARMA project”]

> [!IMPORTANT]
> **Try to avoid duplication**

We have noticed that when providers map their dates to EDM they tend to provide the same date twice, both as a (numeric or) literal value and as a reference to an instance of the TimeSpan class. This should not happen as it may create redundancy which can result in a cluttered interface and a confusing user experience. Especially now that Europeana is able to normalise many of the provided dates and enrich them with additional information appended in a TimeSpan class, providers should be extra careful and try not to repeat information! Note that this works best if the TimeSpan is provided with a human-readable skos:prefLabel (as recommended in the EDM Mapping Guidelines) that can be picked up by display routines.

> [!IMPORTANT]
> **Be aware of calendar issues**

The normalisation process handles BC/AD dates. But these assume a calendar reference!

In EDTF and Europeana’s normalisation, only the Gregorian calendar is assumed and supported, so be careful that this will not cause some misinterpretations of dates. The transition from the Julian to the Gregorian calendars is expected to raise complications. It is unlikely that many metadata specialists undertake a specific conversion to ensure that their Julian dates, should they be known, can be exactly expressed in the Gregorian calendar. This means that timelines may often be (slightly) inaccurate or vary from institution to institution. This should not be a reason to not provide this information, however!

> [!IMPORTANT]
> **Choose the right class for your temporal metadata**

There are cases of temporal information about a cultural heritage object that actually don’t relate to the object (the edm:ProvidedCHO) itself, but for example to its digital representation. This information can be misleading for search and retrieval functionalities and date normalisation cannot fix this issue, as it is not rooted in the date formatting but the semantics. As explained in the [One-to-One Principle](https://www.dublincore.org/resources/glossary/one-to-one_principle/), “conceptually distinct entities, such as a painting and a digital image of the painting, should be described by conceptually distinct descriptions.” This means that a record describing a painting should, for example, not include metadata about the date of the creation of the record, the digitisation process or about the file that resulted from it. Thus, our recommendation is to be careful when choosing the class for providing temporal information (e.g. date of creation of of a digitisation file should be added to dcterms:created in the corresponding edm:WebResource) and to avoid including dates that have no dedicated class (e.g. the date of catalogue record creation).

> [!IMPORTANT]
> **Judge if a period should be expressed as timespan or concept**

For many cultural heritage objects the metadata includes no concise dates or even dates, especially for older objects.

When recording the metadata giving a figure in numbers may be omitted because the exact date is not of primary concern, mostly because the time spans are conceptual ("Roman period") or broadly defined ("first half of first century AD"). Some of these time periods can be linked to dates that vary depending on the point of view of the person attributing the period to an object, or the beginning and end of periods can differ between countries/regions and depend on a region’s individual history (“Medieval period”).

This is fully acceptable, of course. Yet to add precision to the metadata, providers may sometimes still be able to express dates with edm:TimeSpans with approximate or partial date ranges (that can be normalised -  at the moment normalisation of provided timespans is not yet implemented) in order to allow for exploitation of the temporal information on Europeana (e.g. filtering options). In other cases, periods may be instead expressed as (skos:)Concept, either with specific vocabularies like the Greek Historical Periods from [Semantics.gr](http://semantics.gr) or by linking to Linked open data sources (which can also relate to time intervals) such as Wikidata or [PeriodO](http://perio.do) , or a combination of both [cf appendix “[Time periods in the Europeana Archaeology project](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2603417619#Time-periods-in-the-Europeana-Archaeology-project)”].

> [!NOTE]
> Note: Not all of these are de-referenced yet by Europeana (this is the case for [PeriodO](http://perio.do) ) or not de-referenced as edm:TimeSpans (Wikidata).

In this way it is possible to reflect the conceptual time period the metadata creator intended the object to be associated with. This is especially true when some of these sources come with time intervals. There is thus no concrete recommendation on whether to use a TimeSpan or Concept class - or both - for expressing time periods. Instead we want to make the data providers aware of the different options available to them.

> [!NOTE]
> Note: The DCMI Period Encoding that is picked up by Europeana’s normalisation process [cf. appendix “[Date patterns that can be normalised by Europeana](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2603417619#Date-patterns-that-can-be-normalised-by-Europeana)"] enables the provision of a period's name and dates in a combined (but rather flat) way. In particular, DCMI Periods do not allow the label (*name* attribute) to be provided with language information, which is a severe limitation in a multilingual context like Europeana's. This limitation does not apply to TimeSpan and Concept which can be provided with multilingual labels.

The different ways to provide temporal data of time periods in Europeana come with their own advantages and caveats. An overview can be referenced in the appendix “[Processing of timespans and concepts](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/2603417619#Processing-of-timespans-and-concepts)”.

## Appendices

### Date patterns that can be normalised by Europeana

<details>
<summary>Appendix: Date patterns that can be normalised by Europeana</summary>

> [!NOTE]
> *This appendix is based on the full documentation* [*Normalisation of dates in Europeana (working document)*](https://docs.google.com/document/d/1MVO4iY3b_poLwluWRnP45TDol2Wk6zI6j2s9egmoRRU/edit#heading=h.ecxm1zlk6fe5) *- including all variations in date separators*

**Complete dates or dates with reduced precision**

- *Pattern 1 (‘**yyyy-mm-dd**’ or ‘**dd-mm-yyyy**’) with variations in the separators (hyphens, slash, dots)*

  - *Examples:*

    - *‘1985-08-26’*
    - *‘26.08.1985’*
    - *‘1985-8-26’*
    - *‘1985-08-xx’*
    - *‘1985-08-uu’*
- *Pattern 2 (‘**dd mm yyyy**’ or ‘**yyyy mm dd**’)*

  - *Examples:*

    - *‘26 08 1985’*
    - *‘1985 08 26’*
    - *‘26 8 1985’*
- *Pattern 4 (‘**dd month\_name yyyy**’ or ‘**month\_name dd yyyy**’) with variations in the separators (commas, dots, white spaces)*

  - *Examples:*

    - *‘26. August 1985’*
    - *‘August 26 1985’*
    - *‘26 agosto 1985’* → recognition for the 24 official languages of the EU
- *Pattern 5 (’**month\_name yyyy**’) with variations in the separators (commas, dots, white spaces)*

  - *Examples:*

    - *‘August 1985’*
    - *‘Aug 1985’*
    - *‘Agosto, 1985’*  → recognition for the 24 official languages of the EU

**Date ranges**

- *Pattern 3 (’**date/date**’) with variations in the separators (commas, hyphens, pipe, slash, white spaces)*

  - Examples:

    - *‘1985-08-26/1986-08-30’*
    - *‘1985/8/26? - 1986/8/30?*
- *Pattern 7 (‘**century-century**’)*

  - *Examples:*

    - *‘XIV-XV’*
    - *‘s. XIV-XV’*
    - *‘sec. XIV-XV’*
- *Pattern 10 (‘**year era - year era**’)*

  - *Examples:*

    - *‘3000 BC - 1000 BC’*
- *Pattern 11 (‘**year - abbreviated\_year**’)*

  - *Example:*

    - *‘1770-80’*
    - *‘1930/35’*

**Centuries**

- *Pattern 6 (‘**century**’)*

  - *Examples:*

    - *‘XIV’*
    - *‘15th century’*
    - *‘15..’*
    - *‘s. Ixx’*
    - *‘sec. IXX’*
    - *‘saec. IXX’*

> [!NOTE]
> Note: these cases are pretty much the only ones handled by the pattern; in particular, expressions in other languages such as "Jhd." in German are not recognized.

**Year eras**

- *Pattern 9 (‘**year era**’) with era abbreviations defined by Unicode CLDR*

  - *Examples:*

    - *‘3000 BC’*
    - *‘24 ap. J.-C’*
- *Pattern 12 (‘**-yyyyyyyyy**’, max. 9 digits)*

  - *Example:*

    - *‘-50000’*
- *Pattern 13 (‘**-yyyyyyyyy / -yyyyyyyyy**’)*

  - *Example:*

    - *‘-50000/-30000’*

**Historical periods**

- *Pattern 8 (**DCMI Period**)*

  - *Examples:*

    - *‘name=Byzantine Period; start=0395; end=0641’*
    - *‘start=1929-03-01; end=1939-07-15;*’

**Timestamps**

- *Pattern 14 (**formatted timestamp**) not following ISO8601*

  - *Example:*

    - *‘2018-03-27 09:08:34’*

**Uncertain, approximate and unknown dates**

- Dates are considered uncertain if they are followed, or preceded, by a question mark. The use of ‘?’ is expected in the date patterns 1, 3, 6 and 11. It is also used in EDTF.

  - *Examples:*

    - *1492/1500?*
    - *?1492*
- Dates are considered approximations if preceded by the Latin word ‘circa’ or one of its abbreviations: ‘c.’ or ‘ca.’.

  - *Examples:*

    - *c. 1492*
    - *circa 1492*
    - *ca. 1492/1500*
- Unknown dates are recognized for date ranges. The start or end dates may be indicated as a question mark when unknown.

  - *Examples:*

    - *1656/? (normalised into 1656/)*
    - *?/1910 (normalised into /1910)*

**Dates with additions/annotations**

- If additional information is contained in the date value, the date information can still be extracted for normalisation purposes if the additional text is provided in one these four patterns:

  - *text: date*
  - *(text) date*
  - *date (text)*
  - *date [text]*

</details>

### Time periods in the Europeana Archaeology project

<details>
<summary>Appendix: Time periods in the Europeana Archaeology project</summary>

[Europeana Archaeology](https://europeanaarchaeology.carare.eu/) was a generic services project funded by the Connecting Europe Facility of the European Union with specific activities aiming to increase the use of multilingual Linked Open Data within the metadata. This included work to develop the [Europeana Archaeology mapping tool](https://app-share3d.imsi.athenarc.gr/mappings/login) to enable data partners to map subject, period and place name keywords in their records to LOD concepts.

The project created a metadata and content specification to help partners to apply Europeana’s Publishing Framework to the archaeology content being delivered at the high quality required. The metadata specification recommends the use of dc:date or dcterms:temporal to create a reference to an instance of the edm:Timespan class.

The project developed a vocabulary spreadsheet to define the terminology for integration into the Europeana Archaeology mapping tool. The project partners discussed how to manage the mapping of dates and periods to a common vocabulary given the variety within the native datasets. Initially the team proposed mapping to a simplified vocabulary comprising centuries and millennia (from 15[^th] millennium BCE to 21[^st] century AD). However, this proved impractical once partners began mapping real data. As a result the project’s temporal vocabulary was extended to include all period concepts found in the Getty’s Art and Architecture Thesaurus.

The Europeana Archaeology temporal vocabulary includes the following data:

- AAT Concept name (e.g., Dark Ages (general period))
- AAT URI
- Approximate Start year (where possible to estimate)
- Approximate End year (where possible to estimate)
- Wikidata URI (where a match was found)

The Europeana Archaeology vocabulary mapping tool allows users to map a term in their native data to the AAT concept name and to edit the start and end year for the period. This allows users to give a more accurate start and end year for the period in their region. The mapping table produced by the tool is then used to enrich the metadata by generating an instance of edm:TimeSpan.

</details>

### Processing of timespans and concepts

<details>
<summary>Appendix: Processing of timespans and concepts</summary>

The following overview lists the advantages, disadvantages and consequences of processing for the different ways to provide temporal data of time periods in Europeana as structured representations (skos:Concept and edm:TimeSpan contextual resources, and  DCMI Period structured literals)

**Time period only provided as concept (e.g. with a link to Wikidata)**

- multilingual support in frontend and search (e.g. search for the period in various languages), if the vocabulary used is dereferenced by Europeana.
- no date normalisation during processing of the record in Metis
- no enrichment with Time entities (e.g. <https://www.europeana.eu/de/collections/time/3-3rd-century> ) during processing of the record in Metis
- no filtering/sorting/faceting by date for the object

**Time period only provided as timespan**

- no date normalisation during processing of the record in Metis, as there already is a timespan
- display of skos:prefLabel, if the data provider included it in their data
- multilingual support in frontend and search only if the data provider included skos:prefLabel in different languages in their data
- no enrichment with Time entities during processing of the record in Metis
- no filtering/sorting/faceting by date for the object at this time (but Europeana may support it in the short term)

**Time period provided as both concept and timespan**

- multilingual support (e.g. search for the period in various languages)
- no date normalisation during processing of the record in Metis, as there already is a timespan
- no enrichment with Time entities during processing of the record in Metis
- duplication of values in the display
- no filtering/sorting/faceting by date for the object at this time (but Europeana may support it in the short term)

**Time period provided as DCMI Period**

- dates are normalised during processing of the record in Metis
- enrichment with Time entities during processing of the record in Metis
- duplication in the display, because of normalisation
- no multilingual support (e.g. search for the period in various languages)
- no filtering/sorting/faceting by date for the object if no (normalisable) start and end dates are provided

</details>

## Credits and edit history

**Editors:** Antoine Isaac, Kristina Rose, Eleftheria Tsoupra, Adina Ciocoiu

**Contributors:** Nuno Freire, Fiona Mowat

**Last update:** 2024-06-12
