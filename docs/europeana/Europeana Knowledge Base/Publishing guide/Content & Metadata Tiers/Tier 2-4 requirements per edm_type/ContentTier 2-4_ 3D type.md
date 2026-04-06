---
tags:
  - '#content'
  - '#framework'
  - '#epf'
  - '#quality'
  - '#tiers'
  - '#3d'
---

# ContentTier 2-4: 3D type

### Content Tier 2 (Europeana as a showcase)

If you want to make your 3D content more accessible on the Europeana website then the content needs to be embeddable in a supported viewer. You can find more information on embeddable resources on [Embeddable resources in EDM (guidelines)](../../../EDM%20-%20Mapping%20guidelines/Guidelines%20for%20data%20submission%20using%20the%20EDM%20Profiles/Embeddable%20resources%20in%20EDM%20(guidelines).md).

In order to reach Content Tier 2, it is also required to indicate an ‘intendend usage’ (your motivation to create the 3D model) for your 3D resource. You can find more information on how to provide this information on [this page](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3294363660#Property%3A-edm%3AintendedUsage).

### Content Tier 3 (Europeana as a distribution platform for non-commercial reuse)

If you want to make use of Europeana as a distribution platform that enables the use of your 3D content by private individuals, educators and researchers then, **in addition** to the criteria described for Content Tier 2 above, you need to provide a direct link to a (supported) file. You can find more information on how to provide this information on [this page](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3255468048#Step-1%3A-Provide-a-direct-link-to-your-model-and%2For-link-to-a-viewer).

You also need to provide a dc:type property on WebResource level. You can choose from a [Page not accessible (ID: 3255140387)]. More on how to provide this information can be found on [this page](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3255468048#Step-6%3A-Choose-the-dc%3Atype-value-for-the-model).

Additional technical metadata connected to the dc:type can be provided too. See [this page](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3255468048#Step-5%3A-Add-extra-information-about-the-model-in-edm%3AWebResource).

You also need to make sure that the 3D content comes with one of the seven rights statements that **allow reuse:**

- **4 Creative Commons licences: CC BY-NC, CC BY-ND, CC BY-NC-ND, CC BY-NC-SA;**
- **3** [**RightsStatements.org**](http://rightsstatements.org/)**'s statements: NoC-NC, NoC-OKLR, InC-EDU**

### Content Tier 4 (Europeana as a free reuse platform)

If you want to make use of Europeana as a platform that enables the free reuse of your 3D content then, in addition to the criteria described for Content Tiers 2 and 3 above, you also need to make sure that the 3D content comes with a rights statement that allows **free reuse (CC BY, CC BY-SA, CC0 or PDM).**

#### Overview of Content tier 2-4 requirements for 3D files

|          |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |                                                                                                                                                                                                                                                                 |
|:---------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **TIER** | **Rights**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | **edm:type=3D**                                                                                                                                                                                                                                                 |
| **2**    | [Any of the available rights statements](https://pro.europeana.eu/page/available-rights-statements)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Same as content tier 1, plus <br/> Link to a oEmbed compliant viewer <br/> Intended usage (knowledge, infotainment, creativity, curation - see [page](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3294363660#Property%3A-edm%3AintendedUsage)) |
| **3**    | Associated media resource has either **open or restricted** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md)**:** <br/><ul local-id="052f334002f9"><li local-id="dcb2c925fce1"><p local-id="1382b3f0b633">4 Creative Commons licences: CC-BY-NC, CC BY-ND, CC-BY-NC-ND, CC-BY-NC-SA</p></li><li local-id="c89522e28c92"><p local-id="25c47dc3c570">3 <a class="external-link" href="http://rightsstatements.org/" rel="nofollow"><u>RightsStatements.org</u></a>’s statements: NC-OKLR, NoC-NC, InC-EDU</p></li></ul> | Same as content tier 2, plus <br/> Direct link to a (supported) file <br/> Additional dc:type and technical metadata - when applicable in relation to dc:type                                                                                                   |
| **4**    | Associated media resource has **only open** [How do I choose a rights statement when submitting data to Europeana?](../../Licenses%20&%20Rights%20statements/How%20do%20I%20choose%20a%20rights%20statement%20when%20submitting%20data%20to%20Europeana_.md)**:** <br/> PDM, CC-0, CC-BY, CC-BY-SA                                                                                                                                                                                                                                                                                                                                                                                    | Same as content tier 3                                                                                                                                                                                                                                          |

---

---

> [!IMPORTANT]
> For guidelines on which URI for specific rights statement you should use when providing EDM, consult [Providing copyright metadata to Europeana](../../Licenses%20&%20Rights%20statements/Providing%20copyright%20metadata%20to%20Europeana.md).
>
> More information about identifying whether a work is subject to copyright or not is available [here](https://pro.europeana.eu/page/identifying-copyright-in-collection-items).

### Related articles

[ContentTier 1: 3D type](../Tier%201%20requirements%20per%20edm_type/ContentTier%201_%203D%20type.md)
