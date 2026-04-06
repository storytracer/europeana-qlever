
# PID scheme registry

Ensuring that identifiers provided using the property edm:pid are truly persistent is crucial. To support this, we created the PID scheme registry, which lists all PID schemes currently recognised as valid according to our [Policy for persistent identifiers in the data space](../../../Persistent%20identifiers/Policy%20for%20persistent%20identifiers%20in%20the%20data%20space.md):

- [Handle System](#handle-system)
- [Digital Object Identifier (DOI)](#digital-object-identifier-doi)
- [NBN (National Bibliography Number)](#nbn-national-bibliography-number)
  - [Austria, AT](#austria-at)
  - [Switzerland, CH](#switzerland-ch)
  - [Czechia, CZ](#czechia-cz)
  - [Germany, DE](#germany-de)
  - [Finland, FI](#finland-fi)
  - [Hungary, HR](#hungary-hr)
  - [Italy, IT](#italy-it)
  - [Netherlands, NL](#netherlands-nl)
  - [Norway, NO](#norway-no)
  - [Sweden, SE](#sweden-se)
  - [Slovenia, SI](#slovenia-si)
  - [Slovakia, SK](#slovakia-sk)
- [Archival Resource Key (ARK)](#archival-resource-key-ark)
- [Persistent Uniform Resource Locator (PURL)](#persistent-uniform-resource-locator-purl)
  - [PURL.org](#purl-org)
  - [PURL.pt](#purl-pt)
  - [PURL.gov](#purl-gov)

> [!WARNING]
> We are working on the publication of the registry. For this reason, the entry URIs are not yet resolvable. In the meantime, you can access their [source in github](https://github.com/europeana/data-europeana-gateway/tree/pid_schemes/public/scheme/pid).

### **Handle System**

A <http://Handle.Net> (HNR) identifier, or "handle" is a persistent, unique identifier for digital objects and other network resources, used to store and resolve the metadata needed to locate, access, and manage them over time. It uses a distributed system with servers called Handle Servers to resolve these identifiers. A handle consists of a prefix identifying a naming authority and a locally unique suffix, ensuring global uniqueness and long-term persistence despite changes to the resource's location or state. The Handle was initially developed by the [Corporation for National Research Initiatives (CNRI)](https://www.cnri.reston.va.us/about_cnri.html) which is now responsible for assigning prefixes to users of the system under the authority of the [DONA Foundation](https://dona.net/).

Syntax: `hdl:10.<AGENCY_ID>/<LOCAL_ID>`

See registry entry: <http://data.europeana.eu/scheme/pid/handle>

### Digital Object Identifier (DOI)

A [Digital Object Identifier (DOI)](https://www.doi.org/) is a persistent identifier based on the Handle System used to uniquely identify academic, professional, and government information, such as journal articles, research reports, data sets, and official publications, standardised by the [International Organization for Standardization](https://en.wikipedia.org/wiki/International_Organization_for_Standardization) (ISO). The DOI system uses the Handle System technology to update metadata and maintain access, making research output more FAIR (Findable, Accessible, Interoperable, and Re-usable). The developer and administrator of the DOI system is the International DOI Foundation (IDF). Organisations that meet the contractual obligations of the DOI system and are willing to pay to become a member of the system can assign DOIs.[^ ]The DOI system is implemented through a federation of registration agencies coordinated by the IDF.

Syntax: `info:doi/10.<AGENCY_ID>/<LOCAL_ID>`

See registry entry: <http://data.europeana.eu/scheme/pid/doi>

### NBN (National Bibliography Number)

NBN is a persistent, URN-based identifier defined in [RFC 8458](https://datatracker.ietf.org/doc/rfc8458/) used by national libraries to uniquely identify documents within their country's national bibliography, particularly those without a publisher-assigned identifier. Countries that implement NBN use unique country-specific formats, with examples including Germany, the Netherlands and Italy, ensuring long-term access and preservation of a nation's intellectual and cultural output.

Syntax: `URN:NBN:<ISO_COUNTRY_CODE>-<LOCAL_ID>`

The following NBNs are presently recognised:

> [!WARNING]
> Our acceptance of the `URN:NBN` namespace as PIDs for some countries is still under review due to concerns about its reliability as a persistent identifier. As a result, some namespaces may be removed from the registry in the short term.

|                     |                                       |                                              |
|:--------------------|:--------------------------------------|:---------------------------------------------|
| **Country**         | **Example**                           | **Entry in the registry**                    |
| **Austria, AT**     | `URN:NBN:AT:at-ubi:2-3870`            | <http://data.europeana.eu/scheme/pid/nbn:at> |
| **Switzerland, CH** | `URN:NBN:CH:serval-BIB_D3B827073C8A5` | <http://data.europeana.eu/scheme/pid/nbn:ch> |
| **Czechia, CZ**     | `URN:NBN:CZ:aba008-0001h8`            | <http://data.europeana.eu/scheme/pid/nbn:cz> |
| **Germany, DE**     | `URN:NBN:DE:bvb:12-bsb10021405-1`     | <http://data.europeana.eu/scheme/pid/nbn:de> |
| **Finland, FI**     | `URN:NBN:fi-fd2010-00003246`          | <http://data.europeana.eu/scheme/pid/nbn:fi> |
| **Hungary, HR**     | `URN:NBN:HR:188:496570`               | <http://data.europeana.eu/scheme/pid/nbn:hr> |
| **Italy, IT**       | `URN:NBN:IT:unibo-26106`              | <http://data.europeana.eu/scheme/pid/nbn:it> |
| **Netherlands, NL** | `URN:NBN;NL:kb-1755074163456`         | <http://data.europeana.eu/scheme/pid/nbn:nl> |
| **Norway, NO**      | `URN:NBN:no-nb_digimanus_154024`      | <http://data.europeana.eu/scheme/pid/nbn:no> |
| **Sweden, SE**      | `URN:NBN:SE:su:diva-42116`            | <http://data.europeana.eu/scheme/pid/nbn:se> |
| **Slovenia, SI**    | `URN:NBN:SI:DOC-DUX30CEW`             | <http://data.europeana.eu/scheme/pid/nbn:si> |
| **Slovakia, SK**    | `URN:NBN:SK:cair-ko1j79z`             | <http://data.europeana.eu/scheme/pid/nbn:sk> |

### **Archival Resource Key (ARK)**

The Archival Resource Key is a persistent, non-paywalled, decentralised identifier for any information object, providing stable links to digital, physical, or abstract resources like scholarly works, datasets, and artefacts. It's a URL scheme that uses a resolver, such as <http://n2t.net>, to find a resource by including a Name Assigning Authority Number (NAAN) and a local name. They are maintained by the <https://arks.org/>, an open global community supporting the ARK infrastructure on behalf of research and scholarship.

Syntax: `ark:/<NAAN>/<Name>/<SubPart>.<Variants>`

See registry entry: <http://data.europeana.eu/scheme/pid/ark>

### Persistent Uniform Resource Locator (PURL)

A persistent URL (also known as permalinks), is a long-lived URL that acts as a stable, permanent identifier for an online resource, even if the resource's actual location on the web changes. It works by creating a layer of indirection through a resolver service, which redirects the PURL to the resource's current address, ensuring that links don't break and references remain consistent over time. The oldest PURL system was operated by OCLC and since 2006 the resolver service and its administration interface has been transfered to the Internet Archive. Since OCLC’s PURL system has been developed other similar services have emerged, some being restricted to one organisation while others like [PURL.org](http://PURL.org) being publicly available to anyone.

#### [PURL.org](https://purl.archive.org/)

Was developed by OCLC and is now mainted by the Internet Archive. It is an open initiative allowing any party to register a domain within the purl namespace and indicate the target location (URL) where requests should be redirected to.

See registry entry: <http://data.europeana.eu/scheme/pid/purl:org>

#### [PURL.pt](https://opendata.bnportugal.gov.pt/ids_persistentes.htm)

Was developed by the [National Library of Portugal (BNP)](https://www.bnportugal.gov.pt/) in conjunction with the creation of its Digital Library ([Biblioteca Nacional Digital – BND](https://bndigital.bnportugal.gov.pt/)) in January 2002, to provide persistent identifiers for all digital resources made available to the public.

See registry entry: <http://data.europeana.eu/scheme/pid/purl:pt>

#### [PURL.gov](https://purl.access.gpo.gov/)

Was developed by the U.S. Government Publishing Office (GPO) for the Federal Depository Library Program (FDLP) to provide reliable and persistent access to government information for the public.

See registry entry: <http://data.europeana.eu/scheme/pid/purl:gov>
