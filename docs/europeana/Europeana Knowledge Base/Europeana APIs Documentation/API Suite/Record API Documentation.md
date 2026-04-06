---
tags:
  - '#apidocs'
---

# Record API Documentation

The Record API provides direct access to Europeana’s data and metadata, which is modelled using [Page not accessible (ID: 2385313809)]. EDM is an open flexible data model used to capture the data and metadata about Cultural Heritage Objects (CHOs). The Record API is used to retrieve all of the data and metadata that relates to a single Cultural Heritage object, which will have a single Europeana ID. A Europeana ID is made up of a dataset number, and a record ID. For the object at this URL: <https://www.europeana.eu/item/90402/RP_P_1984_87>, the dataset ID is 90402, and the record ID is RP\_P\_1984\_87. Both are findable by looking at the URL.

|                                                                                 |                                            |
|:--------------------------------------------------------------------------------|:-------------------------------------------|
| > [!NOTE] [Get your API Key here](https://pro.europeana.eu/pages/get-api) <br/> | > [!TIP] [Get Started](#get-started) <br/> ||                                                                              |                                                                                              |
|:-----------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|
| > [!NOTE] [Go to the Console](https://api.europeana.eu/console/record) <br/> | > [!WARNING] [Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) <br/> |

---

- [Getting Started](#getting-started)
- [Retrieving a record in the default format (JSON)](#retrieving-a-record-in-the-default-format-json)
- [Retrieving a Record in the JSON-LD format](#retrieving-a-record-in-the-json-ld-format)
- [Retrieving a Record in the RDF/XML format](#retrieving-a-record-in-the-rdf-xml-format)

## Getting Started

Every call to the Record API is an HTTPS request in the following URL signature:

> *https://api.europeana.eu/record/v2/[RECORD\_ID].[FORMAT]*

Where the variables in the URL path mean:

|            |                                                                                                                                                                                                                                                           |
|:-----------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| RECORD\_ID | The identifier of the record which is composed of the dataset identifier plus a local identifier within the dataset in the form of "/DATASET\_ID/LOCAL\_ID", for more detail see [Europeana ID](https://pro.europeana.eu/page/intro#identifying-records). |
| FORMAT     | The file extension corresponding to one of the supported output formats, namely: .json, .jsonld, .rdf. See next section on [Output Formats](https://pro.europeana.eu/page/record#formats)                                                                 |

Additional parameters may apply to the request above such as the [API FAQ](../API%20FAQ.md) and [Browser access](https://pro.europeana.eu/page/intro#browsers).

An example Record API call to get all of the data and metadata from [this item](https://www.europeana.eu/en/item/90402/RP_P_1984_87) in JSON would be: <https://api.europeana.eu/record/v2/90402/RP_P_1984_87.json?wskey=YOURAPIKEY>

### Supported Output Formats

The Record API supports 3 serialization formats, namely: JSON, JSON-LD and RDF/XML. The primary and default output supported by this API is JSON which also means that some fields are only available in this format. Both JSON-LD and RDF/XML are formats to represent Linked Data which used predefined transport schemas for serializing [RDF](https://www.w3.org/RDF/) data. To request a record in either of these formats, just alter the extension of the call to the desired format. The table below explains each of the formats and their respective extensions.

<details>
<summary>List of Output formats for Record API Responses</summary>

|  Format             |  Extension    |  Description                                                                                                                                                                                                                                                            |
|:--------------------|:--------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [JSON](#json)       | .json         | Returns The output serialized in [JSON](https://www.json.org/), using a Europeana specific schema for representing EDM data.                                                                                                                                            |
| [JSON-LD](#json-ld) | .json-ld      | An alternative JSON output based on the [JSON-LD format](https://json-ld.org/) for RDF.                                                                                                                                                                                 |
| [RDF/XML](#rdf-xml) | .rdf          | The XML output is primarily based on [RDF/XML format](https://www.w3.org/TR/rdf-syntax-grammar/) for RDF serialization but following the [EDM XSD schema](https://www.europeana.eu/schemas/edm/EDM.xsd) (the same schema is also used for data ingestion to Europeana). |

</details>

### Error Responses

An error occurring during processing of an API method is reported by (1) a relevant HTTP status code, (2) a value of the success field and (3) a meaningful error message in the error field. The following table shows the fields appearing within an error response:

<details>
<summary>List of Response fields when getting an error Response from the Record APÏ</summary>

|  Field        |  Datatype    |  Description                                                                      |
|:--------------|:-------------|:----------------------------------------------------------------------------------|
| apikey        | String       | The authentication parameter sent out by the client (the wskey parameter)         |
| success       | Boolean      | A boolean (true/false) flag denoting the successful execution of the call         |
| statsDuration | Number       | The time (in milliseconds) taken to serve the request                             |
| error         | String       | If the call was not successful, this fields will contain a detailed text message. |

</details>

The following kinds of errors can be returned by the API:

<details>
<summary>List of error responses the Record API can throw</summary>

|    HTTP Status Code  |  Description                                                                                                                                                                   |
|---------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|                 200  | The request was executed successfully.                                                                                                                                         |
|                 401  | Authentication credentials were missing or authentication failed.                                                                                                              |
|                 404  | The requested record was not found.                                                                                                                                            |
|                 429  | The request could be served because the application has reached its usage limit.                                                                                               |
|                 500  | An error has occorred in the server which has not been properly handled. If you receive this error it means that something has gone really wrong, so please report them to us! |

</details>

<details>
<summary>Example: Request to the Record API supplying an invalid (unknown) API key</summary>

Request:

> [*https://api.europeana.eu/record/v2/90402/SK\_A\_3262.json?wskey=test*](https://api.europeana.eu/record/v2/90402/SK_A_3262.json?wskey=test)

Response:

```java
{
    "apikey": "test",
    "success": false,
    "error": "Invalid API key"
}
```

</details>

## Retrieving a record in the default format (JSON)

JSON is the primary output format of the Record API. It uses a Europeana-specific schema for representing EDM data.

A response in JSON will always contain several fields that present information about the handling of the request, while the concrete information about the record is presented in the "object" field.

<details>
<summary>List of top-level Response fields from the Record API</summary>

|  Field        |  Datatype    |  Description                                                                              |
|:--------------|:-------------|:------------------------------------------------------------------------------------------|
| apikey        | String       | the authentication parameter sent out by the client (the wskey parameter)                 |
| success       | Boolean      | a boolean (true/false) flag denoting the successful execution of the call                 |
| statsDuration | Number       | the time (in milliseconds) taken to serve the request                                     |
| requestNumber | Number       | a positive number denoting the number of request by this API key within the last 24 hours |
| Object        | Object       | The object representing the EDM metadata record, see next section                         |

</details>

### Object

The Object gathers all the information contained within an EDM metadata record.

<details>
<summary>List of all possible Response fields in the Object field of a Record API Response</summary>

|  Field                    |  Datatype                    |  Description                                                                                                     |
|:--------------------------|:-----------------------------|:-----------------------------------------------------------------------------------------------------------------|
| about                     | String                       | [Page not accessible (ID: 2385313809)] of the returned object.                                                   |
| agents                    | Array (Agent)                | A collection of EDM Agent objects contextually related to the object. Find more in the EDM Definition.           |
| aggregations              | Array (Aggregation)          | A collection of EDM Aggregation objects related to the object. Find more in the EDM Definition.                  |
| concepts                  | Array (Concept)              | A collection of SKOS Concept objects contextually related to the object. Find more in the EDM Definition.        |
| country                   | Array (String)               |                                                                                                                  |
| europeanaAggregation      | Array (EuropeanaAggregation) | A collection of EDM Europeana Aggregation objects related to the object. Find more in the EDM Definition.        |
| europeanaCollectionName   | Array (String)               | A collection of names of the datasets the object belongs to.                                                     |
| europeanaCompleteness     | Number                       | A number between 0 and 10 representing the metadata quality of the object.                                       |
| language                  | Array (String)               | A singleton collection with the language of the object.                                                          |
| licenses                  | Array (License)              | A collection of CC Licenses. Find more in the EDM Definition.                                                    |
| optOut                    | Boolean                      | Flag indicating whether the provider allowed retrieval of a thumbnail of the record                              |
| places                    | Array (Place)                | A collection of EDM Place objects contextually related to the object. Find more in the EDM Definition.           |
| provider                  | Array (String)               | A singleton collection with the name of the organization that delivered this object to Europeana.                |
| providedCHOs              | Array (ProvidedCHO)          | A collection of Provided Cultural Heritage Objects related to the record. Find more in the EDM Definition.       |
| proxies                   | Array (Proxy)                | A collection of proxy objects for Provided Cultural Heritage Objects. Find more in the EDM Definition.           |
| services                  | Array (Service)              | A collection of service objects required to consume a Web Resource according to a specific protocol and profile. |
| timespans                 | Array (TimeSpan)             | A collection of EDM TimeSpan objects contextually related to the object. Find more in the EDM iDefinition.       |
| timestamp\_created\_epoch | Number                       | Unix time of the date when the object was created.                                                               |
| timestamp\_update\_epoch  | Number                       | Unix time of the date when the object was last updated.                                                          |
| timestamp\_created        | String                       | ISO 8601 format of the date when the object was created.                                                         |
| timestamp\_update         | String                       | ISO 8601 format of the date when the object was last updated.                                                    |
| title                     | Array (String)               | A collection with the main and alternative titles of the object.                                                 |
| type                      | String                       | The type of the object (see the TYPE facet)                                                                      |
| year                      | Array (String)               |                                                                                                                  |

</details>

### JSON Structures and Fields for EDM

The JSON structures and fields defined in this section all represent classes and properties defined in EDM. More information can be found on the[Page not accessible (ID: 2385313809)]

<details>
<summary>List of EDM fields in a Record API Response and their corresponding JSON fields and datatypes</summary>

|  EDM property                          |  JSON Field                   |  [JSON Datatype](#json-datatype)    |
|:---------------------------------------|:------------------------------|:------------------------------------|
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| edm:dataProvider                       | edmDataProvider               | LangMap                             |
| edm:isShownBy                          | edmIsShownBy                  | String                              |
| edm:isShownAt                          | edmIsShownAt                  | String                              |
| edm:object                             | edmObject                     | String                              |
| edm:provider                           | edmProvider                   | LangMap                             |
| edm:rights                             | edmRights                     | LangMap                             |
| edm:ugc                                | edmUgc                        | String                              |
| dc:rights                              | dcRights                      | LangMap                             |
| edm:hasView                            | hasView                       | Array (String)                      |
| edm:aggregatedcHO                      | aggregatedCHO                 | String                              |
| ore:aggregates                         | aggregates                    | Array (String)                      |
| edm:unstored                           | edmUnstored                   | Array (String)                      |
| edm:WebResource                        | webResources                  | Array (WebResource)                 |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| edm:WebResource                        | webResources                  | Array (WebResource)                 |
| edm:aggregatedcHO                      | aggregatedcHO                 | String                              |
| ore:aggregates                         | aggregates                    | Array (String)                      |
| dc:creator                             | dcCreator                     | LangMap                             |
| edm:landingPage                        | edmLandingPage                | String                              |
| edm:isShownBy                          | edmIsShownBy                  | String                              |
| edm:hasView                            | edmHasView                    | Array (String)                      |
| edm:country                            | edmCountry                    | LangMap                             |
| edm:language                           | edmLanguage                   | LangMap                             |
| edm:rights                             | edmRights                     | LangMap                             |
| edm:preview                            | edmPreview                    | String                              |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| owl:sameAs                             | owlSameAs                     | Array (String)                      |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| dc:contributor                         | dcContributor                 | LangMap                             |
| dc:coverage                            | dcCoverage                    | LangMap                             |
| dc:creator                             | dcCreator                     | LangMap                             |
| dc:date                                | dcDate                        | LangMap                             |
| dc:description                         | dcDescription                 | LangMap                             |
| dc:format                              | dcFormat                      | LangMap                             |
| dc:identifier                          | dcIdentifier                  | LangMap                             |
| dc:language                            | dcLanguage                    | LangMap                             |
| dc:publisher                           | dcPublisher                   | LangMap                             |
| dc:relation                            | dcRelation                    | LangMap                             |
| dc:rights                              | dcRights                      | LangMap                             |
| dc:source                              | dcSource                      | LangMap                             |
| dc:subject                             | dcSubject                     | LangMap                             |
| dc:title                               | dcTitle                       | LangMap                             |
| dc:type                                | dcType                        | LangMap                             |
| dcterms:alternative                    | dctermsAlternative            | LangMap                             |
| dcterms:conformsTo                     | dctermsConformsTo             | LangMap                             |
| dcterms:created                        | dctermsCreated                | LangMap                             |
| dcterms:extent                         | dctermsExtent                 | LangMap                             |
| dcterms:hasFormat                      | dctermsHasFormat              | LangMap                             |
| dcterms:hasPart                        | dctermsHasPart                | LangMap                             |
| dcterms:hasVersion                     | dctermsHasVersion             | LangMap                             |
| dcterms:isFormatOf                     | dctermsIsFormatOf             | LangMap                             |
| dcterms:isPartOf                       | dctermsIsPartOf               | LangMap                             |
| dcterms:isReferencedBy                 | dctermsIsReferencedBy         | LangMap                             |
| dcterms:isReplacedBy                   | dctermsIsReplacedBy           | LangMap                             |
| dcterms:isRequiredBy                   | dctermsIsRequiredBy           | LangMap                             |
| dcterms:issued                         | dctermsIssued                 | LangMap                             |
| dcterms:isVersionOf                    | dctermsIsVersionOf            | LangMap                             |
| dcterms:medium                         | dctermsMedium                 | LangMap                             |
| dcterms:provenance                     | dctermsProvenance             | LangMap                             |
| dcterms:references                     | dctermsReferences             | LangMap                             |
| dcterms:replaces                       | dctermsReplaces               | LangMap                             |
| dcterms:requires                       | dctermsRequires               | LangMap                             |
| dcterms:spatial                        | dctermsSpatial                | LangMap                             |
| dcterms:tableOfContents                | dctermsTOC                    | LangMap                             |
| dcterms:temporal                       | dctermsTemporal               | LangMap                             |
| edm:currentLocation                    | edmCurrentLocation            | String                              |
| edm:hasMet                             | edmHasMet                     | LangMap                             |
| edm:hasType                            | edmHasType                    | LangMap                             |
| edm:incorporates                       | edmIncorporates               | Array (String)                      |
| edm:isDerivativeOf                     | edmIsDerivativeOf             | Array (String)                      |
| edm:isNextInSequence                   | edmIsNextInSequence           | String                              |
| edm:isRelatedTo                        | edmIsRelatedTo                | LangMap                             |
| edm:isRepresentationOf                 | edmIsRepresentationOf         | String                              |
| edm:isSimilarTo                        | edmIsSimilarTo                | Array (String)                      |
| edm:isSuccessorOf                      | edmIsSuccessorOf              | Array (String)                      |
| edm:realizes                           | edmRealizes                   | Array (String)                      |
| edm:type                               | edmType                       | String                              |
| edm:rights                             | edmRights                     | LangMap                             |
| edm:wasPresentAt                       | edmWasPresentAt               | Array (String)                      |
| edm:europeanaProxy                     | europeanaProxy                | Boolean                             |
| ore:proxyFor                           | proxyFor                      | String                              |
| ore:proxyIn                            | proxyIn                       | Array (String)                      |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| dc:rights                              | webResourceDcRights           | LangMap                             |
| edm:rights                             | webResourceEdmRights          | LangMap                             |
| dc:description                         | dcDescription                 | LangMap                             |
| dc:format                              | dcFormat                      | LangMap                             |
| dc:source                              | dcSource                      | LangMap                             |
| dcterms:extent                         | dctermsExtent                 | LangMap                             |
| dcterms:issued                         | dctermsIssued                 | LangMap                             |
| dcterms:conformsTo                     | dctermsConformsTo             | LangMap                             |
| dcterms:created                        | dctermsCreated                | LangMap                             |
| dcterms:isFormatOf                     | dctermsIsFormatOf             | LangMap                             |
| dcterms:hasPart                        | dctermsHasPart                | LangMap                             |
| dcterms:isReferencedBy                 | dctermsIsReferencedBy         | String                              |
| edm:isNextInSequence                   | isNextInSequence              | String                              |
| edm:codecName                          | edmCodecName                  | String                              |
| ebucore:hasMimeType                    | ebucoreHasMimeType            | String                              |
| ebucore:fileByteSize                   | ebucoreFileByteSize           | Number                              |
| ebucore:duration                       | duration                      | String                              |
| ebucore:width                          | ebucoreWidth                  | Number                              |
| ebucore:height                         | ebucoreHeight                 | Number                              |
| edm:spatialResolution                  | edmSpatialResolution          | String                              |
| ebucore:sampleSize                     | ebucoreSampleSize             | String                              |
| ebucore:sampleRate                     | ebucoreSampleRate             | String                              |
| ebucore:bitRate                        | ebucoreBitRate                | String                              |
| ebucore:frameRate                      | ebucoreFrameRate              | String                              |
| edm:hasColorSpace                      | edmHasColorSpace              | String                              |
| edm:componentColor                     | edmComponentColor             | Array (String)                      |
| ebucore:orientation                    | ebucoreOrientation            | String                              |
| ebucore:audioChannelNumber             | ebucoreAudioChannelNumber     | String                              |
| svcs:has\_service                      | svcsHasService                | String                              |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| dcterms:comformsTo                     | dctermsConformsTo             | String                              |
| doap:implements                        | doapImplements                | Array (String)                      |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| skos:prefLabel                         | prefLabel                     | LangMap                             |
| skos:altLabel                          | altLabel                      | LangMap                             |
| skos:hiddenLabel                       | hiddenLabel                   | LangMap                             |
| skos:note                              | note                          | LangMap                             |
| edm:begin                              | begin                         | LangMap                             |
| edm:end                                | end                           | LangMap                             |
| edm:wasPresentAt                       | edmWasPresentAt               | Array (String)                      |
| edm:hasMet                             | edmHasMet                     | LangMap                             |
| edm:isRelatedTo                        | edmIsRelatedTo                | LangMap                             |
| owl:sameAs                             | owlSameAs                     | Array (String)                      |
| foaf:name                              | foafName                      | LangMap                             |
| dc:date                                | dcDate                        | LangMap                             |
| dc:identifier                          | dcIdentifier                  | LangMap                             |
| rdaGr2:dateOfBirth                     | rdaGr2DateOfBirth             | LangMap                             |
| rdaGr2:dateOfDeath                     | rdaGr2DateOfDeath             | LangMap                             |
| rdaGr2:dateOfEstablishment             | rdaGr2DateOfEstablishment     | LangMap                             |
| rdaGr2:dateOfTermination               | rdaGr2DateOfTermination       | LangMap                             |
| rdaGr2:gender                          | rdaGr2Gender                  | LangMap                             |
| rdaGr2:professionOrOccupation          | rdaGr2ProfessionOrOccupation  | LangMap                             |
| rdaGr2:biographicalInformation         | rdaGr2BiographicalInformation | LangMap                             |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| skos:prefLabel                         | prefLabel                     | LangMap                             |
| skos:altLabel                          | altLabel                      | LangMap                             |
| skos:hiddenLabel                       | hiddenLabel                   | LangMap                             |
| skos:note                              | note                          | LangMap                             |
| skos:broader                           | broader                       | Array (String)                      |
| skos:narrower                          | narrower                      | Array (String)                      |
| skos:related                           | related                       | Array (String)                      |
| skos:broadMatch                        | broadMatch                    | Array (String)                      |
| skos:narrowMatch                       | narrowMatch                   | Array (String)                      |
| skos:exactMatch                        | exactMatch                    | Array (String)                      |
| skos:relatedMatch                      | relatedMatch                  | Array (String)                      |
| skos:closeMatch                        | closeMatch                    | Array (String)                      |
| skos:notation                          | notation                      | LangMap                             |
| skos:inScheme                          | inScheme                      | Array (String)                      |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| skos:prefLabel                         | prefLabel                     | LangMap                             |
| skos:altLabel                          | altLabel                      | LangMap                             |
| skos:hiddenLabel                       | hiddenLabel                   | LangMap                             |
| skos:note                              | note                          | LangMap                             |
| dcterms:isPartOf                       | isPartOf                      | LangMap                             |
| wgs84:lat                              | latitude                      | Number                              |
| wgs84:long                             | longitude                     | Number                              |
| wgs84:alt                              | altitude                      | Number                              |
| wgs84:lat\_long                        | position                      | Object                              |
| dcterms:hasPart                        | dcTermsHasPart                | LangMap                             |
| owl:sameAs                             | owlSameAs                     | Array (String)                      |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| skos:prefLabel                         | prefLabel                     | LangMap                             |
| skos:altLabel                          | altLabel                      | LangMap                             |
| skos:hiddenLabel                       | hiddenLabel                   | LangMap                             |
| skos:note                              | note                          | LangMap                             |
| edm:begin                              | begin                         | LangMap                             |
| edm:end                                | end                           | LangMap                             |
| dcterms:isPartOf                       | isPartOf                      | LangMap                             |
| dcterms:hasPart                        | dctermsHasPart                | LangMap                             |
| owl:sameAs                             | owlSameAs                     | Array (String)                      |
| [Page not accessible (ID: 2385313809)] |                               |                                     |
| rdf:about                              | about                         | String                              |
| odrl:inheritFrom                       | odrlInheritFrom               | String                              |
| cc:deprecatedOn                        | ccDeprecatedOn                | String                              |

</details>

### JSON Datatypes

The JSON output of this API uses the following datatypes:

<details>
<summary>List of JSON Datatypes used by the Record API</summary>

|  Datatype         |  Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Boolean           | true or false                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Number            | integer or double precision floating-point number                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| String            | double-quoted Unicode, with backslash escaping                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Array             | an ordered sequence of values, comma-separated and enclosed in square brackets; the values do not need to be of the same type                                                                                                                                                                                                                                                                                                                                                                                          |
| Array([Datatype]) | an ordered sequence values of Datatype (e.g. String or Object), comma-separated and enclosed in square brackets                                                                                                                                                                                                                                                                                                                                                                                                        |
| Object            | an unordered collection of key:value pairs with the ':' character separating the key and the value, comma-separated and enclosed in curly braces; the keys must be strings and should be distinct from each other                                                                                                                                                                                                                                                                                                      |
| LangMap           | A special datatype to provide values in various languages. It is an associative array where the keys are ISO language codes or "def" (where the language is not given), and the value is an array of strings. For example: `"dcTitle": {"por": ["Paris"]}`. Here the datatype of dcTitle is a LanguageMap: the language code is "por" (stands for Portuguese), and the value is a list with only one element: "Paris". For those familiar with Java notations: is it the JSON equivalent of `Map<String,List<String>>` |
| null              | empty value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

</details>

## Retrieving a Record in the JSON-LD format

JSON-LD stands for JSON for Linking Data and is one of the Linked Data formats that the Record API supports. The basic structure of the JSON-LD response is similar to the default [JSON format of the Record API](#json-format-of-the-record-api):

<details>
<summary>example JSON-LD Response from the Record API</summary>

```java
{
  "@context": {
    "ore": "http://www.openarchives.org/ore/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"
  },
  "@graph": [
    {
      "@id": "http://data.europeana.eu/aggregation/europeana/09102/_CM_0839888",
      "@type": "edm:EuropeanaAggregation",
      "dc:creator": "Europeana",
      "edm:aggregatedCHO": {
        "@id": "http://data.europeana.eu/item/09102/_CM_0839888"
      },
      "edm:collectionName": "09102_Ag_EU_MIMO_ESE",
      "edm:country": "Europe",
      "edm:landingPage": {
        "@id": "http://www.europeana.eu/portal/record/09102/_CM_0839888.html"
      },
      "edm:language": "mul",
      "edm:rights": {
        "@id": "http://creativecommons.org/licenses/by-nc-sa/3.0/"
      }
    },
    {
      "@id": "http://data.europeana.eu/aggregation/provider/09102/_CM_0839888",
      "@type": "ore:Aggregation",
      ...
    },
    {
      "@id": "http://data.europeana.eu/item/09102/_CM_0839888",
      "@type": "edm:ProvidedCHO"
    },
    {
      "@id": "http://data.europeana.eu/proxy/europeana/09102/_CM_0839888",
      "@type": "ore:Proxy",
      ...
    },
    {
      "@id": "http://data.europeana.eu/proxy/provider/09102/_CM_0839888",
      "@type": "ore:Proxy",
      ...
    },
    {
      "@id": "http://mediatheque.cite-musique.fr/masc/play.asp?ID=0839888",
      "@type": "edm:WebResource"
    },
    {
      "@id": "http://semium.org/time/1910",
      "@type": "edm:TimeSpan",
      ...
    },
    {
      "@id": "http://semium.org/time/19xx_1_third",
      "@type": "edm:TimeSpan",
      ...
    },
    {
      "@id": "http://sws.geonames.org/2950159",
      "@type": "edm:Place",
      ...
    },
    {
      "@id": "http://www.geonames.org/2950159",
      "@type": "edm:Place",
      ...
    },
    {
      "@id": "http://www.mimo-db.eu/InstrumentsKeywords/4495",
      "@type": "skos:Concept",
      ...
    },
    {
      "@id": "http://www.mimo-db.eu/media/MF-GET/IMAGE/MFIM000024482.jpg",
      "@type": "edm:WebResource",
      ...
    }
  ]
}

```

</details>

The big differences between JSON and JSON-LD are

1. JSON-LD makes use of [Internationalized Resource Identifiers, IRIs](http://en.wikipedia.org/wiki/Internationalized_resource_identifier) as property names. This ensures that each statement of a record matches a standard vocabulary. In Europeana's implementation the properties are qualified names (in the format of "namespace\_prefix:property\_name" such as "dc:creator") for the sake of brevity. In the normal JSON response we use non-standard camel case ("dcCreator") property names. In the [JSON](#json) Section you can find the connections between our camelCase property names and the JSON-LD and RDF qualified names.
2. JSON-LD has a `@context` part, which links object properties in a JSON document to concepts in an ontology. In our JSON-LD this lists the used namespaces and their prefixes.
3. JSON-LD makes a distinction between values that are string literals from values that are other resources.

<details>
<summary>example of how JSON-LD distinguishes between string literal values and other values</summary>

This is how JSON-LD structures a value that has a resource as its datatype:

```java
{
  "edm:landingPage": {
    "@id": "http://www.europeana.eu/portal/record/09102/_CM_0839888.html"
  },
  ...
}

```

And this is how JSON-LD structures a value that has a string literal as its datatype:

```java
{
  "dc:creator": "Europeana",
   ...
}

```

</details>

## Retrieving a Record in the RDF/XML format

The XML output is primarily based on [RDF/XML format](https://www.w3.org/TR/rdf-syntax-grammar/) for RDF serialization but following the [EDM XSD schema](https://www.europeana.eu/schemas/edm/EDM.xsd) (the same schema is also used for data ingestion to Europeana).

The structure of an RDF/XML document formated using the EDM XSD schema is as follows:

- The root element of the XML document is "rdf:RDF". This element will have declared all the namespaces required for the qualified names of all classes and properties being using within the document. A list of all supported namespaces can be view in our [Page not accessible (ID: 2385313809)].
- Within the root element, all instances of EDM classes are declared using the qualified name of the classes as the label for the XML element. An "rdf:about" attribute is present indicating the IRI of that instance.

### Datatypes for request parameters

The following datatypes are defined for the request parameters used in this method.

|  Datatype    |  Description                                          |
|:-------------|:------------------------------------------------------|
| String       | Values are preserved as they are present in the data. |

### Deprecation Information

The following will be deprecated per the given date, ensure that your API clients are updated accordingly:

|  Date        |  Deprecation Details                                                                                                                                                                              |
|:-------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| January 2018 | As the API supports SSL now for a while, we will start to redirect all non-SSL traffic for the API to SSL. Ensure your applications follow redirects if needed or adjust the hostname to use SSL. |

### Roadmap and Changelog

We deploy new versions of the portal and API quite regularly, but not all new versions result in changes in the interface. To see the changes made for this version and also all previous releases, see the [API changelog in the project GitHub](https://github.com/europeana/api2/releases/).
