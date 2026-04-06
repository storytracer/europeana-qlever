
# Organization profile for data providers and aggregators (definitions)

In addition to managing data about cultural heritage objects, Europeana maintains information about the datasets that Europeana receives, and the organizations involved in their delivery. Europeana created the EDM Organization profile to support information about the data providers and aggregators.

**Table of contents**

- [Introduction and scope](#introduction-and-scope)
- [Terminology](#terminology)
- [Overview](#overview)
- [Properties Applicable to foaf:Organization and edm:Aggregator](#properties-applicable-to-foaf-organization-and-edm-aggregator)
  - [Property skos:prefLabel](#property-skos-preflabel)
  - [Property skos:altLabel](#property-skos-altlabel)
  - [Property skos:hiddenLabel](#property-skos-hiddenlabel)
  - [Property dc:description](#property-dc-description)
  - [Property edm:acronym](#property-edm-acronym)
  - [Property owl:sameAs](#property-owl-sameas)
  - [Property edm:country](#property-edm-country)
  - [Property edm:language](#property-edm-language)
  - [Property edm:geographicScope](#property-edm-geographicscope)
  - [Property edm:heritageDomain](#property-edm-heritagedomain)
  - [Property edm:aggregatedVia](#property-edm-aggregatedvia)
  - [Property foaf:logo](#property-foaf-logo)
  - [Property foaf:phone](#property-foaf-phone)
  - [Property foaf:homepage](#property-foaf-homepage)
  - [Property foaf:depiction](#property-foaf-depiction)
  - [Property vcard:hasAddress](#property-vcard-hasaddress)
- [Properties Applicable to edm:Aggregator](#properties-applicable-to-edm-aggregator)
  - [Property edm:aggregatesFrom](#property-edm-aggregatesfrom)
  - [Property edm:providesSupportForMediaType](#property-edm-providessupportformediatype)
  - [Property edm:providesSupportForDataActivity](#property-edm-providessupportfordataactivity)
  - [Property edm:providesAudienceEngagementActivity](#property-edm-providesaudienceengagementactivity)
  - [Property foaf:mbox](#property-foaf-mbox)
- [Properties Applicable to vcard:Address](#properties-applicable-to-vcard-address)
  - [Property vcard:street-address](#property-vcard-street-address)
  - [Property vcard:locality](#property-vcard-locality)
  - [Property vcard:postal-code](#property-vcard-postal-code)
  - [Property vcard:country-name](#property-vcard-country-name)
  - [Property vcard:hasGeo](#property-vcard-hasgeo)
- [Properties Applicable to vcard:Location](#properties-applicable-to-vcard-location)
  - [Property wgs84\_pos:lat](#property-wgs84-pos-lat)
  - [Property wgs84\_pos:long](#property-wgs84-pos-long)

# Introduction and scope

In order to provide functionality based on the names and other attributes of organizations providing data to Europeana it is necessary for these attributes to be recorded in a structured and controlled fashion. This profile is used to support authority control of (Data) Providers’ descriptions in Europeana’s Customer Relationship Management (CRM) system and it lists the data elements that can be used to describe data providers and aggregators.    
The profile is based on the description elements defined for the W3C [Organization](https://www.w3.org/TR/vocab-org/) and [vCard](https://www.w3.org/TR/vcard-rdf/) ontologies and the elements that Europeana is already gathering in its Customer Relationship Management system.

Note that the American spelling of “organization” is used throughout to be compatible with the [FOAF Vocabulary](https://xmlns.com/foaf/spec/).

# Terminology

**Organization**: this is a generic term for an organization of any sort that could be named as a Data Provider or Aggregator.  
**Aggregator**: an organization working with cultural institutions and collectors to gather authentic, trustworthy and robust data. They make this content available to a broader audience via their own services, Europeana, and other infrastructures, for example, for education and research (from <https://pro.europeana.eu/page/glossary> )​​.   
**Data Provider**: an organization that submits data to [Europeana.eu](http://Europeana.eu) . Data providers may submit data directly to Europeana but are more likely to use the services of an Aggregator.  
*NB: in the terminology being current developed (as of November 2024) by the Data Spaces Support Center, Data Providers are Data Product Providers and Aggregators are Data Product Provider Agents.*

# Overview

![Organization profile - 2025-20260206-152005.png](https://europeana.atlassian.net/wiki/download/attachments/3261923389/Organization%20profile%20-%202025-20260206-152005.png?version=1&modificationDate=1770391225120&cacheVersion=1&api=v2)

Many of the properties described below will apply to an organization and will be mapped from the CRM fields to EDM classes/properties accordingly. For example:

- An **Organization** is represented as a `foaf:Organization` class (a subclass of `edm:Agent`), which contains all the details of the postal address. URIs for organizations are minted by Europeana in the form of ‘"http://data.europeana.eu/organisation/{IDENTIFIER}", where {IDENTIFIER} corresponds to the system identifier automatically assigned by the Entity Management system.
- An **Aggregator** is represented as a `edm:Aggregator` class (s subclass of `foaf:Organization`). They are represented and identified as other organizations but they have additional properties specific to their role as aggregator.
- An **Address** will be represented using the `vcard:Address` class and associated with the organization via the `vcard:hasAddress` property. URIs for addresses are a concatenation of the URI of the organization with “#address” (i.e. “http://data.europeana.eu/organisation/{IDENTIFIER}#address").

# Properties Applicable to foaf:Organization and edm:Aggregator

## **Property** skos:prefLabel

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|:----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.w3.org/2004/02/skos/core#prefLabel                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Label**                   | name                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Definition**              | The preferred form of name of the organization.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Usage**                   | The preferred form of name of the organization should be given in as many languages as can be provided, but at most, there can only be one per language. Language can be indicated in EDM XML using XML language tags. <br/> The default name for display in the portal will be derived from the preferred form whose language matches the value of the `edm:language` property (see below). Other-language versions will be used to support multilingual services as they are developed. <br/> The English language version of the preferred name must be provided for administrative purposes. |
| **Obligation & Occurrence** | Mandatory (Minimum: 1, Maximum: unbounded). There should always be a language tag.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Example**                 | “Koninklijke Bibliotheek van België”, “Bibliothèque royale de Belgique” and “Royal Library of Belgium”                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

## **Property skos:altLabel**

|                             |                                                                                                                                                              |
|:----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.w3.org/2004/02/skos/core#altLabel                                                                                                                 |
| **Label**                   | alternative name                                                                                                                                             |
| **Definition**              | Alternative forms of the name of the organization.                                                                                                           |
| **Usage**                   | Any alternative forms of the name of the organization in as many languages as can be provided. Language can be indicated in EDM XML using XML language tags. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                    |

## **Property skos:hiddenLabel**

|                             |                                                                                                                                                                        |
|:----------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.w3.org/2004/02/skos/core#hiddenLabel                                                                                                                        |
| **Label**                   | hidden name                                                                                                                                                            |
| **Definition**              | Forms of the name that should not be used for display.                                                                                                                 |
| **Usage**                   | Any forms of the name of the organization that may be useful for internal purposes but should not be displayed. The use of language tags is optional in this property. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                              |

## **Property dc:description**

|                             |                                                                                                                  |
|:----------------------------|:-----------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://purl.org/dc/elements/1.1/description                                                                      |
| **Label**                   | description                                                                                                      |
| **Definition**              | A description of the organization                                                                                |
| **Usage**                   | A description of the organization may be provided. Language can be indicated in EDM XML using XML language tags. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                        |

## **Property edm:acronym**

|                             |                                                                                                                                                                                                                                 |
|:----------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.europeana.eu/schemas/edm/acronym                                                                                                                                                                                     |
| **Label**                   | acronym                                                                                                                                                                                                                         |
| **Definition**              | The acronym (or abbreviated form of an organization’s name) that is commonly used to identify an organization                                                                                                                   |
| **Usage**                   | Acronyms should be recorded where they exist and are commonly used. They should not be created for the purpose of entering data in the Europeana system. <br/> This element can be repeated for acronyms in multiple languages. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                                                                       |
| **Example**                 | “Koninklijke Bibliotheek” is commonly abbreviated to the acronym "KB"                                                                                                                                                           |

## **Property owl:sameAs**

|                             |                                                                                                                                                                                                                                         |
|:----------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | https://www.w3.org/2002/07/owl#sameAs                                                                                                                                                                                                   |
| **Label**                   | same as                                                                                                                                                                                                                                 |
| **Definition**              | Another URI of the same organization.                                                                                                                                                                                                   |
| **Usage**                   | `owl:sameAs` is used to record the URL of the organization in the CRM system. It can also be used to point to another linked data representation of an organization, e.g. ISNI, the International Standard Name Identifier or Wikidata. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                                                                               |
| **Example**                 | <owl:sameAs rdf:resource=“http://isni.org/isni/0000000121751303”/>                                                                                                                                                                      |

## **Property edm:country**

|                             |                                                                                                                         |
|:----------------------------|:------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.europeana.eu/schemas/edm/country                                                                             |
| **Label**                   | Europeana country                                                                                                       |
| **Definition**              | The country in which the organization is based.                                                                         |
| **Usage**                   | The value must be the URI of an `edm:Place` from the Europeana Entity Collection. Only countries may be used as values. |
| **Obligation & Occurrence** | Mandatory(Minimum: 1, Maximum: 1)                                                                                       |
| **Example**                 | For Cultura Italia, the value should be “http://data.europeana.eu/place/92” (Italy).                                    |

## **Property edm:language**

|                             |                                                                                                                                                                                                                                                                                                                                                                                              |
|:----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/language                                                                                                                                                                                                                                                                                                                                                |
| **Label**                   | Europeana language                                                                                                                                                                                                                                                                                                                                                                           |
| **Definition**              | A language assigned to the resource with reference to the organization.                                                                                                                                                                                                                                                                                                                      |
| **Usage**                   | To support discovery by language a standardised ISO language code is entered in this element as part of the ingestion process. It is based on the language of the organization, and it will be used in the portal to choose the default name for display. For those countries where the preferred name exists in more than one language, this property should be repeated for each language. |
| **Obligation & Occurrence** | Mandatory(Minimum: 1, Maximum: unbounded)                                                                                                                                                                                                                                                                                                                                                    |
| **Example**                 | The ISO 639 two-letter language code “en” represents “English”                                                                                                                                                                                                                                                                                                                               |

## **Property edm:geographicScope**

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
|:----------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/geographicScope                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Label**                   | geographic scope                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Definition**              | The scope of work of the organization in terms of geographic coverage.                                                                                                                                                                                                                                                                                                                                                                                            |
| **Usage**                   | The value in this element is taken from a controlled list maintained by Europeana in the CRM. <br/><ul local-id="e432e79f-adbd-4b96-b23f-ee45f82bcc91"><li local-id="79adad08-92af-4da7-bce2-05e788ee4781"><p local-id="916ed44efca9">Regional</p></li><li local-id="9a8917da-afe8-4d87-99ae-54592b170db6"><p local-id="0fa29b2b7e8d">National</p></li><li local-id="988d2cfa-6634-4354-b994-b8dd1935a733"><p local-id="05263947c119">International</p></li></ul> |
| **Obligation & Occurrence** | Mandatory(Minimum: 1, Maximum: 1)                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Example**                 | “International” scope for the European Film Gateway. “National” scope for Cultura Italia                                                                                                                                                                                                                                                                                                                                                                          |

## **Property edm:heritageDomain**

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|:----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/heritageDomain                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Label**                   | heritage domain                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **Definition**              | The scope of work of the organization in terms of heritage categories.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **Usage**                   | The value of this element is selected from a controlled list managed by Europeana in the CRM. The available values are: <br/><ul local-id="de4eaf67-7461-4cd0-9362-a3fa84fc2939"><li local-id="7bd89cc3-7299-4564-a37c-66b350f4e5e6"><p local-id="aac91bfb513f">Cross domain</p></li><li local-id="eb55f144-dde0-41ab-bb32-26840bbf8125"><p local-id="d13195ec3235">Documentary heritage</p></li><li local-id="a487aa39-d191-4eb6-94ba-4d3bf0091ec4"><p local-id="b076d8c6c089">Bibliographic heritage</p></li><li local-id="2c821ca5-7c67-4d4b-96c8-0f0dade2431a"><p local-id="31c30d26a412">Audiovisual heritage</p></li><li local-id="0c9d49f0-8c82-4bf7-8ddb-083976949af9"><p local-id="21d5d74ca61f">Film heritage</p></li><li local-id="6d21ff00-1ee7-4de1-87e4-9bb58984c0d7"><p local-id="5e645922d1b9">Audio heritage</p></li><li local-id="e05fe80f-e59a-4ee7-87fd-8d709c330c8f"><p local-id="2976a097e3ff">Imagery heritage</p></li><li local-id="9d97ac3f-6019-4694-bbdd-964329fff479"><p local-id="a90162a822b3">Photographic heritage</p></li><li local-id="9826ee87-2e87-466d-8bde-23036545555e"><p local-id="532a32716135">Museum heritage</p></li><li local-id="0d8f7571-c813-4977-8e17-6d708c101e6b"><p local-id="97b07df544fc">Fashion heritage</p></li><li local-id="5b8fc8a7-02ee-4f55-9b9a-087461126b59"><p local-id="140f1b620fda">Musical heritage</p></li><li local-id="d6475d49-a2a4-4753-9a42-f59657488acd"><p local-id="e9c22a460164">Archeological heritage</p></li><li local-id="48c2e402-9544-47ab-8523-d45f06851ef6"><p local-id="bf865bd80e89">Architectural heritage</p></li><li local-id="293b1fe8-6e4e-486b-b681-a23110bd1dce"><p local-id="3ddefc1e094f">Natural heritage</p></li><li local-id="73f25a33-4c33-459c-ac22-4f02ffaade17"><p local-id="2bb921c01627">Scientifc heritage</p></li><li local-id="5d4362a4-1c11-4d08-a817-af2c807ec07f"><p local-id="ae4028b395e4">Jewish heritage</p></li><li local-id="76f651aa-2851-4238-acdb-1bf5ec5097df"><p local-id="ae77b8fd5302">Intanigible heritage</p></li></ul> |
| **Obligation & Occurrence** | Mandatory(Minimum: 1, Maximum: unbounded)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## **Property edm:aggregatedVia**

|                             |                                                                                                                     |
|:----------------------------|:--------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/aggregatedVia                                                                  |
| **Label**                   | has data aggregated via                                                                                             |
| **Definition**              | A relationship between an organization and another organization that aggregates its data.                           |
| **Usage**                   | An organization may provide data via several aggregators. <br/> See also the inverse property `edm:aggregatesFrom`. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                           |
| **Example**                 | Cinecittà - Luce has data aggregated by The European Film Gateway.                                                  |

## **Property foaf:logo**

|                             |                                        |
|:----------------------------|:---------------------------------------|
| **URI**                     | http://xmlns.com/foaf/0.1/logo         |
| **Label**                   | logo                                   |
| **Definition**              | A logo representing an organization.   |
| **Usage**                   | A direct link to an image is required. |
| **Obligation & Occurrence** | Recommended (Minimum: 0, Maximum: 1)   |

## **Property foaf:phone**

|                             |                                                                                                                                                                                                            |
|:----------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://xmlns.com/foaf/0.1/phone                                                                                                                                                                            |
| **Label**                   | telephone number                                                                                                                                                                                           |
| **Definition**              | A telephone number.                                                                                                                                                                                        |
| **Usage**                   | This could be the number of the switchboard or for a help/information desk for an organization or the direct line for a contact person. <br/> This should be given as the full international dialing code. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                                                  |

## **Property foaf:homepage**

|                             |                                              |
|:----------------------------|:---------------------------------------------|
| **URI**                     | http://xmlns.com/foaf/0.1/homepage           |
| **Label**                   | homepage                                     |
| **Definition**              | The URL for the homepage of the organization |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: 1)            |

## **Property foaf:depiction**

|                             |                                        |
|:----------------------------|:---------------------------------------|
| **URI**                     | http://xmlns.com/foaf/0.1/depiction    |
| **Label**                   | depiction                              |
| **Definition**              | A depiction of the organization        |
| **Usage**                   | A direct link to an image is required. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: 1)      |

## **Property vcard:hasAddress**

|                             |                                            |
|:----------------------------|:-------------------------------------------|
| **URI**                     | http://www.w3.org/2006/vcard/ns#hasAddress |
| **Label**                   | address                                    |
| **Definition**              | The physical address of the organization   |
| **Usage**                   | Links to a `vcard:Address`                 |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: 1)          |

# Properties Applicable to edm:Aggregator

## **Property edm:aggregatesFrom**

|                             |                                                                                                                      |
|:----------------------------|:---------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/aggregatesFrom                                                                  |
| **Label**                   | aggregates data from                                                                                                 |
| **Definition**              | A relationship between an aggregator and an organization whose data it aggregates.                                   |
| **Usage**                   | An aggregator may aggregate data from several organizations. <br/> See also the inverse property `edm:aggregatedBy`. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                            |
| **Example**                 | The European Film Gateway aggregates data from Cinecittà - Luce.                                                     |

## **Property edm:providesSupportForMediaType**

|                             |                                                                                                                   |
|:----------------------------|:------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/providesSupportForMediaType                                                  |
| **Label**                   | provides support for media type                                                                                   |
| **Definition**              | The type of media for which the aggregator provides support to its data providers.                                |
| **Usage**                   | Values of this property must be one of the five Europeana types (in upper case): TEXT, IMAGE, SOUND,  VIDEO or 3D |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                         |
| **Example**                 | The European Film Gateway provides support for ‘VIDEO’                                                            |

## **Property edm:providesSupportForDataActivity**

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|:----------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/providesSupportForDataActivity                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Label**                   | Provides support for data activity                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Definition**              | A data activity (metadata harvesting, metadata enrichment, quality control…) for which the aggregator provides support to its data providers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Usage**                   | The value of this element is selected from a controlled list managed by Europeana in the CRM. The available values are: <br/><ul local-id="a9ac349e-de50-4bc9-95af-919ff090cb87"><li local-id="8800649a-276e-4c32-ba38-e7c136657851"><p local-id="1ad346947c3a">Management of identifiers</p></li><li local-id="9a4254b1-56ed-4387-9cd1-85cf8b2a7d1b"><p local-id="5c1cb4975bd2">Copyright support</p></li><li local-id="ed80469f-c171-448f-a7a5-5a6dd167e2d6"><p local-id="58113079dc53">Content storage</p></li><li local-id="80a4bf1e-4e33-4c93-b0b6-c0f022e3f72e"><p local-id="9c76f2c1c14c">Content quality improvement</p></li><li local-id="c3f8c93b-14c4-4810-a666-8b6d7d56218e"><p local-id="493b855feb4a">Metadata capture</p></li><li local-id="79135d7b-3e4a-4a0a-999e-42688c526c2c"><p local-id="4c14506f45a3">Metadata storage</p></li><li local-id="c571679c-2560-4b41-8a33-83ed37e54dc2"><p local-id="72d8ed063bee">Metadata harvesting</p></li><li local-id="17af9ed9-3361-472d-9a24-7d5af1eb8bbf"><p local-id="bec51112fb37">Metadata mapping</p></li><li local-id="d2197f9e-1373-4239-b969-a60df514ebb4"><p local-id="013dbfbeb92a">Metadata validation and quality control</p></li><li local-id="29c7ae38-5c15-426f-8ea8-351733652e42"><p local-id="d8f229390220">Metadata enrichment</p></li></ul> |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

## **Property edm:providesAudienceEngagementActivity**

|                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://wwww.europeana.eu/schemas/edm/providesAudienceEngagementActivity                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Label**                   | Provides Audience Engagement Activity                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Definition**              | An audience engagement activity (newsletter, events) that the aggregator provides its data providers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Usage**                   | The value of this element is selected from a controlled list managed by Europeana in the CRM. The available values are: <br/><ul local-id="5092c373-ad76-4e69-970d-fa469efa8fb6"><li local-id="9e65aeb7-fd91-4dbc-a997-8377bf4f3900"><p local-id="d126ca705c56">Newsletters</p></li><li local-id="2060649a-227b-406e-9f24-3a68a1cfbd36"><p local-id="c9af521bc5e1">Social media engagement</p></li><li local-id="c978e8d4-7bd5-49f7-a78d-aed0ff15d9e8"><p local-id="6f8b85ef6a33">Digital curation (e.g. virtual exhibitions, thematic galleries)</p></li><li local-id="2c956aac-5430-4617-aded-ca89e73cec5b"><p local-id="0de3a96157a4">Content creation (e.g. blog posts, stories)</p></li><li local-id="44d76fd4-78cd-423b-8020-6e941c665b7b"><p local-id="22b592b3c54d">Crowdsourcing and community engagement</p></li><li local-id="e6607a05-56c0-4832-ba7c-3d7621ede4cc"><p local-id="f0f13028b61e">Collaborative projects with other organisations</p></li><li local-id="0da7449f-ce9a-4380-aaa1-c66d2602025f"><p local-id="0e37109bd2f4">Organisations of events and conferences</p></li></ul> |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

## **Property foaf:mbox**

|                             |                                                                                                                             |
|:----------------------------|:----------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://xmlns.com/foaf/0.1/mbox                                                                                              |
| **Label**                   | email                                                                                                                       |
| **Definition**              | An email address                                                                                                            |
| **Usage**                   | This could be the email address for a help/information desk for an organization or the email address of the contact person. |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                   |

# Properties Applicable to vcard:Address

## **Property vcard:street-address**

|                             |                                                                                  |
|:----------------------------|:---------------------------------------------------------------------------------|
| **URI**                     | http://www.w3.org/2006/vcard/ns#street-address                                   |
| **Label**                   | street address                                                                   |
| **Definition**              | A generic field for the street, the name of a building, the name of a department |
| **Obligation & Occurrence** | Recommended (Minimum: 0, Maximum: 1)                                             |

## **Property vcard:locality**

|                             |                                                                                                   |
|:----------------------------|:--------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.w3.org/2006/vcard/ns#locality                                                          |
| **Label**                   | locality                                                                                          |
| **Definition**              | The smallest administrative area, which is usually a town, city, ward, village or a commune, etc. |
| **Obligation & Occurrence** | Recommended (Minimum: 0, Maximum: 1)                                                              |

## **Property vcard:postal-code**

|                             |                                             |
|:----------------------------|:--------------------------------------------|
| **URI**                     | http://www.w3.org/2006/vcard/ns#postal-code |
| **Label**                   | postal code                                 |
| **Definition**              | This is the postal code.                    |
| **Obligation & Occurrence** | Recommended (Minimum: 0, Maximum: 1)        |
| **Example**                 | YO31 7PQ, 58330                             |

## **Property vcard:country-name**

|                             |                                              |
|:----------------------------|:---------------------------------------------|
| **URI**                     | http://www.w3.org/2006/vcard/ns#country-name |
| **Label**                   | country                                      |
| **Definition**              | This is the country part of the address.     |
| **Usage**                   | See also Europeana Country.                  |
| **Obligation & Occurrence** | Mandatory(Minimum: 1, Maximum: 1)            |

## **Property vcard:hasGeo**

|                             |                                                              |
|:----------------------------|:-------------------------------------------------------------|
| **URI**                     | http://www.w3.org/2006/vcard/ns#hasGeo                       |
| **Label**                   | geocoordinate                                                |
| **Definition**              | Information related to the global positioning of the object. |
| **Usage**                   | The values should instances of `vcard:Location`              |
| **Obligation & Occurrence** | Recommended (Minimum: 0, Maximum: 1)                         |

# Properties Applicable to vcard:Location

## **Property wgs84\_pos:lat**

|                             |                                              |    |
|:----------------------------|:---------------------------------------------|:---|
| **URI**                     | http://www.w3.org/2003/01/geo/wgs84\_pos#lat |    |
| **Label**                   | latitude                                     |    |
| **Definition**              | The latitude coordinate                      |    |
| **Usage**                   | The value must be in decimal degrees         |    |
| **Obligation & Occurrence** | Mandatory (Minimum: 1, Maximum: 1)           |    |

## **Property wgs84\_pos:long**

|                             |                                               |    |
|:----------------------------|:----------------------------------------------|:---|
| **URI**                     | http://www.w3.org/2003/01/geo/wgs84\_pos#long |    |
| **Label**                   | longitude                                     |    |
| **Definition**              | The longitude coordinate                      |    |
| **Usage**                   | The value must be in decimal degrees          |    |
| **Obligation & Occurrence** | Mandatory (Minimum: 1, Maximum: 1)            |    |
