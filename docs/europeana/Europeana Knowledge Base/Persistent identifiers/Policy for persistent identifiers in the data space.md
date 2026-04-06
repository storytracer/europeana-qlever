
# Policy for persistent identifiers in the data space

> [!NOTE]
> **Note on versioning:** The first version of the policy, containing 20 principles, was published on Europeana Pro in December 2024: [Policy for persistent identifiers in the data space](https://pro.europeana.eu/post/policy-for-persistent-identifiers-in-the-data-space). The version presented on this page is an extended edition of the original policy. It contains the same 20 principles, now accompanied by explanations to support their practical application.

- [Introduction](#introduction)
- [Purpose](#purpose)
- [Principles](#principles)
  - [1. Characteristics of a PID](#key-1-characteristics-of-a-pid)
  - [2. Assigning PIDs to resources and managing change](#key-2-assigning-pids-to-resources-and-managing-change)
  - [3. Dissemination, use and interoperability of PIDS](#key-3-dissemination-use-and-interoperability-of-pids)
  - [4. Sustainability and governance of PIDs](#key-4-sustainability-and-governance-of-pids)
- [References](#references)

# Introduction

When different organisations use different identifiers for the same cultural heritage resource, or even within the same organisation, different identifiers are employed over time, this results in challenges when attempting to unambiguously identify and locate the resource and its associated information. URLs pointing to resources are vulnerable to becoming broken or inaccessible, leading to link rot, which disrupts all forms of (re)use and negatively impacts traffic towards the organisation’s website as well as its SEO ranking among search engines. Using persistent identifiers to provide stable references to resources is a crucial step towards ensuring reliable identification, location and access. Persistent identification plays a vital role in enhancing the reuse of cultural heritage resources by providing more change resistant and citable identifiers that facilitate discovery and proper attribution.

The adoption of persistent identifiers by cultural heritage institutions with digital collections shows commitment towards interoperability and data access that in turn builds trust in the institution and the data it creates. This practice supports the dissemination and reuse of cultural heritage objects across academic, cultural, scientific, and commercial domains, helping to make them more accessible to audiences across the data spaces and contributing to the broader goals of knowledge exchange and innovation.

> [!IMPORTANT]
> **Definition:** Persistent identifier (PID) is an association between a sequence of characters and a specific resource. The term “persistent” refers to the identifier’s role in ensuring continued access to the resource and the data associated with it for the foreseeable future. Organisations identifying resources can implement in-house PID solutions, or rely on existing PID service providers. Some of the most commonly used PIDs systems are [Archival Resource Key (ARK)](https://arks.org/about/), [Digital Object Identifier (DOI)](https://www.doi.org/), [National Bibliography Numbers (NBN)](https://www.ifla.org/references/best-practice-for-national-bibliographic-agencies-in-a-digital-age/resource-description-and-standards/identifiers/national-bibliography-number-nbn/), [Persistent Identifiers for eResearch (ePIC)](https://www.pidconsortium.net/).

> [!IMPORTANT]
> For definitions of terms used in the policy, please refer to the [Glossary of Terms](https://europeana.atlassian.net/wiki/x/XoC2ww).

# Purpose

This document is intended for participants in the European data space for cultural heritage, especially data partners that are assigning identifiers to resources being shared in the data space.

The persistence of identifiers relies on a combination of technological and organisational endeavours. It depends on (technical) services built around them and ongoing commitment to sustainability from operators of PID systems or infrastructures. At the same time it is equally important for organisations or individuals overseeing PID implementation and its management to demonstrate responsibility and commitment.

In the context of the data space, it is worthwhile acknowledging that collaborating with various stakeholders whose identification practices and infrastructures are not entirely within the data space steward’s control, entails a level of uncertainty. To ensure better trustworthiness of the data space, this policy establishes clear expectations for data partners seeking to implement and contribute (P)IDs. Their identifiers will be acknowledged as persistent as long as they adhere to the principles outlined in this document and demonstrate compliance through transparent documentation of their approaches in their own institutional policies, which are understood as an important indicator of institution’s commitment to PID implementation and its continuous administration. At the same time, being able to develop an understanding of the procedures and workflows implemented by data partners is crucial for the data space steward and other stakeholders, as it enables the mitigation of potential risks and, ultimately, enhances the trustworthiness of the PIDs available in the data space.

# Principles

## 1. Characteristics of a PID

### P1: A PID is **a URI that follows a formally defined and recognisable identifier scheme capable of supporting an identification space large enough to accommodate existing and future needs.**

<details>
<summary>Explanation</summary>

A PID is a URI built upon a clear and formalised structure or scheme. This scheme ensures that a PID is recognisable, meaning that it follows specific rules that make it easy for users to identify the type of PID it is (for example ARK, DOI, NBN, etc.). Such a scheme must also be capable of handling a large number of identifiers without collision or loss of uniqueness.

For example, consider the ARK identifier for the artwork “Mona Lisa”: `ark:/53355/cl010066723`*.* It follows the ARK syntax: `ark:/NAAN/Name`, where the Name Assigning Authority Number (NAAN) uniquely identifies the organisation that assigned the PID, followed by the Name, which is a local identifier for the resource. Because the ARK scheme is formally defined and widely recognised, many unique identifiers can be created without conflicts.

</details>

### P2: **A PID is as opaque as possible, meaning that it contains the least information possible about the resource it identifies.**

<details>
<summary>Explanation</summary>

An important consideration when generating PIDs is to pay attention to structures that are vulnerable to semantic rot, that is, the risk that identifiers become outdated or misleading because they refer to a certain perception, nature or provenance of a resource that may change over time. For example, including the name of an organisation, resource or department in a PID may seem helpful, but if any of those elements change, the identifier may also be more likely to change, undermining its persistence.

Take the ARK identifier for the artwork “Mona Lisa”: `ark:/53355/cl010066723` as an example. It is opaque: strings `53355` and `cl010066723` contain no embedded meaning about the institution or resource. Because it avoids semantically meaningful elements, the PID is more likely to stay stable over time, even if, for instance, “Mona Lisa” was renamed. Opaqueness can help to ensure that the identifier remains consistent over time, regardless of any changes to the resource or its context.

</details>

### P3: **A PID is unique, meaning that it identifies only one resource, it is not reused to identify other resources, and no other PID exists within its identifier scheme for the same resource.**

<details>
<summary>Explanation</summary>

A PID refers to one specific resource and is never reused for anything else. To make this possible on a global scale, PID schemes follow agreed structures and rules that ensure identifiers are unique and managed consistently. These structures are managed by recognised authorities, helping to prevent two different resources from accidentally receiving the same identifier or the same resource from being assigned more than one PID within the same scheme.

For example, the ARK identifier `ark:/53355/cl010066723` uniquely refers to the artwork “Mona Lisa”. The number `53355` is assigned to the holding organisation - “Louvre” and only Louvre can create ARK identifiers within this namespace. This kind of system ensures that each PID is not only unique within an organisation, but also remains globally distinct across organisations.

</details>

### **P4: A PID is persistent, meaning it is never changed, nor deleted.**

<details>
<summary>Explanation</summary>

A PID purpose is to provide a permanent and stable reference to a specific resource. This means the identifier must remain unchanged and always resolve to the same resource.

For example, `ark:/53355/cl010066723` is an immutable identifier for the artwork “Mona Lisa”. Even if the “Mona Lisa” is digitised again, reclassified or moved to a different system, this ARK PID must remain exactly the same and continue to refer to the “Mona Lisa” artwork. It must never be reassigned to a different painting or resource. To ensure this long-term reliability, organisations must plan for the ongoing management of their identifiers, especially during internal changes such as restructuring, leadership turnover, or technology transitions, to ensure that PIDs remain actionable and accurate in the future.

PIDs themselves should never be deleted, even if the underlying resource no longer exists. Deleting a PID would break any references or citations that rely on it and would violate the promise that each PID provides a stable and permanent reference. In such cases, or whenever deletion might be considered, organisations should follow the guidance in Principle 8 and deprecate the PID instead of deleting it, marking it as no longer active while keeping it intact so it can continue to serve as a reliable identifier.

</details>

## 2. Assigning PIDs to resources and managing change

### P5: **PIDs identify resources that are intended to be stable in their definition.**

<details>
<summary>Explanation</summary>

A PID is only effective when it consistently refers to the same resource over time. This requires that the resource’s core characteristics (those that define its identity) remain stable. For example, if a PID is assigned to a specific book edition defined as the first edition, it should not later be used to refer to later editions, as this could create confusion about what the PID actually identifies.

Clearly defining the fundamental attributes of a resource from the outset is very important, as this directly affects how PIDs are assigned, managed and ultimately reused. For instance, if an organisation holds multiple physical copies of the same poster, it must decide whether each copy is a distinct resource deserving its own PID, or whether they are all manifestations of a single resource that can share one PID. The decision essentially depends on how the organisation defines the resource’s core characteristics.

</details>

### **P6: The assignment of PIDs is not restricted to any specific type of resource, whether physical, digital or conceptual, an individual, a subpart or entire collection or even a version of a resource.**

<details>
<summary>Explanation</summary>

PIDscan be assigned to a wide variety of resources, depending on the specific needs of the organisation and/or users. When deciding the scope (including the granularity) of a PID, organisations should prioritise assigning identifiers to units that can remain stable and accessible over time. User needs should also be considered, as the way PIDs are assigned can influence how easily users can reference or access specific parts of a resource in isolation. For instance, if a PID is assigned to a very broad resource, it can be harder to maintain its stability and users might struggle to find or stably reference what they have observed before in a particular section of the resource. On the other hand, if resources are assigned at a very granular level, managing them can become quite challenging.

In some cases, separate PIDs may be needed for different representations of the same resource. For example, the physical painting and its digital reproduction can each have their own PID: the PID for the painting refers to the physical object itself, while the PID for its digital representation refers to the digital version. Nevertheless, the PID for the physical painting can be associated with, or point to, one or multiple digital representations. Both resources (and their identifiers) are distinct, yet still can be kept interrelated.

</details>

### **P7: When a resource undergoes significant changes to the extent that it becomes a new resource, the PID of the previous version of the resource is not used to identify the new resource.**

<details>
<summary>Explanation</summary>

Permanently identified resources may change over time and managing these changes requires careful attention. If a change is so significant that it alters the core identity of the resource, the original PID should no longer be used to refer to the changed resource. This is important because users rely on the PID to consistently point to the same, clearly defined resource. For example, imagine a published text document where a new edition adds a prologue, dedication or editorial changes. If a researcher had highlighted or cited specific passages in the original version, those passages might be layered or removed in the new edition. Using the same PID could then confuse and mislead users or make it impossible to locate the referenced content.

One common way to manage evolution of a resource is through versioning, which allows updates to resources to be tracked and identified without losing the connection to the original version of the resource. The decision whether to treat a change as a new version or a completely new resource depends on how the organisation defines resources’s identity.

</details>

### **P8: When circumstances result in a resource being deleted, the PID is kept and marked as deprecated.**

<details>
<summary>Explanation</summary>

If a resource has been permanently removed from the system, its associated PID must not be removed or reassigned to a different resource. Instead, the PID should remain active but flagged as deprecated to indicate that the original resource has been deleted. This helps minimise disruption for users or systems that rely on the PID for referencing.

Note that deprecation is also appropriate when a resource undergoes significant changes. For example, if it is split into two or more new resources, the original PID can be marked as obsolete, while providing clear guidance on (and references to) the new resources.

</details>

## 3. Dissemination, use and interoperability of PIDS

### **P9:** **A PID resolves to a landing page (containing the PID, information about the resource and a means for accessing the resource) or to the resource itself depending on the type of resource, or ultimately to the PID record if neither are available.**

<details>
<summary>Explanation</summary>

A PID is not just a static label for a resource, it is designed to be actionable. This means that it can be used in a practical way to access, retrieve or interact with the resource it identifies. The process by which a PID leads to a resource or related information is known as resolution. This is typically achieved via a resolver, an intermediary service that interprets the PID and redirects users to the appropriate endpoint.

Depending on the nature of the resource and the available infrastructure, a PID may resolve to:

- Landing page, which includes the PID itself, descriptive metadata and resource or access options for it.
- Resource itself (for example, a file, image, dataset, document).
- PID record, which contains basic metadata about the resource.

For example, the ARK identifier for the artwork “Mona Lisa”: `ark:/53355/cl010066723` is, on its own, just a character string (following a formal identifier scheme). However, when made actionable via a resolver, such as `https://n2t.net/ark:/53355/cl010066723`, it becomes a resolvable URI. Accessing this link initiates the resolution process, which, in this case, redirects the user to a landing page containing images of the painting and information about it.

Resolvers vary in scope and functionality depending on the context and identifier scheme. Global resolvers (for example [N2T](https://n2t.net/), [DOI](https://dx.doi.org/) and [Handle system](https://hdl.handle.net/)) are services that operate on a global scale, providing universal accessibility for PIDs. While some global resolvers, like the DOI resolver, are specific to a particular identifier scheme, others, such as N2T and Handle, support multiple schemes. Local or institutional resolvers, on the other hand, support resolution within a specific domain or repository.

Resolvers offer several advantages over assigning stable URLs (often referred to as “cool URIs”). They decouple the PID from the resource's physical location, ensuring that it remains functional even if the resource moves. For example, if a document is moved to a new server, an organisation using a resolver only needs to update the target URL in the resolver’s database. All users and systems referencing the PID can continue to access the resource without needing to know about the change.

</details>

### **P10: When a PID is deprecated, its resolution presents a tombstone page where a subset of the information about the resource is maintained and information about the reason for deletion is available.**

<details>
<summary>Explanation</summary>

A tombstone page serves to preserve a traceable record of a resource’s existence after the resource has been removed, retracted, destroyed, lost, or otherwise made unavailable to users. It should retain enough information to confirm the identity of the resource, while typically omitting the resource itself (e.g. media files). It often includes an explanation of why the resource is no longer available, a link to a new version or related resources (if applicable) and provides contact information for further inquiries.

</details>

### **P11:** **Metadata about the PID is maintained in a PID record and made accessible without restrictions in machine-readable formats.**

<details>
<summary>Explanation</summary>

A PID record is a structured set of information about the identified resource, such as essential metadata about it, information on how to retrieve it, details of any revisions or updates made to the resource over time and links to related resources. While the metadata is usually minimal, it must include enough detail to help users understand the resource. It may only be a subset of the resource’s metadata compared to the landing page.

Importantly, PID records are designed to serve machine actionable services. This means they must be available in a format that allows both humans and systems to access, interpret, and act upon the metadata. For example, DOI identifier `https://doi.org/10.5962/bhl.title.62506` is accessible through content negotiation, a mechanism that allows users and systems to request metadata in different formats (e.g. JSON, XML or RDF) by specifying the desired format in the accept header (e.g. Accept: application/json for the JSON representation) when making a request to the DOI. This ensures that both humans and machines can read and process the information. To support this function, PID records must also be openly and freely accessible, without restrictions such as paywalls, login requirements or subscription services.

</details>

### **P12:** **A PID is usable, without any legal, contractual or financial restrictions, in perpetuity to identify its associated resource.**

<details>
<summary>Explanation</summary>

A PID must remain valid and usable over time, regardless of where the resource is located or who manages it. Anyone should be able to use the PID at any time to reference the resource, without encountering any barriers, even if access to the resource itself is restricted or subject to conditions. This unrestricted and persistent usability of PIDs makes them reliable tools for long-term access and citation in various contexts, such as academic research, digital archives or data sharing platforms.

</details>

### **P13:** **Users are informed on how to use PIDs for referring to resources sustainably.**

<details>
<summary>Explanation</summary>

PIDs must be clearly presented and accessible to everyone for any purpose. Unlike endpoint URLs, which may change over time, PIDs provide a stable and persistent reference to a resource. It is important to make them visible and encourage users to cite a resource using its PID. Promoting the correct use of PIDs helps organisations support long-term access, citation, data sharing and reuse.

</details>

## 4. Sustainability and governance of PIDs

### **P14:** **The administration of PIDs is fulfilled by a trustworthy and long-lasting system infrastructure that guarantees quality, security, reliability, availability and performance.**

<details>
<summary>Explanation</summary>

A sustainable PID system must guarantee that identifiers continue to work reliably over time, regardless of changes in technology, staff or service providers. This requires not just robust infrastructure, but also clear governance and contingency planning.

Organisations should ensure that the resolution service remains available, secure, and performant, even during system migrations or when third-party providers are involved. If external partners or vendors manage parts of the PID lifecycle (e.g. registration or resolution), agreements and fallback mechanisms should be in place to prevent data loss or loss of functionality. Regular monitoring, maintenance, and documentation are essential to keep the PID infrastructure operational and to safeguard long-term access to the identified resources.

</details>

### **P15:** **A single owner is committed to keeping the information in the PID record and the landing page up to date.**

<details>
<summary>Explanation</summary>

A PID owner is typically an organisation with the responsibility of ensuring all metadata and related details for the resource linked to the PID are consistently updated as changes occur. This may involve updates related to the resource’s status, format, location, rights or other pertinent information. By assuming full responsibility for keeping the PID record and associated landing page up-to-date, the owner ensures that users can trust the information provided through the PID. Regularly updated records help prevent issues such as outdated content or misidentification of resources, all of which could lead to confusion or loss of valuable data.

Designating a single owner also facilitates clear accountability. If discrepancies or issues arise, there is a designated entity that can be contacted to make necessary updates or corrections. This streamlines the process and fosters confidence in the PID system, which is vital for any data reuse that relies on PIDs for citation and access.

</details>

### P16: **The information about PID ownership is made public.**

<details>
<summary>Explanation</summary>

Publicly available ownership information clearly communicates who is responsible for maintaining and updating the PID record and landing page. It enables users to verify details related to the resource and ensures that, if, for example, the owning organisation changes or issues arise with the resource, there is a clear point of contact. Providing information about the ownership helps build trust, giving users confidence in the reliability and dependability of the PID system.

</details>

### P17: **A new PID is not assigned to the resource when the ownership of the resource changes while its content remains the same.**

<details>
<summary>Explanation</summary>

PIDs are intended to provide stable, long-term references to resources. Assigning a new PID when the ownership of a resource changes undermines this stability, as users relying on the original PID may not recognise or discover the new one. Instead of assigning a new PID, we strongly recommend coordination between the current and new resource owner. The current owner should transfer all associated metadata and responsibilities to the new owner. This includes updating the PID record to reflect the change in ownership and ensuring the PID resolver redirects users to the resource’s new location and landing page, now managed by the new owner.

If, for any reason, the new owner assigns a new PID to the resource, we recommend reducing user confusion by having the original PID redirect to the new PID.

</details>

### **P18:** **A PID policy is created, maintained and made available by the owner of the PID, which defines the governance mechanisms and system infrastructure that guarantee compliance against the principles defined in this document.**

<details>
<summary>Explanation</summary>

The Policy for persistent identifiers in the data space brings together key considerations and best practices for creating and managing truly persistent identifiers. Organisations that assign PIDs should develop their own written policy that reflects the Policy’s principles in their own context and ensures that core aspects, such as PID scope, governance, format, infrastructure, metadata management and access, are clearly addressed. Maintaining a reliable and up-to-date policy helps ensure that PIDs are not only technically sound but also trusted and sustainable over time.

</details>

### P19: **A PID policy is explicit, unambiguous and stable.**

<details>
<summary>Explanation</summary>

A PID policy contains clearly defined rules and procedures that leave no room for confusion. Its primary purpose is to ensure consistency and reliability in the PID lifecycle processes, supporting the long-term stability that users and systems depend on. Because PIDs are intended to provide a stable reference over time, the policy that governs them should also be stable and not change frequently. Changes should only be made when necessary, for example, to expand the scope of persistent identification. Updates to the policy must follow a transparent review and communication process to avoid undermining trust in the system.

</details>

### P20: **A PID policy is documented and disseminated to all (internal & external) stakeholders.**

<details>
<summary>Explanation</summary>

A policy is made accessible to everyone involved in or affected by the management and use of PIDs. This ensures that all stakeholders, whether within the organisation or external partners and users are informed about the procedures and responsibilities outlined in the policy. By making the policy widely available, organisations demonstrate transparency and accountability, ensuring all stakeholders understand the practices governing PIDs.

</details>

# References

1. Dutch Digital Heritage Network (Netwerk Digitaal Erfgoed) [Persistent Identifier Guide](https://www.pidwijzer.nl/en/best-practices/implementation)
2. Committee on Earth Observation Satellites (CEOS) [Persistent Identifiers Best Practices](https://ceos.org/document_management/Working_Groups/WGISS/Documents/WGISS%20Best%20Practices/CEOS%20Persistent%20Identifier%20Best%20Practice.pdf) (for Earth Observation mission data)
3. Group of European Data Experts (GEDE) [Persistent identifiers: Consolidated assertions](https://www.rd-alliance.org/system/files/PID-report_v6.1_2017-12-13_final.pdf)
4. GBIF [A Beginner’s Guide to Persistent Identifiers](https://assets.ctfassets.net/uo17ejk9rkwj/8aIUAbLo0oycyMiM2IKUS/363edf7ab4558460cfe1ef140567450f/persistent_identifiers_guide_en_v1.pdf)
5. CD2H [Best Practices for Using Identifiers](https://playbook.cd2h.org/en/latest/chapters/chapter_2.html)
6. McMurry et al. [Identifiers for the 21st century: How to design, provision, and reuse persistent identifiers to maximize utility and impact of life science data](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5490878/)
7. Catch Plus Project [Persistent Identifiers](http://www.catchplus.nl/wp-content/uploads/2010/01/Discussion-document-persistent-identifiers-CATCHPlus.pdf)
8. British Library [Persistent Identifier Policy](https://doi.org/10.23636/kwgh-pc35)
9. Bibliothèque nationale de France [Politique identifiants BnF](https://www.bnf.fr/fr/politique-identifiants-bnf)
10. European Open Science Cloud (EOSC) [A Persistent Identifier (PID) policy for the European Open Science Cloud (EOSC](https://data.europa.eu/doi/10.2777/926037))
