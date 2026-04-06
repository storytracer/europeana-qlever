
# What happens to persistent identifiers during ingestion?

After successful validation, logic is applied to PIDs to normalise and convert [Persistent identifiers in EDM (definitions)](../../../Europeana%20Data%20Model/EDM%20profiles/Persistent%20identifiers%20in%20EDM%20(definitions).md) values into instances of [Persistent identifiers in EDM (definitions)](../../../Europeana%20Data%20Model/EDM%20profiles/Persistent%20identifiers%20in%20EDM%20(definitions).md) class.

The edm:PersistentIdentifier class contains structured information about the PID, including its canonical and non-canonical forms, and other information, such as the PID scheme and any equivalent PIDs in other schemes. You can find the full list of properties available for edm:PersistentIdentifier class in [Persistent identifiers in EDM (definitions)](https://europeana.atlassian.net/wiki/external/MjU0ZjgzZDA3MjM4NGQ4Nzk1MTA2NjM5OWI5ZGU2YTY).

> [!IMPORTANT]
> **Note about different PID forms**
>
> Some PID schemes allow PIDs to appear in different forms, but also define a canonical form (a standardised version used for consistency). These schemes specify how any valid form can be converted into the  canonical one. This is important because it allows systems to recognise when different-looking PIDs (within the same scheme) actually refer to the same resource.
>
> For example, the following three ARK identifiers all refer to the same resource:
>
> - `ark:/12148/cb12031244g` (canonical form)
> - `https://data.bnf.fr/ark:/12148/cb12031244g`
> - `https://n2t.org/ark:/12148/cb12031244g`

**An example of the result of the normalisation process is shown below:**

***Example - Original value***

```java
<edm:ProvidedCHO rdf:about="..."> 
  <edm:pid>https://ark.bnf.fr/ark:/12148/bpt6k279983</edm:pid>
  […]
</edm:ProvidedCHO>
```

***Example - Normalised value***

*The original value remains in the provider’s proxy, while a reference to the normalised PID (i.e. edm:PersistentIdentifier class) is attached to the edm:pid property in the Europeana’s proxy*

```java
<ore:Proxy rdf:about="#Provider_proxy"> 
  <edm:pid>https://ark.bnf.fr/ark:/12148/bpt6k279983</edm:pid>
  […]
</ore:Proxy>

<ore:Proxy rdf:about="#Europeana_proxy"> 
  <edm:pid rdf:resource="#pid_1"/>
  […]
</ore:Proxy>

<edm:PersistentIdentifier rdf:about="#pid_1">
  <rdf:value>ark:/12148/bpt6k279983</rdf:value>
  <dcterms:creator xml:lang="en">Bibliothèque nationale de France</dcterms:creator>
  <dcterms:created>2019-09-11T08:10:18.452Z</dcterms:created>
  <odrl:hasPolicy rdf:resource="http://ark.bnf.fr/ark:/12148/bpt6k2102478.policy"/>
  <skos:notation>XPTO</skos:notation>
  <edm:hasURL rdf:resource="https://ark.bnf.fr/ark:/12148/bpt6k279983"/>
  <edm:equivalentPID>doi:10.5962/bhl.title.62506</edm:equivalentPID>
  <edm:replacesPID>ark:/12148/XPTO</edm:replacesPID>
  <skos:inScheme rdf:resource="https://arks.org/"/>
</edm:PersistentIdentifier>

<edm:PersistentIdentifierScheme rdf:about="https://arks.org/">
  <dcterms:title>Archival Resource Keys<dcterms:title>
</edm:PersistentIdentifierScheme>
```
