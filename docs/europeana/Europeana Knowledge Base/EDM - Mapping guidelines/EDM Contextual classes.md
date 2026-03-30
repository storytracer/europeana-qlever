---
tags:
  - '#edm-contextual-classes'
---

[EDM - Mapping guidelines](../EDM%20-%20Mapping%20guidelines.md)

# EDM Contextual classes

The contextual classes of **edm:Agent, edm:Place, edm:TimeSpan** and **skos:Concept** are provided to allow these entities to be modelled as separate entities from the CHO with their own properties if the data can support such treatment. When source metadata contains additional details about an entity that is distinct from the CHO (for instance, the date of birth for an author, different language versions of a subject term) then these contextual classes can be employed to model that separate entity. Such values are properties of that separate entity, rather than a property of the CHO and the properties can be mapped by creation of an appropriate EDM contextual entity. This may be the case where the value in the property is an identifier taken from a thesaurus or authority file which will link to further information related to that entity. For example, the identifier for an Author name in an authority file will give access to fuller information about that Author.

![](../../attachments/85df3c37-8b05-415e-9f85-d7f563e92dc3.png)

*A Provided CHO with two contextual resources*

Many providers already have rich data due to their use of authority files, controlled vocabularies and thesauri.

The inclusion of contextual resources allows the exploitation of this rich data and allows data about the contextual resource to be kept separate from the data about the object of the description.

For example, a provider could create an instance of an edm:Agent class and instead of simply providing the text string “ William Shakespeare” as dc:creator, could provide the link (URI) to Shakespeare in an authority file and enable the use of the rich related data in that source(multi-­lingual variations of the name, dates and places of birth, death etc.) Similarly for Places, Timespans and Concept. Europeana can use such URIs to fetch further information from those external resources if they are available as linked open data. This is therefore the main way in which we can carry out enrichment on the data: *by adding details that may not already exist in the provided data.*

> [!IMPORTANT]
> **Please note that when and if you provide a link to a derefereceable resource (ie Getty AAT, geonames, etc - vocabularies supported by Europeana) there is no need to create a contextual class.**
