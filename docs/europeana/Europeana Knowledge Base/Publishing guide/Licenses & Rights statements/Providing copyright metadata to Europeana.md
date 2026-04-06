---
tags:
  - '#copyright'
---

# Providing copyright metadata to Europeana

# Copyright metadata fields

Copyright metadata needs to be provided for every digital object submitted to Europeana and has to be mapped either to edm:rights, or, if you have created a reference to the cc:License class, to odrl:inheritFrom field, as in the example below.

<details>
<summary>cc:License class linked from the web resource</summary>

```java
<edm:WebResource rdf:about="http://www.mimo-db.eu/media/UEDIN/VIDEO/0032195v.mpg">
    <edm:rights rdf:resource="#statement_3000095353971"/>
</edm:WebResource>

<cc:License rdf:about="#statement_3000095353971">
     <odrl:inheritFrom rdf:resource="http://rightsstatements.org/vocab/NoC-NC/1.0/"/>
     <cc:deprecatedOn rdf:datatype="http://www.w3.org/2001/XMLSchema-datatypes#date">2029-06-01</cc:deprecatedOn>
</cc:License>
```

</details>

For additional copyright information dc:rights may be used. Data partners should ensure that the values in rights-related fields (dc:rights, edm:rights or odrl:inheritFrom) do not contradict each other. An example of a contradictory scenario is where edm:rights points to the Public Domain value and dc:rights contains a statement such as “*© Cultural Heritage Institution 2014*,” which indicates the object is still in copyright.

In addition, it is best practice to ensure that the copyright metadata is consistent with the information presented on the data provider’s website.

For more information on edm:rights, odrl:inheritFrom and dc:rights, consult the [EDM - Mapping guidelines](../../EDM%20-%20Mapping%20guidelines.md).

> [!IMPORTANT]
> Based on the value provided in edm:rights or odrl:inheritFrom Europeana displays a rights statement badge under the object in the portal. The badge is clickable and leads to a web page that contains information about the applicable rights.

# Copyright metadata values

Value for edm:rights or odrl:inheritFrom must be a rights statement Uniform Resource Identifier (URI) selected from the [list of available values](https://pro.europeana.eu/page/available-rights-statements).

Before providing a rights statement URI in the metadata, you may wish to double-check that your choice of rights statement is accurate and appropriate. Consult Europeana Pro for

- [information on rights statements](https://pro.europeana.eu/page/rights-statements-faq)
- [how to identify copyright in collection items](https://pro.europeana.eu/page/identifying-copyright-in-collection-items)
- and have a look at [this page](https://europeana.atlassian.net/l/c/4rxNrdSP) in the Knowledge Base

## Available values

Note that URIs you provide in the metadata must be exactly as specified here, which means that they must start with `http` and not `https`.

### 1. Creative Commons Licenses

We accept all versions with or without the relevant port that conform to this URI pattern: `http://creativecommons.org/licenses/{license-properties}/{version}/{port}/`

<details>
<summary>Available CC licenses</summary>

|                                        |                                                                      |                                                                                                                                                                                                                                                              |                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|:---------------------------------------|:---------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Available values per URI component** |                                                                      |                                                                                                                                                                                                                                                              | **Example**                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `Version`                              | `License-properties`                                                 | `Port (optional)`                                                                                                                                                                                                                                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 1.0                                    | by <br/> by-sa <br/> by-nd <br/> by-nc <br/> by-nc-sa <br/> by-nd-nc | generic (no port) \| fi \| il \| nl                                                                                                                                                                                                                          | <http://creativecommons.org/licenses/by/1.0/> <br/> <http://creativecommons.org/licenses/by-sa/1.0/fi/> <br/> <http://creativecommons.org/licenses/by-nd/1.0/il/> <br/> <http://creativecommons.org/licenses/by-nc/1.0/nl/> <br/> <http://creativecommons.org/licenses/by-nc-sa/1.0/nl/> <br/> <http://creativecommons.org/licenses/by-nd-nc/1.0/nl/>                                                                                                            |
| 2.0                                    | by <br/> by-sa <br/> by-nd <br/> by-nc <br/> by-nc-sa <br/> by-nc-nd | generic (no port) \| au \| at \| be \| br \| ca \| cl \| hr \| uk \| fr \| de \| it \| jp \| nl \| pl \| kr \| es \| tw                                                                                                                                      | [http://creativecommons.org/licenses/by/2.0/](https://creativecommons.org/licenses/by/2.0/) <br/> <http://creativecommons.org/licenses/by-sa/2.0/au/> <br/> <http://creativecommons.org/licenses/by-nd/2.0/at/> <br/> <http://creativecommons.org/licenses/by-nc/2.0/be/> <br/> <http://creativecommons.org/licenses/by-nc-sa/2.0/br/> <br/> [http://creativecommons.org/licenses/by-nc-nd/2.0/ca/](https://creativecommons.org/licenses/by-nc-nd/2.0/ca/)       |
| 2.1                                    | by <br/> by-sa <br/> by-nd <br/> by-nc <br/> by-nc-sa <br/> by-nc-nd | au \| es \| jp                                                                                                                                                                                                                                               | [http://creativecommons.org/licenses/by/2.1/au/](https://creativecommons.org/licenses/by/2.1/au/) <br/> <http://creativecommons.org/licenses/by-sa/2.1/es/> <br/> <http://creativecommons.org/licenses/by-nd/2.1/jp/> <br/> <http://creativecommons.org/licenses/by-nc/2.1/jp/> <br/> <http://creativecommons.org/licenses/by-nc-sa/2.1/jp/> <br/> [http://creativecommons.org/licenses/by-nc-nd/2.1/jp/](https://creativecommons.org/licenses/by-nc-nd/2.1/jp/) |
| 2.5                                    | by <br/> by-sa <br/> by-nd <br/> by-nc <br/> by-nc-sa <br/> by-nc-nd | generic (no port) \| ar \| au \| br \| bg \| ca \| cn \| co \| hr \| dk \| hu \| in \| il \| it \| mk \| my \| mt \| mx \| nl \| pe \| pl \| pt \| scotland \| si \| za \| es \| se \| ch \| tw                                                              | <http://creativecommons.org/licenses/by/2.5/> <br/> <http://creativecommons.org/licenses/by-sa/2.5/ar/> <br/> <http://creativecommons.org/licenses/by-nd/2.5/au/> <br/> <http://creativecommons.org/licenses/by-nc/2.5/br/> <br/> <http://creativecommons.org/licenses/by-nc-sa/2.5/bg/> <br/> <http://creativecommons.org/licenses/by-nc-nd/2.5/ca/>                                                                                                            |
| 3.0                                    | by <br/> by-sa <br/> by-nd <br/> by-nc <br/> by-nc-sa <br/> by-nc-nd | generic (no port) \| au \| at \| br \| cl \| cn \| cr \| hr \| cz \| ec \| eg \| ee \| fr \| de \| gr \| gt \| hk \| igo \| ie \| it \| lu \| nl \| nz \| no \| ph \| pl \| pt \| pr \| ro \| rs \| sg \| za \| es \| ch \| tw \| th \| ug \| us \| ve \| vn | <http://creativecommons.org/licenses/by/3.0/> <br/> <http://creativecommons.org/licenses/by-sa/3.0/au/> <br/> <http://creativecommons.org/licenses/by-nd/3.0/at/> <br/> <http://creativecommons.org/licenses/by-nc/3.0/br/> <br/> <http://creativecommons.org/licenses/by-nc-sa/3.0/cl/> <br/> <http://creativecommons.org/licenses/by-nc-nd/3.0/cn/>                                                                                                            |
| 4.0                                    | by <br/> by-sa <br/> by-nd <br/> by-nc <br/> by-nc-sa <br/> by-nc-nd | Version 4.0 discourages using ported versions and instead acts as a single global license <br/>  <br/>                                                                                                                                                       | <http://creativecommons.org/licenses/by/4.0/> <br/> <http://creativecommons.org/licenses/by-sa/4.0/> <br/> <http://creativecommons.org/licenses/by-nd/4.0/> <br/> <http://creativecommons.org/licenses/by-nc/4.0/> <br/> <http://creativecommons.org/licenses/by-nc-sa/4.0/> <br/> <http://creativecommons.org/licenses/by-nc-nd/4.0/>                                                                                                                           |

</details>

### 2. Rights Statements provided by RightsStatements.org

We accept 1.0 version that conforms to this URI pattern: `http://rightsstatements.org/vocab/{statement-identifier}/1.0/`

<details>
<summary>Available Rights Statements</summary>

| **Available values per URI component**   | **Example**                                        |  **Additional requirements**                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|:-----------------------------------------|:---------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Statement-identifier`                   |                                                    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| NoC-NC                                   | <http://rightsstatements.org/vocab/NoC-NC/1.0/>    | In order to support the correct implementation of this statement, a data provider must be able to supply to Europeana a copy of the contract that specifies the restrictions on the commercial use. <br/> If such information is publicly available, the data partner must also specify a year of expiration in <cc:deprecatedOn> (part of cc:License class) to indicate the first calendar year in which the digital object(s) can be used by third parties without restrictions on commercial use. |
| NoC-OKLR                                 | <http://rightsstatements.org/vocab/NoC-OKLR/1.0/>  | In order to support the correct implementation of this statement, a data provider must communicate to Europeana the legal restriction that applies to the reuse.                                                                                                                                                                                                                                                                                                                                     |
| InC                                      | <http://rightsstatements.org/vocab/InC/1.0/>       |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| InC-EDU                                  | <http://rightsstatements.org/vocab/InC-EDU/1.0/>   |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| InC-EU-OW                                | <http://rightsstatements.org/vocab/InC-OW-EU/1.0/> | In order to support the correct implementation of this statement, a data provider must make sure that the object is registered in the [EU Orphan Works Database](https://euipo.europa.eu/ohimportal/en/web/observatory/orphan-works-db).                                                                                                                                                                                                                                                             |
| CNE                                      | <http://rightsstatements.org/vocab/CNE/1.0/>       | Data provider must consult with Europeana before using this statement.                                                                                                                                                                                                                                                                                                                                                                                                                               |

</details>

### **3. Creative Commons Public Domain Tools**

We accept 1.0 version that conforms to this URI pattern: `http://creativecommons.org/publicdomain/{public-domain-tool}/1.0/`

<details>
<summary>Available CC public domain tools</summary>

| **Available values per URI component**   | **Example**                                         |
|:-----------------------------------------|:----------------------------------------------------|
| `Public-domain-tool`                     |                                                     |
| zero                                     | <http://creativecommons.org/publicdomain/zero/1.0/> |
| mark                                     | <http://creativecommons.org/publicdomain/mark/1.0/> |

</details>
