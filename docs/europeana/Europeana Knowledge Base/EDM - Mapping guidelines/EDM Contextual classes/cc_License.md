---
tags:
  - '#cc-license'
---

[EDM - Mapping guidelines](../../EDM%20-%20Mapping%20guidelines.md) > [EDM Contextual classes](../EDM%20Contextual%20classes.md)

# cc:License

> [!IMPORTANT]
> - The **mandatory property** is marked in **dark blue**
> - The **optional properties** are left in **black**.
>
> Please provide the properties in the record in the **same order** given in this document, the metadata validation performed by Europeana requires this order.

- [odrl:inheritFrom](#odrl-inheritfrom)
- [cc:deprecatedOn](#cc-deprecatedon)

|                  |                                                                                                                                                                                                                                                                                                                             |                                       |                 |
|:-----------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------|:----------------|
| **Property**     | **Description**                                                                                                                                                                                                                                                                                                             | **Value** **type**                    | **Cardinality** |
| odrl:inheritFrom | ID of a base rights statement from which the described License is derived. This value must come for alist of statements controlled by Europeana. `<odrl:inheritFrom rdf:resource="http://rightsstatements.org/vocab/NoC-­NC/1.0/"/>`                                                                                        | ref                                   | 1....1          |
| cc:deprecatedOn  | The date that the license expires, as it has been described, which implies among other things the expiration of the restrictions specified by the license. `<cc:deprecatedOn rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2029‐06-­01</cc:deprecatedOn>` <br/> Note this datatype is mandatory for cc:deprecatedOn. | Literal expressed as an XML date type | 0....1          |

cc:License is a new class in EDM so it does not appear in the example MIMO data shown in the annexes. An example is given here instead.  
In the metadata for the edm:WebResource there will be an edm:rights statement with the identifier of the cc:License class. This will form the link to the cc:License resource.

```java
<edm:WebResource rdf:about="http://www.mimo-­‐db.eu/media/UEDIN/VIDEO/0032195v.mpg">
    <edm:rights rdf:resource="#statement_3000095353971"/>
</edm:WebResource>
...
<cc:License rdf:about="#statement_3000095353971"/>
    <odrl:inheritFrom rdf:resource=“http://rightsstatements.org/vocab/NoC-­‐NC/1.0/”/>
    <cc:deprecatedOn rdf:datatype=”http://www.w3.org/2001/XMLSchema-­‐datatypes#date”>2029-­06-­01 </cc:deprecatedOn>
</cc:License>
```
