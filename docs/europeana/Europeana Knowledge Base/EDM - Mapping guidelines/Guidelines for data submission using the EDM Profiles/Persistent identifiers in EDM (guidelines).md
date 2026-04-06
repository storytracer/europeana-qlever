
# Persistent identifiers in EDM (guidelines)

We encourage data partners to include [Glossary of terms](../../Persistent%20identifiers/Glossary%20of%20terms.md) for their resources in the metadata. This strengthens the role of existing identifiers in the data space and ensures your resources remain reliably referenced. By adopting PIDs at source and sharing them through data exchange activities, you help maintain the stability of these services and make your resources easier to find, cite and reuse. For example, many Europeana services (such as, User Galleries, Liked items, partnerships like Transcribathon and Crowdsourcing platforms) currently rely on stable object references in order to work properly.

> [!TIP]
> The full definition of the EDM profile for Persistent Identifiers (potentially including elements not to be contributed by data providers) is available [here](https://europeana.atlassian.net/wiki/x/OgC7ww).

# Steps for providing PIDs for aggregated resources

- [Step 1: Identify existing PIDs for aggregated resources](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3283812357#Step-1%3A-Identify-existing-PIDs-for-aggregated-resources)
- [Step 2: Include all known PIDs in EDM](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3283812357#Step-2%3A-Include-all-known-PIDs-in-EDM)
- [Step 3: Use PIDs as resource identifiers](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3283812357#Step-3%3A-Use-PIDs-as-resource-identifiers)
- [Step 4: Provide information about new PID schemes](https://europeana.atlassian.net/wiki/spaces/EF/pages/edit-v2/3283812357#Step-4%3A-Provide-information-about-new-PID-schemes)

> [!IMPORTANT]
> The definitions of the terms **MUST**, **MUST NOT**, **SHOULD**, etc. used in this document can be found at <https://tools.ietf.org/html/rfc2119>.

## Step 1: Identify existing PIDs for aggregated resources

As part of your workflow for obtaining and mapping source data, determine whether resources, such as the provided Cultural Heritage Objects (`edm:ProvidedCHO`) or any of the media resources (`edm:WebResource`) have a PID.

## Step 2: Include all known PIDs in EDM

When a PID exists for a described resource, you SHOULD supply it as a literal value using the `edm:pid` property. This property can be attached to:

- `edm:ProvidedCHO`
- `edm:WebResource`

To offer flexibility and reduce complexity for providers, the value of `edm:pid` can be any valid form of a PID. Providers are also allowed to include multiple instances of the `edm:pid` property to inform users about all available forms of the same PID.

*Example of an ARK identifier for provided Cultural Heritage Object:*

```java
<edm:ProvidedCHO rdf:about="XPTO"> 
  <edm:pid>https://ark.bnf.fr/ark:/12148/bpt6k279983</edm:pid>
  […]
</edm:ProvidedCHO>
```

### Mapping recommendations

> [!IMPORTANT]
> **Choose the right class for the PID and be mindful of granularity of resources**

Make sure you provide the PID in the EDM class that corresponds to the resource it identifies. Different representations of the same resource, for example a physical painting and its digital image, may each have their own PID. If the provided CHO is a physical painting, the PID for the painting should be included in the `edm:ProvidedCHO`, while the PID for the digital image (if it exists) should be included in the corresponding `edm:WebResource`.

Similarly, ensure that the PID actually belongs to the resource you are describing, not to a broader collection or related resource. The scope of the PID (e.g. a whole publication, a single issue of a journal or an individual object) should match the scope of the provided resource. For example, if you are providing individual journal issues, you should not include a PID that identifies the entire journal series.

> [!IMPORTANT]
> **Provide all existing PIDs for the resource**

If a resource has PIDs from different schemes, it is strongly recommended to provide all of them, as this information helps us detect duplicates in our database and consolidate resources from multiple sources or aggregation paths.

## Step 3: Use PIDs as resource identifiers

In addition to providing PID in the `edm:pid` property, we encourage using the PID also as the RDF identifiers of EDM resources (i.e. as `rdf:about` attribute of the relevant EDM class), as shown in the example below.

*Example of an ARK identifier provided as* `rdf:about` *of provided Cultural Heritage Object:*

```java
<edm:ProvidedCHO rdf:about="https://ark.bnf.fr/ark:/12148/bpt6k279983"> 
  <edm:pid>https://ark.bnf.fr/ark:/12148/bpt6k279983</edm:pid>
  […]
</edm:ProvidedCHO>
```

## Step 4: Provide information about new PID schemes

Persistent identifiers are validated during ingestion against the [PID scheme registry](https://europeana.atlassian.net/wiki/x/IgC4ww), a maintained list of identifier schemes we recognise as persistent.

If the supplied PID conforms to one of the registry’s recognised schemes, based on its matching pattern, it is [normalised](https://europeana.atlassian.net/wiki/x/GAC7ww). If the match is not found, the PID is flagged during ingestion and ultimately excluded from the data. This process ensures that only trustworthy PIDs are disseminated in the data space and that they are presented in a consistent and reliable way.

If you or the institution you work with uses a PID scheme that is not currently listed in the PID Scheme Registry, you are invited to submit information about it using this [form](https://europeana.atlassian.net/servicedesk/customer/portal/5/group/11/create/168).

The scheme will be reviewed and assessed against the [PID policy for the data space](https://europeana.atlassian.net/wiki/x/A4Clwg). Based on this evaluation, it may be added to the registry.

*Example of the ARK scheme from the registry: a match between the value provided in* `edm:pid` *and the ARK scheme is determined using the regular expression defined in the* `edm:matchingPattern` *property*

```java
<edm:PersistentIdentifierScheme rdf:about="https://arks.org/">
  <dcterms:title>Archival Resource Key (ARK)</dcterms:title>
  <rdfs:seeAlso rdf:resource="https://arks.org/"/>
  <doap:maintainer>ARK Alliance</doap:maintainer>
  <edm:matchingPattern>https?://ark\.bnf\.fr/ark:(/?[0-9]+)(/[a-z0-9=~\*\+@_$%\-]+)(/[a-z0-9=~\*\+@_$%\-/\.]+)?</edm:matchingPattern>
  <edm:canonicalPattern>ark:${1}${2}${3}</edm:canonicalPattern>
  <edm:resolvablePattern>https://n2t.net/${0}</edm:resolvablePattern>
</edm:PersistentIdentifierScheme>
```
