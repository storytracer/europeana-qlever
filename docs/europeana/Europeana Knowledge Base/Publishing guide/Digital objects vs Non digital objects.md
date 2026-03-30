
[Publishing guide](../Publishing%20guide.md)

# Digital objects vs Non digital objects

**Digital objects and media resources in Europeana**

Europeana defines a digital object as a digital representation of an object that is part of Europe's cultural and/or scientific heritage. The digital object can also be the original object when born digital.

What type of digital representations are acceptable for Europeana and how objects should be represented depends on the type of the objects. In most cases, audio/video snippets or a subset of pages for a multipage document (e.g. book, report) are not an adequate representation of a digital object in order to fulfil the user demands (*The exceptions are manuscripts and illuminated manuscripts where it can be meaningful to users to have individual pages as separate metadata records*). A 300-page book is expected to be represented in Europeana as one single object and not as 300 separate objects. Digital representations of paintings or artefacts are photographs or digitisation of the objects. If the cultural object is a photograph of a painting or an artefact (for instance, a gelatin dry plate negative representing a 19th century painting), it has to be clear from the metadata that the described object is not the painting or artefact itself.

Europeana has established requirements for the links to the media resources that are part of the provided metadata. By following these requirements, we can give audiences a better experience and a greater connection with your collections. Following these requirements we will:

- Extract technical metadata from media resources (e.g. mime-type, image size, duration, colour).
- Generate thumbnail (preview) images, and show these images as part of the search results.
- Display media resources on the item pages of the Europeana collections website.

The requirements for media resources are specified in the [Europeana Media Policy](https://pro.europeana.eu/page/media-policy). The media files and [MIME types](https://pro.europeana.eu/page/media-formats-mime-types ) supported by Europeana are also published on Europeana Pro.

**Non-digital objects**

In the context of the Europeana Content Strategy, non-digital objects are any objects for which a digital representation is not available. The value of these objects resides within the informative potential of their metadata and descriptions. For example, we may consider the case of an object that has not been digitised or whose digital representation is deemed not suitable, but for which a metadata record or finding aid is available (e.g. a finding aid about a non-digitised collection of photographs at [Archives Portal Europe](https://www.archivesportaleurope.net/ead-display/-/ead/pl/aicode/FR-SIAF/type/fa/id/FRDAFAPH_AD075)).

We acknowledge that there are cases where non-digital objects play an important role in Europeana (e.g. in usability) due to the informative potential that non-digital objects have over other digital objects. In hierarchical metadata it is possible that not every level within a hierarchy has a digital representation attached to it. For this metadata to be present in Europeana, the objects described at these levels of the hierarchy must be ingested as non-digital objects. Without the possibility to deliver the metadata of these non-digital objects to Europeana, the quality of the data’s hierarchy is compromised, which will negatively affect the end-user browsing experience. Another example of hierarchical metadata are bibliographic records of newspaper titles, which have no digital surrogate, but are essential for the interpretation of the metadata of the individual newspaper issues, which do have digital surrogates.

In both cases described above, non-digital objects are included in a collection that contains hierarchical metadata, and the metadata of the non-digital objects contains explicit hasPart/isPartOf relations with other digital objects. It is important to keep in mind that these cases are exceptional and that non-digital object aggregation will otherwise not be implemented in Europeana.
