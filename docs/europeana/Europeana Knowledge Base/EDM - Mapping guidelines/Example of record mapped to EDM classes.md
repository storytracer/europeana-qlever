---
tags:
  - '#edm-mapping-guidelines'
  - '#example-record'
---

# Example of record mapped to EDM classes

- [Original data](#original-data)
- [Mapped data](#mapped-data)
- [Core classes](#core-classes)
  - [Provided CHO](#provided-cho)
  - [Web Resource](#web-resource)
  - [Aggregation](#aggregation)
- [Contextual Classes](#contextual-classes)
- [Additional mapping examples](#additional-mapping-examples)
  - [Examples of high quality data](#examples-of-high-quality-data)

In this section a record is used to show how the EDM properties are distributed across three EDM core classes and two conceptual classes. This example is a description of a Buccin trombone which has a stand-­alone digital image and can also be seen embedded in a video and be heard in a sound recording

![](https://europeana.atlassian.net/wiki/download/attachments/987758739/image-20221215-135152.png?version=1&modificationDate=1671112318853&cacheVersion=1&api=v2)

[*Title: Buccin trombone Nominal pitch: B?*](https://www.europeana.eu/en/item/09102/_UEDIN_214)   
*Data Provider: University of Edinburgh*  
*Rights:* [*http://creativecommons.org/licenses/by­‐nc-­sa/3.0/*](#http-creativecommons-org-licenses-by-nc-sa-3-0)

# Original data

The original metadata for this example is presented in [LIDO](http://www.lido-schema.org/schema/v1.0/lido-v1.0-specification.pdf) format

<details>
<summary>Source data in LIDO format</summary>

```java
<lido>
<lidoRecID type="local">UEDIN:214</lidoRecID>
<descriptiveMetadata xml:lang="en">
<objectClassificationWrap>
 <objectWorkTypeWrap>
 <objectWorkType>
  <term>musical instruments</term>
 </objectWorkType>
 </objectWorkTypeWrap>
<classificationWrap>
<classification>
  <term>Buccin.</term>
</classification>
<classification>
 <conceptID type="SH_Class">423.22</conceptID>
</classification>
 <classification type="InstrumentsKeywordsPivot">
 <conceptID type="URI">http://www.mimo-db.eu/InstrumentsKeywords/4378</conceptID>
 <term label="Instrument class">Buccin</term>
</classification>
<classification type="InstrumentsKeywords">
 <conceptID type="URI">http://www.mimo-­db.eu/InstrumentsKeywords/4378_1</conceptID>
 <term label="Instrument class" xml:lang="en">Buccin</term>
</classification>
<classification type="HornbostelSachsClass">
 <conceptID type="URI">http://www.mimo-­‐db.eu/HornbostelAndSachs/356</conceptID>
 <term label="Hornbostel-­Sachs class" xml:lang="en">423.22 Labrosones with slides</term>
</classification>
</classificationWrap>
</objectClassificationWrap>
<objectIdentificationWrap>
<titleWrap>
<titleSet>
<appellationValue pref="preferred">Buccin trombone. Nominal pitch: B?.</appellationValue>
</titleSet>
</titleWrap>
<repositoryWrap>
<repositorySet type="current">
<repositoryName>
<legalBodyName>
<appellationValue>University of Edinburgh</appellationValue>
</legalBodyName>
</repositoryName>
</repositorySet>
</repositoryWrap>
<objectDescriptionWrap>
<objectDescriptionSet>
 <descriptiveNoteValue>Technical description: Brass; ligature fitting on bell section at joint; stockings on main slides.Bell with one coil, angled to face forwards. Repair History: Main slide possibly not original (tenon of slide section of joint
 is tapered, bell section joint for cylindrical tenon).</descriptiveNoteValue>
</objectDescriptionSet>
</objectDescriptionWrap>
<objectMeasurementsWrap>
<objectMeasurementsSet>
 <displayObjectMeasurements>1200.</displayObjectMeasurements>
</objectMeasurementsSet>
</objectMeasurementsWrap>
</objectIdentificationWrap>
<eventWrap>
<eventSet>
<event>
<eventType>
 <term xml:lang="en">production</term>
</eventType>
<eventActor>
<actorInRole>
<actor>
<nameActorSet>
 <appellationValue xml:lang="en"/>
</nameActorSet>
</actor>
<roleActor>
 <term xml:lang="en">instrument maker</term>
</roleActor>
</actorInRole>
</eventActor>
<eventActor>
 <displayActorInRole>Probably to be identified with the `Trombone with snake's head' purchased by Professor John Donaldson for the Music Classroom, University of Edinburgh, from Thomas Glen, 2 North Bank Street 20 August 1857 for
&#xA3;1/5/-­.</displayActorInRole>
<actorInRole>
<actor>
<nameActorSet>
 <appellationValue xml:lang="en">Probably to be identified with the `Trombone with snake's head' purchased by Professor John Donaldson for the Music Classroom, University of Edinburgh, from Thomas Glen, 2 North Bank Street 20
August 1857 for &#xA3;1/5/-­.</appellationValue>
</nameActorSet>
</actor>
<roleActor>
<term xml:lang="en">provenance</term>
</roleActor>
</actorInRole>
</eventActor>
<eventDate>
<displayDate xml:lang="en">Circa 1840</displayDate>
</eventDate>
<eventPlace>
<placeID type="geonames">http://www.geonames.org/3017382</placeID>
 <namePlaceSet>
 <appellationValue xml:lang="fr">FRANCE</appellationValue>
</namePlaceSet>
</eventPlace>
</event>
</eventSet>
</eventWrap>
</descriptiveMetadata>
<administrativeMetadata xml:lang="en">
<recordWrap>
<recordID type="local"/>
<recordType>
<term>item</term>
</recordType>
<recordSource>
<legalBodyID source="http://www.mimo-­db.eu/DataProviders/5" type="local">UEDIN</legalBodyID>
<legalBodyName>
<appellationValue label="Preferred Name (en)" xml:lang="en">University of Edinburgh</appellationValue>
<appellationValue label="Preferred Name (local language)" xml:lang="en">University of
Edinburgh</appellationValue>
<appellationValue label="City">Edinburgh</appellationValue>
<appellationValue label="Country">United Kingdom</appellationValue>
</legalBodyName>
<legalBodyWeblink label="OAI repository URL">http://image-­projects.lib.ed.ac.uk/oai/request?verb=Identify</legalBodyWeblink>
<legalBodyWeblink label="OAI repository set">EUCHMI</legalBodyWeblink>
</recordSource>
<recordRights/>
</recordWrap>
<resourceWrap>
<resourceSet>
<resourceID type="local">http://www.mimo-­‐db.eu/media/UEDIN/VIDEO/0032195v.mpg</resourceID>
<resourceRepresentation>
<linkResource>http://image-­‐projects.lib.ed.ac.uk//bitstream/10683/17533/3/0032195v.mpg</linkResource>
</resourceRepresentation>
<resourceType>
<term>VIDEO</term>
</resourceType>
</resourceSet>
<resourceSet>
<resourceID type="local">http://www.mimo-­‐db.eu/media/UEDIN/AUDIO/0032195s.mp3</resourceID>
<resourceRepresentation>
<linkResource>http://image-­‐projects.lib.ed.ac.uk//bitstream/10683/17533/2/0032195s.mp3</linkResource>
</resourceRepresentation>
<resourceType>
<term>SOUND</term>
</resourceType>
</resourceSet>
<resourceSet>
<resourceID pref="preferred" type="local">http://www.mimo-­‐
db.eu/media/UEDIN/IMAGE/0032195c.jpg</resourceID>
<resourceRepresentation>
<linkResource>http://image-­‐projects.lib.ed.ac.uk//bitstream/10683/17533/1/0032195c.jpg</linkResource>
</resourceRepresentation>
<resourceType>
<term>IMAGE</term>
</resourceType>
</resourceSet>
</resourceWrap>
</administrativeMetadata>
</lido>
```

</details>

# Mapped data

Each of the classes created from the example data are shown as a section of RDF/XML and a diagram. The source LIDO data in given in the Annex, followed by the full record of mapped data.  
Note: all resources mapped in EDM should have an identifier. It could be either absolute or local. In this document absolute identifiers are clickable

<details>
<summary>Data mapped to EDM</summary>

```java
<?xml version="1.0" encoding="UTF-­‐8"?>
<rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/"
xmlns:edm="http://www.europeana.eu/schemas/edm/"
xmlns:wgs84_pos="http://www.w3.org/2003/01/geo/wgs84_pos#"
xmlns:foaf="http://xmlns.com/foaf/0.1/"
xmlns:rdaGr2="http://rdvocab.info/ElementsGr2/"
xmlns:oai="http://www.openarchives.org/OAI/2.0/"
xmlns:owl="http://www.w3.org/2002/07/owl#"
xmlns:rdf="http://www.w3.org/1999/02/22-­‐rdf-­‐syntax-­‐ns#"
xmlns:ore="http://www.openarchives.org/ore/terms/"
xmlns:skos="http://www.w3.org/2004/02/skos/core#"
xmlns:dcterms="http://purl.org/dc/terms/">
<edm:ProvidedCHO rdf:about="#UEDIN:214">
  <dc:date>Circa 1840</dc:date>
  <dc:description>Technical description: Brass; ligature fitting on bell section at joint; stockings on main slides.Bell with one coil, angled to face forwards. Repair History: Main slide possibly not original (tenon of slide section of joint
  is tapered, bell section joint for cylindrical tenon).</dc:description>
  <dc:identifier>#UEDIN:214</dc:identifier>
  <dcterms:spatial rdf:resource="http://sws.geonames.org/3017382/"/>
  <dc:title>Buccin trombone. Nominal pitch: B?.</dc:title>
  <dc:type rdf:resource="http://www.mimo-­‐db.eu/InstrumentsKeywords/4378"/>
  <dc:type rdf:resource="http://www.mimo-­‐db.eu/HornbostelAndSachs/356"/>
  <edm:type>IMAGE</edm:type>
</edm:ProvidedCHO>
<edm:WebResource rdf:about="http://www.mimo-­db.eu/media/UEDIN/VIDEO/0032195v.mpg">
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by‐nc-sa/3.0/"/>
</edm:WebResource>
<edm:WebResource rdf:about="http://www.mimo‐db.eu/media/UEDIN/AUDIO/0032195s.mp3">
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-­sa/3.0/"/>
</edm:WebResource>
<edm:WebResource rdf:about="http://www.mimo-­db.eu/media/UEDIN/IMAGE/0032195c.jpg">
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-­sa/3.0/"/>
</edm:WebResource>
<edm:Place rdf:about="http://sws.geonames.org/3017382/"/>
  <skos:prefLabel xml:lang="en">France</skos:prefLabel>
</edm:Place>
<skos:Concept rdf:about="http://www.mimo-­db.eu/InstrumentsKeywords/4378">
  <skos:prefLabel xml:lang="en">Buccin</skos:prefLabel>
</skos:Concept>
<skos:Concept rdf:about="http://www.mimo-­db.eu/HornbostelAndSachs/356">
  <skos:prefLabel xml:lang="en">423.22 Labrosones with slides</skos:prefLabel>
</skos:Concept>
<ore:Aggregation rdf:about="http://www.mimo-­db.eu/UEDIN/214">
  <edm:aggregatedCHO rdf:resource="#UEDIN:214"/>
  <edm:dataProvider>University of Edinburgh</edm:dataProvider>
  <edm:hasView rdf:resource="http://www.mimo-­db.eu/media/UEDIN/VIDEO/0032195v.mpg"/>
  <edm:hasView rdf:resource="http://www.mimo-­db.eu/media/UEDIN/AUDIO/0032195s.mp3"/>
  <edm:isShownAt rdf:resource=" http://www.mimo-­db.eu/MIMO/infodoc/ged/view.aspx?eid=OAI_IMAGE_PROJECTS_LIB_ED_AC_UK_10683_17533"/>
  <edm:isShownBy rdf:resource="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg"/>
  <edm:object rdf:resource="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg"/>
  <edm:provider>MIMO -­ Musical Instrument Museums Online</edm:provider>
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-­sa/3.0/"/>
</ore:Aggregation>
</rdf:RDF>
```

</details>

# Core classes

## Provided CHO

In the original LIDO record, these properties can be found in the set related to the descriptive metadata allowing the identification of the object. These properties only describe the Cultural Heritage Object provided to Europeana, in this case a musical instrument.

```java
<edm:ProvidedCHO rdf:about="#UEDIN:214">
  <dc:date>Circa 1840</dc:date>
  <dc:description xml:lang="fr">Technical description: Brass; ligature fitting on bell section at joint; stockings on main slides. Bell with one coil, angled to face forwards.
  Repair History: Main slide possibly not original (tenon of slide section of joint is tapered, bell section joint for cylindrical tenon).</dc:description>
  <dc:identifier>#UEDIN:214</dc:identifier>
  <dcterms:spatial rdf:resource="http://sws.geonames.org/3017382/" />
  <dc:title xml:lang="fr">Buccin trombone. Nominal pitch: B?.</dc:title>
  <dc:type rdf:resource="http://www.mimo-db.eu/InstrumentsKeywords/4378"/>
  <dc:type rdf:resource="http://www.mimo-db.eu/HornbostelAndSachs/356"/>
  <edm:type>IMAGE</edm:type>
</edm:ProvidedCHO>
```

![](https://europeana.atlassian.net/wiki/download/attachments/987758739/image-20221215-150648.png?version=1&modificationDate=1671116814325&cacheVersion=1&api=v2)

## Web Resource

In this example, the cultural heritage object is provided with three different digital representations. This musical instrument has a stand-­‐alone digital image but can also be seen embedded in a video and be heard in a sound recording. This situation results in the creation of three different WebResources pointing to a different type of resources: Image (jpeg), video (mpg) and sound  
recording (mp3).

```java
<edm:WebResource rdf:about="http://www.mimo-db.eu/media/UEDIN/VIDEO/0032195v.mpg">
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-sa/3.0/"/>
</edm:WebResource>
<edm:WebResource rdf:about="http://www.mimo-db.eu/media/UEDIN/AUDIO/0032195s.mp3">
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-sa/3.0/"/>
</edm:WebResource>
<edm:WebResource rdf:about="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg">
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-sa/3.0/"/>
</edm:WebResource>
```

![](https://europeana.atlassian.net/wiki/download/attachments/987758739/image-20221215-150802.png?version=1&modificationDate=1671116888022&cacheVersion=1&api=v2)

## Aggregation

In the original LIDO record, these properties can be found in the set related to the administrative metadata. In our example, the musical instrument has been provided to Europeana by a specific provider: MIMO – Musical Instrument Museums Online. Additional properties have been added to describe the delivery made to Europeana which gathered every information related to the CulturalHeritage Object. This package of information is embedded in an aggregation.

```java
<ore:Aggregation rdf:about="http://www.mimo-db.eu/UEDIN/214">
  <edm:aggregatedCHO rdf:resource="#UEDIN:214"/>
  <edm:dataProvider>University of Edinburgh</edm:dataProvider>
  <edm:hasView rdf:resource="http://www.mimo-db.eu/media/UEDIN/VIDEO/0032195v.mpg"/>
  <edm:hasView rdf:resource="http://www.mimo-db.eu/media/UEDIN/AUDIO/0032195s.mp3"/>
  <edm:isShownAt rdf:resource=" http://www.mimo-db.eu/MIMO/infodoc/ged/view.aspx?eid=OAI_IMAGE_PROJECTS_LIB_ED_AC_UK_10683_17533"/>
  <edm:isShownBy rdf:resource="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg"/>
  <edm:object rdf:resource="http://www.mimo-db.eu/media/UEDIN/IMAGE/0032195c.jpg"/>
  <edm:provider>MIMO - Musical Instrument Museums Online</edm:provider>
  <edm:rights rdf:resource="http://creativecommons.org/licenses/by-nc-sa/3.0/"/>
</ore:Aggregation>
```

![](https://europeana.atlassian.net/wiki/download/attachments/987758739/image-20221215-151058.png?version=1&modificationDate=1671117062838&cacheVersion=1&api=v2)

# Contextual Classes

In this example instead of linking data directly to the edm:ProvidedCHO it is possible to create separate nodes for Concept and Place. The original data contained identifiers for two Concepts taken from controlled vocabularies – the MIMO instrument keywords vocabulary and the Hornbostel-Sachs musical classification system. Similarly, there is an identifier for the Place taken from [GeoNames](http://www.geonames.org/). Both of these are shown using [SKOS](https://www.w3.org/2004/02/skos/).

```java
<edm:Place rdf:about="http://sws.geonames.org/3017382/"/>
  <skos:preflabel xml:lang="en">France</skos:prefLabel>
  <wgs84_pos:lat>47.0000</wgs84_pos:lat>
  <wgs84_pos:long>2.00</wgs84_pos:long>
</edm:Place>
<skos:Concept rdf:about="http://www.mimo-db.eu/InstrumentsKeywords/4378">
  <skos:prefLabel xml:lang="en">Buccin</skos:prefLabel>
</sko:Concept>
<skos:Concept rdf:about="http://www.mimo-db.eu/HornbostelAndSachs/356">
  <skos:prefLabel xml:lang="en">423.22 Labrosones with slides</skos:prefLabel>
</skos:Concept>
```

![](https://europeana.atlassian.net/wiki/download/attachments/987758739/image-20221215-152127.png?version=1&modificationDate=1671117691744&cacheVersion=1&api=v2)

# Additional mapping examples

Additional mapping examples, in the context of content tiers and metadata tiers, can be found here [Example records - content & metadata tiers](../Publishing%20guide/Content%20&%20Metadata%20Tiers/Example%20records%20-%20content%20&%20metadata%20tiers.md) .

## Examples of high quality data

Examples of high quality data can be found here [Examples of high quality data](../Publishing%20guide/Content%20&%20Metadata%20Tiers/Examples%20of%20high%20quality%20data.md) .
