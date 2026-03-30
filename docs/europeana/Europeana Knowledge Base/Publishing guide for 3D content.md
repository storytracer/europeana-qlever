


# Publishing guide for 3D content

This page is for professionals working in cultural heritage institutions who want to share 3D data with [europeana.eu](http://Europeana.eu) .

- [Getting started…Where can I find more information about digitising in 3D?](#getting-started-where-can-i-find-more-information-about-digitising-in-3d)
- [What are the main requirements for sharing 3D with Europeana?](#what-are-the-main-requirements-for-sharing-3d-with-europeana)
- [Where can I find more information about sharing 3D with Europeana?](#where-can-i-find-more-information-about-sharing-3d-with-europeana)
- [How do I map 3D object(s) and data about them to EDM?](#how-do-i-map-3d-object-s-and-data-about-them-to-edm)
- [Are there any examples of 3D records in EDM?](#are-there-any-examples-of-3d-records-in-edm)
- [Which 3D formats does Europeana support?](#which-3d-formats-does-europeana-support)
- [Can Europeana host 3D files?](#can-europeana-host-3d-files)
- [What rights statement or licence should I assign to a 3D model?](#what-rights-statement-or-licence-should-i-assign-to-a-3d-model)
- [Is there (new) copyright in the 3D model?](#is-there-new-copyright-in-the-3d-model)
- [How can I support and facilitate reuse of my 3D material?](#how-can-i-support-and-facilitate-reuse-of-my-3d-material)
- [Where can I get (technical) support?](#where-can-i-get-technical-support)

# Getting started…Where can I find more information about digitising in 3D?

- TwinIt!: 3D for Europe’s culture 4CH webinar series
- 4CH competence centre provides access to a [Knowledge Base and a series of resources](https://www.4ch-project.eu/resources-activities/) and to experts able to advise on 3D digitisation
- [VIGIE 2020/654 European Study on quality in 3D digitisation of tangible cultural heritage](https://digital-strategy.ec.europa.eu/en/library/study-quality-3d-digitisation-tangible-cultural-heritage)
- [Share3D: Introduction to the 3D workflow](https://carare.gitbook.io/share-3d-guidelines/3d-process/context) provides an overview of 3D
- DARIAH offers a free online course about ‘[Remaking Material Culture in 3D](https://teach.dariah.eu/course/view.php?id=55&section=0)’

In addition, the Expert Group on Digital Cultural Heritage and Europeana have summarised some aspects to keep in mind when starting digitising 3D:

- Consider the value and need for digitisation (see for example the [Twin it! campaign](https://pro.europeana.eu/page/twin-it-3d-for-europe-s-culture) and [EC 3D KPI’s](https://digital-strategy.ec.europa.eu/en/news/commission-proposes-common-european-data-space-cultural-heritage))
- Select what to digitise and for what use cases and user group
- Decide whether to digitise in-house or to outsource
- Clarify the copyright aspects and plan for open and broad access
- Determine the minimum quality needed but aim for the highest affordable
- Identify the different versions and formats suitable for the use cases targeted
- Plan for long term preservation of the data acquired
- Use the right equipment, methods and workflows
- Protect the assets during and after digitisation
- Invest in knowledge of 3D technologies, processes and content

For reference and more information, see [Basic principles and tips for 3D digitisation of cultural heritage](https://digital-strategy.ec.europa.eu/en/library/basic-principles-and-tips-3d-digitisation-cultural-heritage)

For tutorials, see for example [dariahTeach](https://teach.dariah.eu/)

For community of practice, the [5DCulture Community of Practice](https://5dculture.eu/cop) provides access to a wealth of resources, news and best practices which relate to 3D and cultural heritage.

# What are the main requirements for sharing 3D with Europeana?

The main requirements for sharing 3D with Europeana are:

- The 3D models are published online and accessible in a viewer
- Metadata records are available for export or harvesting in an XML format that is mapped to the Europeana Data Model
- Your organisation has signed the [Data Exchange Agreement](https://pro.europeana.eu/page/the-data-exchange-agreement) with Europeana Foundation or via one of the Europeana aggregators

In addition, Europeana recommends enriching your metadata records by:

- Including language tags
- Supporting browse by subject or types; by place; by date or time-span; by agents
- Using [LOD vocabularies supported by Europeana](https://docs.google.com/spreadsheets/d/1BoDNolkcp_qfvVShdOZyGcf61XslcwKF2MdGcjgYs20/edit?usp=sharing)
- Offering access to additional information on the creation process of the 3D models (i.e. the paradata)

[Aggregators](https://pro.europeana.eu/page/aggregators) can offer help and advice on the process of transforming your metadata records into Europeana’s EDM format and sharing your metadata with Europeana

# Where can I find more information about sharing 3D with Europeana?

*Europeana’s Publishing Guide* is available on the [Publishing guide](Publishing%20guide.md) as a resource for data partners sharing material with the Europeana website. The Publishing Guide builds on the Europeana Publishing Framework (EPF) which addresses the quality of content and metadata through ‘tiers’. For 3D, see the following sections:

- [ContentTier 1: 3D type](Publishing%20guide/Content%20&%20Metadata%20Tiers/Tier%201%20requirements%20per%20edm_type/ContentTier%201_%203D%20type.md) and [Page not accessible (ID: 2059796527)]
- [Tier A-C requirements](Publishing%20guide/Content%20&%20Metadata%20Tiers/Tier%20A-C%20requirements.md) which are common for all media types

In addition, the [User Guide to the Share3D dashboard](https://carare.gitbook.io/share-3d-guidelines/user-guide-share3d-dashboard/introduction) provides a step-by-step guide to sharing 3D models with Europeana via the tool maintained by CARARE.

# How do I map 3D object(s) and data about them to EDM?

If you are new to the Europeana Data Model (EDM), we recommend you begin by consulting the [EDM - Mapping guidelines](EDM%20-%20Mapping%20guidelines.md).

At the moment, there are no special additional fields for data about 3D objects available in EDM. We are working on reviewing which additional fields could be useful.

Just like with other types of objects, the type for 3D objects has to have a set value, in this case, edm:type = '3D'. A link to your online resource should be provided in edm:isShownBy. There are two preferred options when providing a 3D object in EDM:

- **edm:isShownBy is a direct link to a 3D file**. If you provide a direct link (for example to an STL file) in edm:isShownBy, it is advisable to map a URL to your resource to edm:hasView as well. This will lead to a higher quality measurement in [Content & Metadata Tiers](Publishing%20guide/Content%20&%20Metadata%20Tiers.md). Please note Europeana website does not yet support the display of 3D objects when edm:isShownBy is a direct link to a 3D file.
- **edm:isShownBy is a link to a webpage where the 3D object can be displayed and which can be mapped to an oEmbed URL**. Europeana currently supports links to [Sketchfab](https://sketchfab.com/) or the [WEAVE viewer](https://weave-3dviewer.com/) when they are provided as one of the following URL patterns:

[https://sketchfab.com/3d-models/\*](https://sketchfab.com/3d-models/*',)

[https://sketchfab.com/models/\*](https://sketchfab.com/models/*',)

[https://sketchfab.com/show/\*](https://sketchfab.com/show/*')

[https://weave-3dviewer.com/asset/\*](https://weave-3dviewer.com/asset/*')

Europeana applies an additional logic to convert the above URLs into an oEmbed URL that is used for embedding, meaning that 3D objects are displayed on the Europeana website. So if you would like the user to interact with your content directly on the Europeana item page, you can use the SketchFab or WEAVE viewer. More supported viewers and URL patterns are expected to be added in the future. If you have your own viewer, you can request your [oEmbed-compliant](https://oembed.com/) viewer to be added to the internal registry of oEmbed endpoints that are supported by us. Please send a message to the [3D service desk](https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/56) and your request will be checked.

Alternatively, if your viewer is not supported by Europeana, it is possible to provide a link to 3D online content (i.e. link to a 3D viewer or player) in edm:isShownAt, but this may lead to lower content tiers.

# Are there any examples of 3D records in EDM?

Yes, there are specific [3D XML-examples](https://drive.google.com/drive/u/1/folders/1PjVyjSLilSjgGuaq4vLG9UiOs1Grutb0) in EDM and on [Example records - content & metadata tiers](Publishing%20guide/Content%20&%20Metadata%20Tiers/Example%20records%20-%20content%20&%20metadata%20tiers.md), you can find examples for any media type, including 3D. Examples are available as XML and as a preview on the Europeana website.

# Which 3D formats does Europeana support?

At the moment, there are no recommended formats yet. Any format that is visible in an embeddable (oEmbed) viewer (currently only Sketchfab or WEAVE are supported, but more will be in the future, and it is always possible to request if your own viewer can be embedded) should do, as well as direct links to your 3D content.

There are, however, formats that are well established within the 3D community and that we are considering supporting in the future. Multiple formats can already be found within the 3D content published on the Europeana website, such as DAE, PLY, WRL, GLTF (via embedded SketchFab viewer), and OBJ. Other options can, for example, be STL, NXS (NXZ), DICOM, IFC or USDZ. The selected format may of course depend upon the requirements you have for your 3D collections, and the use case you have in mind.

For 3D records, 3D PDF files are not sufficient and should not be submitted to Europeana.

# Can Europeana host 3D files?

No. Some national aggregators have solutions if you are unable to host content yourself.

# What rights statement or licence should I assign to a 3D model?

The copyright section in the [Europeana Knowledge Base](https://europeana.atlassian.net/wiki/x/AQDLEw) and our [copyright pages](https://pro.europeana.eu/share-your-data/copyright) on Europeana Pro are a good starting point. They give information on copyright, the list of available rights statements, and how to choose one that is correct.

To support our goal of providing accurate rights information on Europeana.eu, we would like to give some more information that may help you decide the most appropriate rights statement for your 3D material that reflects the existence or lack of existence of copyright and your institutional policy.

The first crucial element to consider when choosing a rights statement is whether copyright exists (in the underlying object that is represented and/or in the digital version) or if on the contrary no copyright exists and the material is in the public domain. To clarify this, refer to the question that follows (‘Is there (new) copyright in the 3D model?’). Depending on whether copyright exists or not, you can choose from various rights statements and provide specific indications.

If copyright exists (in the underlying object, the model or both), you should use either a [Creative Commons Licence](https://pro.europeana.eu/page/available-rights-statements#section-3-creative-commons-licenses), or a [Rights Statement](https://pro.europeana.eu/page/available-rights-statements#section-4-rights-statements-by-the-rights-statements-consortium) with the ‘in copyright’ indication. These options should not be used if no copyright exists. The choice between these various options should be made by whoever holds the copyright, on the basis of a willingness to authorise more or less reuse.

If no copyright exists in the underlying object, one of the ‘public domain options’ should be used. That is: the [Creative Commons Public Domain Mark](https://pro.europeana.eu/page/available-rights-statements#section-2-creative-commons-public-domain-tools), or the [Rights Statement](https://pro.europeana.eu/page/available-rights-statements#section-4-rights-statements-by-the-rights-statements-consortium) with the ‘no copyright’ indication, such as ‘No Copyright - Other Known Legal Restriction’ or ‘No Copyright - non commercial re-use only’

Last, the [Creative Commons Public Domain Dedication (CC0)](https://pro.europeana.eu/page/available-rights-statements#section-2-creative-commons-public-domain-tools) should be used for 3D material in which copyright exists and for which the rightsholder has agreed to waive the rights.

Please check [this page](https://pro.europeana.eu/page/available-rights-statements) for the full list of options, and [this page](https://pro.europeana.eu/page/selecting-a-rights-statement) for tips on which one to choose.

It is also possible that the original object and its 3D model can have different rights conditions. Because in practice, a user cannot use one without the other, we recommend sharing a single set of reuse conditions, that is, a licence, tool or rights statement that reflects both conditions at once. To do that, you should choose the most restrictive option (e.g. if the digitisation is out of copyright, but the object that is digitised is still in copyright, choose a rights statement that reflects the ‘in copyright’ status). You can read more about this [here](https://pro.europeana.eu/page/selecting-a-rights-statement#section-3-no-rights-on-digital-reproductions). If necessary, you can add clarifying information in the additional metadata.

In case of doubt, please contact us directly to help you through the process of selecting the most appropriate rights statement for your content.

# Is there (new) copyright in the 3D model?

Copyright only exists if the expression is the author's own intellectual creation.  A case-by-case assessment is necessary to identify whether copyright arises in the model, and it requires information on the process and whether creative choices were made.

There is potential for copyright to arise if creative choices have been made in 3D shapes, textures, lighting, sounds, or other. However, if a model is a faithful representation of an object, and the decisions made are mostly technical, one can assume that new copyright will not arise in the model. Even where significant time and effort have been made into creating the model, it is possible that no protection arises.

As a result, if the model is a representation of an object that is in the public domain in the physical world, one should assume that the model will be in the public domain as well.

In certain countries, certain rights are also recognised in ‘photographs’ (and assimilated types of reproductions) that are not ‘the author’s own intellectual creation’. This type of protection, though, can [no longer be claimed](https://pro.europeana.eu/post/article-14-and-the-public-domain-the-state-of-play-across-europe) for reproductions of public domain works.

# How can I support and facilitate reuse of my 3D material?

Correct rights information, and the access to the content, are two important elements to support and facilitate reuse of the 3D material.

First about the rights statement: users should base their decision on how to use the 3D material on the rights statements chosen by you.

Other than choosing the rights statement accurately, consider the options it offers to those who will want to use it. Prioritise using CC0, PDM, or any of the rights statements or licences that permit reuse (as long as they are accurate). You can read more about this on [this page](https://pro.europeana.eu/page/open-and-reusable-digital-cultural-heritage).

Second, about access to the actual digital content. Users may reuse 3D models in various ways.  The simplest form of reuse involves viewing a model online or the ability to embed a model in a web-page.  Other forms of reuse require the ability to download the model (or the 3D dataset).  For 3D printing users need to be able to download the file (STL) and send it to their printer.  Users who wish to incorporate a 3D model into a new digital project (for example, someone who is creating a digital reconstruction of a Mediaeval house might wish to incorporate models of a table and chairs correct to the period) need to be able to download the 3D files. This potentially includes shape files, textures, metadata and paradata).

# Where can I get (technical) support?

- [CARARE](https://carare.gitbook.io/share-3d-guidelines/3d-process/context), one of Europeana’s domain/thematic aggregators, can offer advice and support on 3D and/or help direct you to contacts with specialist expertise in your country.
- [EUreka3D project](https://eureka3d.eu/) (2023-2024) is developing a platform that you can use to store, manage and publish your 3D models
- [Europeana Aggregators](https://pro.europeana.eu/page/aggregators) can help with the aggregation of your metadata for Europeana publication, and provide advice and support
- 4CH as the Competence Center for the Conservation of Cultural Heritage currently being established will provide technical support on 3D capturing, modeling, and visualisation at [info3D@4ch.eu](mailto:info3D@4ch.eu)

As another option, you can reach out to Europeana directly via our [service desk](https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/56). Make sure to state the subject of your question(s) clearly in the form.
