
# Persistent identifiers in EDM (definitions)

This page defines the classes and associated properties that are part of the **EDM profile for persistent identifiers**. The profile outlines how [Glossary of terms](../../Persistent%20identifiers/Glossary%20of%20terms.md) can be explicitly represented in EDM metadata. It is motivated by the [Policy for persistent identifiers in the data space for cultural heritage](https://europeana.atlassian.net/wiki/x/A4Clwg), which sets out the vision and terminology behind the profile.

**Table of contents:**

- [Property edm:equivalentPID](#property-edm-equivalentpid)
- [Property edm:hasURL](#property-edm-hasurl)
- [Property edm:pid](#property-edm-pid)
- [Property edm:replacesPID](#property-edm-replacespid)
- [Class edm:PersistentIdentifier](#class-edm-persistentidentifier)
  - [rdf:value](#rdf-value)
  - [skos:notation](#skos-notation)
  - [edm:hasURL](#edm-hasurl)
  - [dcterms:created](#dcterms-created)
  - [dcterms:creator](#dcterms-creator)
  - [odrl:hasPolicy](#odrl-haspolicy)
  - [skos:inScheme](#skos-inscheme)
  - [edm:equivalentPID](#edm-equivalentpid)
  - [edm:replacesPID](#edm-replacespid)
- [Class edm:PersistentIdentifierScheme](#class-edm-persistentidentifierscheme)
  - [dcterms:title](#dcterms-title)

> [!TIP]
> Data providers can see these elements in action for their case in the [EDM Mapping Guidelines section](https://europeana.atlassian.net/wiki/x/BQC7ww).

![EDM Persistent Identifiers PID profile -20260107-114813.png](https://europeana.atlassian.net/wiki/download/attachments/3283812410/EDM%20Persistent%20Identifiers%20PID%20profile%20-20260107-114813.png?version=1&modificationDate=1767786514814&cacheVersion=1&api=v2)

## **Property** edm:equivalentPID

|                             |                                                                                                                                                                          |
|:----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.europeana.eu/schemas/edm/equivalentPID                                                                                                                        |
| **Label**                   | equivalent persistent identifier                                                                                                                                         |
| **Definition**              | A PID from another PID Scheme that identifies the same resource.                                                                                                         |
| **Domain**                  | edm:PersistentIdentifier                                                                                                                                                 |
| **Range**                   | Union of rdfs:Literal and edm:PersistentIdentifier. <br/> When the value is a literal, the PID should be in the canonical form.                                          |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                |
| **Example**                 | ```java<br/><edm:PersistentIdentifier about="..."> <br/>  <edm:equivalentPID>ark:/12345/cb12r31f44g</edm:equivalentPID><br/>  …<br/></edm:PersistentIdentifier> <br/>``` |

## **Property** edm:hasURL

|                             |                                                                                                                                                                                    |
|:----------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.europeana.eu/schemas/edm/hasURL                                                                                                                                         |
| **Label**                   | has URL                                                                                                                                                                            |
| **Definition**              | A URL representation of the PID that can be used for resolving the PID. In some PID schemes, the URL form may be the canonical form.                                               |
| **Domain**                  | edm:PersistentIdentifier                                                                                                                                                           |
| **Range**                   | rdfs:Resource                                                                                                                                                                      |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                          |
| **Example**                 | ```java<br/><edm:PersistentIdentifier about="..."> <br/>    <edm:hasURL rdf:resource=”https://n2t.net/ark:/12345/cb12r31f44g”/><br/>    …<br/></edm:PersistentIdentifier> <br/>``` |

## **Property** edm:pid

|                             |                                                                                                                                        |
|:----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.europeana.eu/schemas/edm/pid                                                                                                |
| **Label**                   | persistent identifier                                                                                                                  |
| **Definition**              | A long-lasting identifier for the resource.                                                                                            |
| **Domain**                  | Union of edm:ProvidedCHO, edm:WebResource, edm:Agent, edm:Place, skos:Concept, edm:TimeSpan, and ore:Proxy.                            |
| **Range**                   | Union of rdfs:Literal and edm:PersistentIdentifier                                                                                     |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                              |
| **Example**                 | ```java<br/><edm:ProvidedCHO about="..."> <br/>    <edm:pid>ark:/12148/cb12031244g</edm:pid><br/>    …<br/></edm:ProvidedCHO> <br/>``` |

## **Property** edm:replacesPID

|                             |                                                                                                                                                                          |
|:----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**                     | http://www.europeana.eu/schemas/edm/replacesPID                                                                                                                          |
| **Label**                   | replaces persistent identifier                                                                                                                                           |
| **Definition**              | A PID from the same PID Scheme that identifies the same resource but  has been deprecated in favor of this PID.                                                          |
| **Domain**                  | edm:PersistentIdentifier                                                                                                                                                 |
| **Range**                   | A string literal with the canonical form of the PID.                                                                                                                     |
| **Obligation & Occurrence** | Optional (Minimum: 0, Maximum: unbounded)                                                                                                                                |
| **Example**                 | ```java<br/><edm:PersistentIdentifier about="..."> <br/>    <edm:replacesPID>ark:/12345/cb12r31f44g</edm:replacesPID><br/>    …<br/></edm:PersistentIdentifier> <br/>``` |

## **Class** edm:PersistentIdentifier

|                |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **URI**        | http://www.europeana.eu/schemas/edm/PersistentIdentifier                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Label**      | Persistent Identifier Resource                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Definition** | Resource that enables the further description of a PID and its representation(s).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **Usage note** | The PID must not be used as the URI of the edm:PersistentIdentifier resource, since the PID should be used in the URI of the identified resource. The PID must be represented in the rdf:value or skos:notation property of the edm:PersistentIdentifier. <br/> edm:PersistentIdentifier resources may be blank nodes (i.e. inline nodes without an identifier). If the edm:PersistentIdentifier resource has a URI, then it must not be the PID itself because the edm:PersistentIdentifier represents the metadata record of the PID, not the resource that is identified by the PID. <br/> Note that in some PID schemes, a PID record may hold metadata about the referent. This is not the case of edm:PersistentIdentifier, which is intended for holding only technical and administrative metadata about the PID. |

<details>
<summary>All properties for edm:PersistentIdentifier</summary>

|                       |                                                                                    |           |                                                                                                                                                                                                                                          |
|:----------------------|:-----------------------------------------------------------------------------------|:----------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Property**          | **Range**                                                                          | **Card.** | **Usage note**                                                                                                                                                                                                                           |
| **rdf:value**         | Literal                                                                            | `1..1`    | The canonical form of the PID                                                                                                                                                                                                            |
| **skos:notation**     | Literal                                                                            | `0..*`    | Other representation of the PID. Although by convention skos:notation is used with a rdf:datatype, in this case the indication of a datatype is not recommended because the PID scheme is indicated by using the skos:inScheme property. |
| **edm:hasURL**        | Reference                                                                          | `0..*`    | A URL representation of the PID that can be used for resolving the PID. In some PID schemes, the URL form may be the canonical form.                                                                                                     |
| **dcterms:created**   | Literal                                                                            | `0..1`    | Date of creation of the PID. The value must be a Literal, expressed as xsd:date or xsd:dateTime .                                                                                                                                        |
| **dcterms:creator**   | Literal or [Reference](https://pro.europeana.eu/page/intro#reference) to edm:Agent | `0..1`    | The entity responsible for the creation (or assignment) and maintenance of the PID. For literal values, the use of language tags is optional in this property.                                                                           |
| **odrl:hasPolicy**    | Reference                                                                          | `0..1`    | A reference to the PID policy from the creator/maintainer of the PID                                                                                                                                                                     |
| **skos:inScheme**     | Reference                                                                          | `0..1`    | The PID scheme of the PID                                                                                                                                                                                                                |
| **edm:equivalentPID** | Literal                                                                            | `0..*`    | A PID from another PID Scheme that identifies the same resource. When the value is a Literal, the PID should be in the canonical form.                                                                                                   |
| **edm:replacesPID**   | Literal                                                                            | `0..*`    | A PID from the same PID Scheme that identifies the same resource but  has been deprecated in favor of this PID. The value must be in the canonical form.                                                                                 |

</details>

## **Class** edm:PersistentIdentifierScheme

|                 |                                                                                                     |
|:----------------|:----------------------------------------------------------------------------------------------------|
| **URI**         | http://www.europeana.eu/schemas/edm/PersistentIdentifierScheme                                      |
| **Label**       | Persistent Identifier Scheme                                                                        |
| **Definition**  | A comprehensive set of standards defining various aspects of PIDs, such as their format and syntax. |
| **Subclass of** | skos:ConceptScheme                                                                                  |

<details>
<summary>All properties for edm:PersistentIdentifierScheme</summary>

|               |           |           |                             |
|:--------------|:----------|:----------|:----------------------------|
| **Property**  | **Range** | **Card.** | **Usage note**              |
| dcterms:title | Literal   | `0..*`    | The name of the PID scheme. |

</details>
