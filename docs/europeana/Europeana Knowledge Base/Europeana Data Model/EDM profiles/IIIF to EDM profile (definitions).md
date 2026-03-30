---
tags:
  - '#edm'
  - '#iiif-properties'
  - '#iiif'
  - '#iiiif-classes'
---

[Europeana Data Model](../../Europeana%20Data%20Model.md) > [EDM profiles](../EDM%20profiles.md)

# IIIF to EDM profile (definitions)

This page defines the classes and associated properties that are part of the IIIF to EDM profile. In EDM, IIIF resources representing a cultural object are modelled as instances of the edm:WebResource class, like many other digital representations.

> [!NOTE]
> Note: Some of the properties already covered in the [basic EDM Definitions](https://europeana.atlassian.net/wiki/x/EQDOsQ) (edm:isShownBy, edm:hasView, edm:object) are excluded from this section.

**Table of contents:**

- [Overview](#overview)
- [Classes](#classes)
  - [svcs:Service](#svcs-service)
- [Properties](#properties)
  - [dcterms:conformsTo](#dcterms-conformsto)
  - [doap:implements](#doap-implements)
  - [svcs:has\_service](#svcs-has-service)
  - [dcterms:isReferencedBy](#dcterms-isreferencedby)

# Overview

Below is an overview of classes and properties for the IIIF to EDM profile:

![](../../../attachments/4399c172-09bd-4b07-b1b4-4661bdaa5c1b.jpg)

# **Classes**

## svcs:Service

|            |                                                                                                                                                                                  |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URI        | [http://rdfs.org/sioc/services#](http://rdfs.org/sioc/services#Service)                                                                                                          |
| Label      | Service                                                                                                                                                                          |
| Definition | A Service is web service associated with a Site or part of it. The `svcs:Service` class is used to declare (and provide information to) the service used to consume the Resource |
| Example    | `<svcs:Service rdf:about="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/f1"/>`                                                                                           |

# **Properties**

## **dcterms:conformsTo**

|             |                                                                                                                                                                                                                                                                    |
|:------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URI         | `http://purl.org/dc/terms/conformsTo`                                                                                                                                                                                                                              |
| Label       | ConformsTo                                                                                                                                                                                                                                                         |
| Definition  | An established standard to which the web resource or service conforms. W3C WCAG 2.0 (web content accessibility guidelines). If the Service describes a IIIF resource, dcterms:conformsTo must be used to describe the IIIF protocol the resource is conforming to. |
| Domain      | svcs:Service                                                                                                                                                                                                                                                       |
| Subproperty | dc:relation                                                                                                                                                                                                                                                        |
| Occurence   | Mandatory (Minimum: 1, Maximum: unbounded) For IIIF Image API services, the value of this property must be `http://iiif.io/api/image`                                                                                                                              |
| Example     | `<dcterms:conformsTo rdf:resource="http://iiif.io/api/image"/>`                                                                                                                                                                                                    |

## **doap:implements**

|            |                                                                                                                                                                                        |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URI        | `http://usefulinc.com/ns/doap#`                                                                                                                                                        |
| Label      | Implements                                                                                                                                                                             |
| Definition | A specification that a project implements. Could be a standard, API or legally defined level of conformance. In IIIF `doap:implements` refers to the the protocol implemented in IIIF. |
| Domain     | svcs:Service                                                                                                                                                                           |
| Occurrence | Optional (Minimum: 0, Maximum: 1)                                                                                                                                                      |
| Example    | `<doap:implements rdf:resource="http://iiif.io/api/image/2/level1.json"/>`                                                                                                             |

## **svcs:has\_service**

|            |                                                                                                    |
|:-----------|:---------------------------------------------------------------------------------------------------|
| URI        | `http://rdfs.org/sioc/services#`                                                                   |
| Label      | HasService                                                                                         |
| Definition | The identifier of the `svcs:Service` required to consume the edm:WebResource.                      |
| Domain     | edm:WebResource                                                                                    |
| Occurence  | Optional (Minimum: 0, Maximum: unbounded) <br/> This property is mandatory for IIIF web resources. |
| Example    | `<svcs:has_service rdf:resource="http://www.example.org/Service/IIIF">`                            |

## dcterms:isReferencedBy

|             |                                                                                                                                                                                               |
|:------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URI         | `http://purl.org/dc/terms/isReferencedBy`                                                                                                                                                     |
| Label       | IsReferencedBy                                                                                                                                                                                |
| Definition  | A related resource that references, cites, or otherwise points to the described resource. In IIIF, `dcterms:isReferencedBy` can be used to connect an edm:WebResource to a IIIF manifest URI. |
| Domain      | `edm:WebResource`                                                                                                                                                                             |
| Subproperty | `dc:relation`                                                                                                                                                                                 |
| Occurence   | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                                     |
| Example     | `<dcterms:isReferencedBy rdf:resource="https://gallica.bnf.fr/iiif/ark:/12148/btv1b55001425m/manifest.json"/>`                                                                                |
