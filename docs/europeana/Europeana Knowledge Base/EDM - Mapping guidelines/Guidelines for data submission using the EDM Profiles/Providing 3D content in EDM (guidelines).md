
# Providing 3D content in EDM (guidelines)

We encourage data partners to provide 3D content following the steps on the page below. Doing so enhances data quality and reusability while contributing to the evaluation and validation of the 3D profile. Following the [EDM - Mapping guidelines](../../EDM%20-%20Mapping%20guidelines.md)continues to be mandatory: for example awarding the correct [Licenses & Rights statements](../../Publishing%20guide/Licenses%20&%20Rights%20statements.md) is of vital importance and influences the [tier calculation.](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3270115340?draftShareId=197efaf8-0cf3-4483-9cda-bc53d5bb4fec)

> [!TIP]
> The full definition of the EDM profile for 3D content is available [here](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3294363660?draftShareId=a32a51a2-e031-4a0d-bd30-d658f574f550).
>
> Any issues regarding the provision on 3D assets can be flagged [contacting us](https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/56).

# Steps for providing 3D content

- [Step 1: Provide a URL to an embeddable viewer](#step-1-provide-a-url-to-an-embeddable-viewer)
- [Step 2: Provide a thumbnail for the 3D object](#step-2-provide-a-thumbnail-for-the-3d-object)
- [Step 3: Provide a direct link to the model](#step-3-provide-a-direct-link-to-the-model)
- [Step 4: Indicate the intended use of the 3D digitisation](#step-4-indicate-the-intended-use-of-the-3d-digitisation)
- [Step 5 (optional): Indicate the relation of the model to the “real world”](#step-5-optional-indicate-the-relation-of-the-model-to-the-real-world)
- [Step 6 (optional): Add extra information about the model in edm:WebResource](#step-6-optional-add-extra-information-about-the-model-in-edm-webresource)
- [Step 7 (optional): Specify the type of model and its associated technical metadata](#step-7-optional-specify-the-type-of-model-and-its-associated-technical-metadata)
- [Step 8 (optional): Include more complete paradata for the model](#step-8-optional-include-more-complete-paradata-for-the-model)
- [A complete example](#a-complete-example)

Each step includes a mapping example, showing how the provision evolves and builds on the previous step towards the final mapping. The last example compiles all the steps into a complete example.

> [!IMPORTANT]
> The definitions of the terms **MUST**, **MUST NOT**, **SHOULD**, etc. used in this document can be found at <https://tools.ietf.org/html/rfc2119>.

## **Step 1: Provide a URL to an embeddable viewer**

Provide the oEmbed URL for the embeddable view of the 3D object as `edm:isShownBy`. The web resource representation for this view must follow the [Embeddable resources in EDM (guidelines)](Embeddable%20resources%20in%20EDM%20(guidelines).md) and meet its requirements.

If more viewers for this object are available and you would like to provide them as alternative views, you can link to each of the viewers using `edm:hasView`.

Example:

```java
<ore:Aggregation rdf:about="[…]">
[…]
    <edm:isShownBy rdf:resource="https://eureka3d.vm.fedcloud.eu/oembed?url=https%3A%2F%2Feureka3d.vm.fedcloud.eu%2F3d%2F00000000007E85E1736861726547756964233838393331333763313830656365653561396438353630336333633434333437636863316264233665663637356366323134343661326366656235653866346139393233333165636865663265236232323537333061633031353762383339353036343831613665656130336265636839393537&format=json"/>
[…]
</ore:Aggregation>

<edm:WebResource rdf:about="https://eureka3d.vm.fedcloud.eu/oembed?url=https%3A%2F%2Feureka3d.vm.fedcloud.eu%2F3d%2F00000000007E85E1736861726547756964233838393331333763313830656365653561396438353630336333633434333437636863316264233665663637356366323134343661326366656235653866346139393233333165636865663265236232323537333061633031353762383339353036343831613665656130336265636839393537&format=json">    
    <edm:type>3D</edm:type>
    <svcs:has_service rdf:resource="https://eureka3d.vm.fedcloud.eu/oembed"/>
[…]
</edm:WebResource>

<svcs:Service rdf:about="https://eureka3d.vm.fedcloud.eu/oembed">
    <dcterms:conformsTo rdf:resource="https://oembed.com/"/>
    <rdfs:label xml:lang="en">Eureka3D Viewer</rdfs:label>
</svcs:Service>
```

> [!IMPORTANT]
> Note that providing a link to a viewer is mandatory to reach Content Tier 2.

## **Step 2: Provide a thumbnail for the 3D object**

Europeana cannot generate a thumbnail directly from the embedded resource. Therefore, it is strongly recommended that you provide a thumbnail following the instructions indicated in the [Embeddable resources in EDM (guidelines)](Embeddable%20resources%20in%20EDM%20(guidelines).md).

Example:

```java
<ore:Aggregation rdf:about="[…]">
[…]
    <edm:object rdf:resource="https://3d.humanities.science/small/33859"/>
[…]
</ore:Aggregation>
```

> [!IMPORTANT]
> Note that providing a thumbnail is mandatory to reach Content Tier 1.

## **Step 3: Provide a direct link to the model**

Provide a direct link to the 3D model as a `edm:WebResource`. Instances of `edm:WebResource` that describe corresponding models and views must be connected by a `dcterms:isFormatOf` relation, where the `edm:WebResource` for the view references the `edm:WebResource` for the model (see the second example below).   
Consider carefully if the model is suitable for online display, or if it should only be available for users to download. A model that is intended for online display must be linked from the `ore:Aggregation` with either `edm:isShownBy` or `edm:hasView`, while a model intended for downloading only, must not be linked from the `ore:Aggregation`,

> [!IMPORTANT]
> When considering whether a model is suitable for online display, make sure that the model is in a format supported by Europeana (see the list of [Media Formats/Mime Types](../../Europeana%20and%20IIIF/Media%20Formats_Mime%20Types.md)), and that the model file is not too large, since a large model could take too long to load on a Web browser.

Example of a model suitable for online display:

```java
<ore:Aggregation rdf:about="[…]">
[…]
    <edm:hasView rdf:resource="https://zenodo.org/api/records/11483175/files/Lange_Houtstraat_33.obj/content"/>
[…]
</ore:Aggregation>

<edm:WebResource rdf:about="https://zenodo.org/api/records/11483175/files/Lange_Houtstraat_33.obj/content">
   […]
</edm:WebResource>
```

Example of a model provided for download:

```java
<ore:Aggregation rdf:about="[…]">
  […]
  <edm:isShownBy rdf:resource="https://eureka3d.vm.fedcloud.eu/oembed?url=https%3A%2F%2Feureka3d.vm.fedcloud.eu%2F3d%2F00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764&format=json"/>
  […]
</ore:Aggregation>

<edm:WebResource rdf:about="https://eureka3d.vm.fedcloud.eu/oembed?url=https%3A%2F%2Feureka3d.vm.fedcloud.eu%2F3d%2F00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764&format=json">    
  <edm:type>3D</edm:type>  
  <dcterms:isFormatOf rdf:resource="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764"/>  
  […]
</edm:WebResource>

<edm:WebResource rdf:about="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764">
  <edm:type>3D</edm:type>  
   ...
</edm:WebResource>
```

> [!IMPORTANT]
> Note that providing a direct link to the model is mandatory to reach Content Tier 3.

## **Step 4: Indicate the intended use of the 3D digitisation**

Identify and specify what the intended use (motivation) of the data provider was when digitising the 3D object. This can be provided using the `edm:intendedUsage` property. The values for the edm:intendedUsage property are controlled and can be found [3D content in EDM (definitions)](../../Europeana%20Data%20Model/EDM%20profiles/3D%20content%20in%20EDM%20(definitions).md). Please use a value from the vocabulary at the most granular level. For example, if the intended usage is ‘Research’, use ‘Research’ as a value and not ‘Knowledge’. Only if there is no decision made for the most granular level, then using the intended usage at the higher level is recommended.

If there was no intended use, then data providers SHOULD not use this property.

> [!IMPORTANT]
> Note that indicating the intended use is mandatory for reaching Content Tier 2.

> [!WARNING]
> Keep in mind that this is not about the reuse potential of the 3D models by users.

Example:

```java
<edm:WebResource rdf:about="https://data_partner.org/my_3D_model">
  ...
  <edm:intendedUsage rdf:resource="http://data.europeana.eu/vocabulary/usageArea/Research"/>
   ...
</edm:WebResource>
```

## Step 5 (optional): Indicate the relation of the model to the “real world”

Determine whether the model is the result of a 3D digitisation of an object, a reconstruction of an existing one or a digitally created 3D object.

This can be provided using the `schema:digitalSourceType` property with one of the following controlled values (see further information about them [here](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3294363660#List-of-vocabulary-terms-to-capture-relation-to-the-%E2%80%9Creal-world%E2%80%9D)):

- **reality captured**: `https://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture`
- **3D reconstruction**: `https://cv.iptc.org/newscodes/digitalsourcetype/dataDrivenMedia`
- **born digital**: `https://cv.iptc.org/newscodes/digitalsourcetype/digitalCreation`

Example:

```java
<edm:WebResource rdf:about="https://data_partner.org/my_3D_model">
  ...
    <schema:digitalSourceType rdf:resource="https://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"/>
 ...
</edm:WebResource>
```

## Step 6 (optional): Add extra information about the model in edm:WebResource

Multiple properties were already [edm:WebResource](../EDM%20Core%20classes/edm_WebResource.md) on the `edm:WebResource` level to provide context and information on your digital representation. In addition, certain extra properties have now been enabled on the `edm:WebResource` level as well.

- `dc:title`: different from the title of the CHO.
- `dc:language`: the model contains textual descriptions or speech in a specific language.
- `dcterms:temporal`: the model captures the state of the real-world object during a particular period in time.

> [!IMPORTANT]
> These properties were previously not available at WebResource level.

Example:

```java
<edm:WebResource rdf:about="https://data_partner.org/my_3D_model">
 ...
    <dc:title>A point cloud representation of the object</dc:title>
    <dc:language>en</dc:language>
    <dcterms:temporal>Roman</dcterms:temporal>
  ...
</edm:WebResource>
```

## **Step 7 (optional): Specify the type of model and its associated technical metadata**

Choose one of the four options from a controlled list vocabulary, and provide it as a reference in `dc:type`:

- **3D mesh**: `http://data.europeana.eu/vocabulary/modelType/3DMesh`
- **3D point cloud**: `http://data.europeana.eu/vocabulary/modelType/3DPointCloud`
- **Building Information Model (BIM)**: `http://data.europeana.eu/vocabulary/modelType/BIM`
- **Parametric model**: `http://data.europeana.eu/vocabulary/modelType/parametricModel`
- **3D Gaussian Splatting**: `http://data.europeana.eu/vocabulary/modelType/3DGaussianSplatting`

The following technical metadata properties can be provided for each type:

|  **Properties**     |  **3D mesh**    |  **Parametric model**    |  **BIM**    |  **3D point cloud**    |  **3D Gaussian Splatting**    |
|:--------------------|:----------------|:-------------------------|:------------|:-----------------------|:------------------------------|
| `edm:vertexCount`   | ☑️              | ☑️                       | ☑️          |                        |                               |
| `edm:polygonCount`  | ☑️              | ☑️                       | ☑️          |                        |                               |
| `edm:pointCount`    |                 |                          |             | ☑️                     |                               |
| `edm:gaussianCount` |                 |                          |             |                        | ☑️                            |

> [!WARNING]
> Other technical metadata properties are being considered for the 3D profile, e.g. Texture.

> [!IMPORTANT]
> Providing this information will help reach Content Tier 3 or 4.

Example:

```java
<edm:WebResource rdf:about="https://data_partner.org/my_3D_model">
 ...
   <dc:type rdf:resource="http://data.europeana.eu/vocabulary/modelType/3DMesh"/>
   <edm:polygonCount>12345</edm:polygonCount>
   <edm:vertexCount>12345</edm:vertexCount>
 ...
</edm:WebResource>
```

## **Step 8 (optional): Include more complete paradata for the model**

Paradata is information about the process of digitisation of the 3D object. It can take many different forms. Data partners can provide certain paradata using the properties that are currently available on the edm:WebResource level as described in the [edm:WebResource](../EDM%20Core%20classes/edm_WebResource.md)and in [Providing 3D content in EDM (guidelines)](Providing%203D%20content%20in%20EDM%20(guidelines).md) on this page.

Alternatively, data partners can provide a link to a full version of paradata published externally preferably using a domain standard such as [CIDOC DIG](https://cidoc-crm.org/crmdig), CARARE 2.0 (ie. other non-standard formats may be used) - an approach that is comparable to what [IIIF's Presentation API](https://iiif.io/api/presentation/3.0/) enables via its `rdfs:seeAlso` element.

Provide a reference to the paradata as a link from the model web resource to a separate web resource using the `rdfs:seeAlso` property. The format of the paradata file is specified using the `dcterms:conformsTo` property as shown in the example below.

> [!IMPORTANT]
> Providing paradata is optional and does not affect the metadata tier calculation.

Example:

```java
<edm:WebResource rdf:about="https://data_partner.org/my_3D_model">
 ...
       <rdfs:seeAlso rdf:resource="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E430A736861726547756964233538373362666161396464613066373765313264343965346666666336353764636834636135233665663637356366323134343661326366656235653866346139393233333165636865663265233261626461663562346161316433653364353639613632323761363338633363636838366431/content"/>
...
<edm:WebResource rdf:about="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E430A736861726547756964233538373362666161396464613066373765313264343965346666666336353764636834636135233665663637356366323134343661326366656235653866346139393233333165636865663265233261626461663562346161316433653364353639613632323761363338633363636838366431/content">
     <dcterms:conformsTo>pdf</dcterms:conformsTo>
</edm:WebResource>

```

## A complete example

<details>
<summary>Complete example - click to unfold</summary>

```java
[…]
<ore:Aggregation rdf:about="[…]">
[…]
 <edm:object rdf:resource="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E815D736861726547756964233237353938333538353536663337346233383362373862633263323065643930636838623735233665663637356366323134343661326366656235653866346139393233333165636865663265233865626632383265316261323839633065633265343038383533383464623065636832646262/content"/>
 <edm:isShownBy rdf:resource="https://eureka3d.vm.fedcloud.eu/oembed?url=https%3A%2F%2Feureka3d.vm.fedcloud.eu%2F3d%2F00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764&format=json"/>
 […]
</ore:Aggregation>

<edm:WebResource rdf:about="https://eureka3d.vm.fedcloud.eu/oembed?url=https%3A%2F%2Feureka3d.vm.fedcloud.eu%2F3d%2F00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764&format=json">
        <edm:type>3D</edm:type>
        <edm:rights rdf:resource="http://creativecommons.org/publicdomain/mark/1.0/"/>
        <schema:digitalSourceType rdf:resource="https://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"/>
        <edm:intendedUsage rdf:resource="http://data.europeana.eu/vocabulary/usageArea/Curation"/>
        <dcterms:created>2024</dcterms:created>
        <svcs:has_service rdf:resource="https://eureka3d.vm.fedcloud.eu/oembed"/>
        <dcterms:isFormatOf rdf:resource="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764"/>
    </edm:WebResource>
        
    <svcs:Service rdf:about="https://eureka3d.vm.fedcloud.eu/oembed">
        <dcterms:conformsTo rdf:resource="https://oembed.com/"/>
        <rdfs:label xml:lang="en">Eureka3D Viewer</rdfs:label>
    </svcs:Service>

    
    <edm:WebResource rdf:about="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E9920736861726547756964236439373135383431316466333933663131323235393832636666663339373665636861373435233665663637356366323134343661326366656235653866346139393233333165636865663265233462663463306362306536363632643064353061363230393538363038623032636839323764">
        <edm:type>3D</edm:type>
        <dc:title>High resolution 3D Model of the object</dc:title>
        <dc:creator xml:lang="en">3D Digitisation Company</dc:creator>
        <dc:description xml:lang="en">This model was 3D scanned using X software</dc:description>
        <dc:language>en</dc:language>
        <dcterms:temporal>1868</dcterms:temporal>
        <dc:type rdf:resource="http://data.europeana.eu/vocabulary/modelType/3DMesh"/>
        <edm:rights rdf:resource="http://creativecommons.org/licenses/by-sa/4.0/"/>        
        <schema:digitalSourceType rdf:resource="https://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"/>
        <edm:intendedUsage rdf:resource="http://data.europeana.eu/vocabulary/usageArea/Curation"/>
        <edm:polygonCount>143104084</edm:polygonCount>
        <edm:vertexCount>12345</edm:vertexCount>
        <rdfs:seeAlso rdf:resource="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E430A736861726547756964233538373362666161396464613066373765313264343965346666666336353764636834636135233665663637356366323134343661326366656235653866346139393233333165636865663265233261626461663562346161316433653364353639613632323761363338633363636838366431/content"/>
    </edm:WebResource>

    <edm:WebResource rdf:about="https://datahub.egi.eu/api/v3/onezone/shares/data/00000000007E430A736861726547756964233538373362666161396464613066373765313264343965346666666336353764636834636135233665663637356366323134343661326366656235653866346139393233333165636865663265233261626461663562346161316433653364353639613632323761363338633363636838366431/content">
        <dcterms:conformsTo>pdf</dcterms:conformsTo>
    </edm:WebResource>

[…]
```

</details>
