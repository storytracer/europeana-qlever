
[Europeana APIs Documentation](../../Europeana%20APIs%20Documentation.md) > [API Suite](../API%20Suite.md)

# SPARQL API Documentation

The SPARQL API allows you to use the SPARQL Query language to interact with Europeana’s database, and lets you explore connections between Europeana data and outside data sources, like [VIAF](http://viaf.org/), [Iconclass](http://www.iconclass.org/), Getty Vocabularies ([AAT](http://www.getty.edu/research/tools/vocabularies/lod/)), [Geonames](http://www.geonames.org/), [Wikidata](https://www.wikidata.org/), and [DBPedia](http://wiki.dbpedia.org/). If you are looking for a way to delve into the structured metadata of Europeana (for instance, to ask the question "What are all the French 18th-century painters with at least five artworks available through Europeana'), this is the API for you. If you want to simply search Europeana in an unstructured way (for instance 'give me all results for the word 'cat'), then using the [Search API Documentation](Search%20API%20Documentation.md) is a better choice. SPARQL is part of Europeana's [Page not accessible (ID: 2386100230)] initiative.

Before starting to use this API, we recommend reading the introduction page for an overview of the [Page not accessible (ID: 2385313809)] and reading the [Terms of Use](https://www.europeana.eu/rights/terms-of-use#europeana-api). If you want to get started with this API, go directly to the [Getting Started](#getting-started) section or try it out directly on the [Console](https://sparql.europeana.eu).

If you want to learn more about SPARQL, we recommend the [sparql.dev](https://sparql.dev/) tutorial and [Wikidata SPARQL tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial). We also recommend the [SPARQL for humanists](http://matthewlincoln.net/2014/07/10/sparql-for-humanists.html) page to help you dive into the SPARQL Query Language.

> [!WARNING]
> ### The SPARQL API is powered by a separate database (Virtuoso) which reflects the state of the Europeana datasets as of July 2017. We are working on a monthly update for this endpoint so that it is kept in sync with the main Europeana APIs.

- [Getting Started](#getting-started)
- [More examples of SPARQL Queries](#more-examples-of-sparql-queries)

## Getting Started

### Things to know before starting

- Europeana data is represented as triples:

```java
<subject> <predicate> <object>
```

Each subject, predicate and an object represent a node within Europeana’s network of resources. These statements are usually represented as URIs to which certain labels might correspond.

For instance, the following triple

```java
<http://data.europeana.eu/item/90402/RP_P_1984_87> <http://purl.org/dc/terms/created> "1827 - 1832" .
```

explains that for the item that you can find at [this URL](http://data.europeana.eu/item/90402/RP_P_1984_87) (the subject) has a metadata field called dcTerms:created (the predicate) that is filled with the value “1827-1832”. The cultural heritage object at that URL was, in other words, created between 1827 and 1832.

- A SPARQL query requires the declaration of PREFIXes that are shortcuts to the labels of given predicates.
- The different packages of information contained in the Europeana data are described using several classes in the Europeana Data Model (EDM). We invite you to consult our [Page not accessible (ID: 2386100230)] page and the [Page not accessible (ID: 2385313809)] if you need more details on the model.
- When formulating a query don’t forget to adjust the LIMIT value which indicates the number of results to be returned by the query. Note that the query may take longer if the number of results asked is high.
- If you set a LIMIT value but still want to be able to select the range of results you will get within the dataset, adjust the OFFSET value.

### Where is the endpoint available?

```java
https://sparql.europeana.eu/
```

### A first query

### 1. Add your prefixes by selecting them in the SPARQL editor as described above.

<details>
<summary>Example of Step 1: Add your Prefixes</summary>

For instance a selection of the namespaces dc, edm and ore will give you:

```java
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
```

</details>

### 2. Then SELECT the things you want to find and define names for these variables.

<details>
<summary>Example of Step 2: create a SELECT clause</summary>

We want all the results with a title, a creator, a media URL and a year.

```java
SELECT ?title ?creator ?mediaURL ?year
```

</details>

### 3. Define the variables

<details>
<summary>Example of step 3: define your variables</summary>

```java
WHERE {
  ?item edm:type "SOUND" ;
      ore:proxyIn ?proxy;
      dc:title ?title ;
      dc:creator ?creator .
  ?proxy edm:isShownBy ?mediaURL .
  ?EuropeanaProxy edm:year ?year .
}
```

In this example, you restrict the results to the resources with the edm:type SOUND.

</details>

### 4. Define a LIMIT

<details>
<summary>example of step 4: define a LIMIT</summary>

```java
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT ?title ?creator ?mediaURL ?date
WHERE {
  ?CHO edm:type "SOUND" ;
      ore:proxyIn ?proxy;
      dc:title ?title ;
      dc:creator ?creator ;
      dc:date ?date .
  ?proxy edm:isShownBy ?mediaURL .
}
LIMIT 100
```

You obtain all the first 100 SOUND resources which have a title, a creator, a media URL and a year.

</details>

### How to define more complex queries

You can start defining more complex queries which will group, list, filter or order your results. The commands COUNT, GROUP BY and ORDER BY can be used for this purpose.

<details>
<summary>Example of how to use ORDER BY</summary>

For instance we want to order our results by year (ascending order)

```java
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT ?title ?creator ?mediaURL ?date
WHERE {
  ?CHO edm:type "SOUND" ;
      ore:proxyIn ?proxy;
      dc:title ?title ;
      dc:creator ?creator;
      dc:date ?date .
  ?proxy edm:isShownBy ?mediaURL .
  FILTER (?date > "1780" && ?date < "1930")
}
ORDER BY asc (?date)
LIMIT 100
```

You will notice that this type of query takes longer as we are asking to the database to not only return results but also to order them.

</details>

## More examples of SPARQL Queries

<details>
<summary>Example 1: List of data providers which contributed content to Europeana</summary>

```java
PREFIX edm: <http://www.europeana.eu/schemas/edm/>

SELECT ?DataProvider
WHERE { ?Aggregation edm:dataProvider ?DataProvider }`
```

</details>

<details>
<summary>Example 2: List of datasets from Italy</summary>

```java
PREFIX edm: <http://www.europeana.eu/schemas/edm/>

SELECT DISTINCT ?Dataset
WHERE {
  ?Aggregation edm:datasetName ?Dataset ;
      edm:country "Italy"
}
```

</details>

<details>
<summary>Example 3: Objects provided to Europeana from the 18th and from France</summary>

```java
PREFIX ore: <http://www.openarchives.org/ore/terms/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>

SELECT DISTINCT ?ProvidedCHO ?year
WHERE {
  ?Aggregation edm:aggregatedCHO ?ProvidedCHO ;
      edm:country "France" .
  ?Proxy ore:proxyFor ?ProvidedCHO ;
      edm:year ?year .
  FILTER (?year > "1700" && ?year < "1800")
}
ORDER BY asc(?year)
LIMIT 100
```

</details>

<details>
<summary>Example 4: Listing of edm:Agent</summary>

```java
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>

SELECT ?Agent
WHERE { ?Agent rdf:type edm:Agent }
LIMIT 100
```

</details>

<details>
<summary>Example 5: Objects provided to Europeana linking to edm:Place</summary>

```java
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>

SELECT DISTINCT ?ProvidedCHO
WHERE {
  ?Place rdf:type edm:Place .
  ?Proxy ?property ?Place ;
      ore:proxyIn ?Aggregation .
  ?Aggregation edm:aggregatedCHO ?ProvidedCHO
}
```

</details>

<details>
<summary>Example 6: List certain attributes of an item using Dublin Core terms</summary>

[Try this on the wikidata query service](https://query.wikidata.org/#%23Get%20information%20of%20Europeana%20item%20using%20federated%20query%0APREFIX%20dc%3A%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2F%3E%0APREFIX%20edm%3A%20%3Chttp%3A%2F%2Fwww.europeana.eu%2Fschemas%2Fedm%2F%3E%0APREFIX%20ore%3A%20%3Chttp%3A%2F%2Fwww.openarchives.org%2Fore%2Fterms%2F%3E%0A%0ASELECT%20%2a%20WHERE%20%7B%0A%20%20BIND%28%3Chttp%3A%2F%2Fdata.europeana.eu%2Fproxy%2Fprovider%2F91622%2Fraa_kmb_16000200042758%3E%20as%20%3Fp854%29%20%20%0A%20%20SERVICE%20%3Chttp%3A%2F%2Fsparql.europeana.eu%2F%3E%20%7B%0A%20%20%20%7B%0A%20%20%20%20%20%20%20%20%20%3Fp854%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Fterms%2Fcreated%3E%20%3Fcreated%20.%0A%20%20%20%20%20%20%20%20%20%3Fp854%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Fidentifier%3E%20%3Fidentifier%20.%0A%20%20%20%20%20%20%20%20%20%3Fp854%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Fpublisher%3E%20%3Fpublisher%20.%0A%20%20%20%20%20%20%20%20%20%3Fp854%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Frights%3E%20%3Frights%20.%0A%20%20%20%20%20%20%20%20%20%3Fp854%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Ftitle%3E%20%3Ftitle%20.%0A%20%20%20%20%20%20%20%20%20%3Fp854%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Fdescription%3E%20%3Fdescription%20.%0A%20%20%20%20%20%7D%0A%20%20%7D%0A%7D)

```java
  #Get information of Europeana item using federated query
PREFIX dc: <http: 1.1="" dc="" elements="" purl.org="">
PREFIX edm: <http: edm="" schemas="" www.europeana.eu="">
PREFIX ore: <http: ore="" terms="" www.openarchives.org="">

SELECT * WHERE {
  BIND(<http: 91622="" data.europeana.eu="" provider="" proxy="" raa_kmb_16000200042758=""> as ?p854)  
  SERVICE <http: sparql.europeana.eu=""> {
   {
         ?p854 <http: created="" dc="" purl.org="" terms=""> ?created .
         ?p854 <http: 1.1="" dc="" elements="" identifier="" purl.org=""> ?identifier .
         ?p854 <http: 1.1="" dc="" elements="" publisher="" purl.org=""> ?publisher .
         ?p854 <http: 1.1="" dc="" elements="" purl.org="" rights=""> ?rights .
         ?p854 <http: 1.1="" dc="" elements="" purl.org="" title=""> ?title .
         ?p854 <http: 1.1="" dc="" description="" elements="" purl.org=""> ?description .
     }
  }
}
  </http:></http:></http:></http:></http:></http:></http:></http:></http:></http:></http:>
```

</details>

<details>
<summary>Example 7: Objects provided to Europeana linking to skos:Concept from the Getty target vocabulary</summary>

```java
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>

SELECT DISTINCT ?ProvidedCHO
WHERE {
  ?Concept rdf:type skos:Concept .
  FILTER strstarts(str(?Concept), "http://vocab.getty.edu/aat/") .
  ?Proxy ?property ?Concept ;
      ore:proxyIn ?Aggregation .
  ?Aggregation edm:aggregatedCHO ?ProvidedCHO
}
LIMIT 100
```

</details>

<details>
<summary>Example 8: Use a federated query</summary>

### to extract Europeana's DC:subjects for a certain item and translate them to other vocabulary URIs

[Try this on the Sophox query service](https://sophox.org/#%23%20Find%20Commons%20category%20suggestions%20for%20a%20Commons%20file%20using%20subjects%20stored%20in%20Europeana%0A%23%201.)%20Bind%20identifier%20of%20the%20photo%20to%20variable%0A%23%202.)%20Read%20subjects%20in%20Finnish%20of%20photo%20defined%20by%20identifier%20from%20Europeana%0A%23%203.)%20Translate%20subjects%20to%20YSO%20ontology%20using%20Finto-service.%20%0A%23%204.)%20Translate%20YSO%20items%20to%20Wikidata%20items%20using%20Wikidata%20and%20read%20Commons%20categories%0A%0ASELECT%20*%20WITH%20%7B%0A%20%20SELECT%20*%20WHERE%20%7B%20%20%20%20%20%0A%20%20%20%20%20%23%201.)%20Bind%20identifier%20of%20the%20photo%20to%20variable%0A%20%20%20%20%20BIND(%22HK19700502%3A254%22%20as%20%3Fidentifier)%0A%0A%20%20%20%20%20%23%202.)%20Read%20subjects%20in%20Finnish%20of%20photo%20defined%20by%20identifier%20from%20Europeana%0A%20%20%20%20%20SERVICE%20%3Chttp%3A%2F%2Fsparql.europeana.eu%2F%3E%20%7B%0A%20%20%20%20%20%20%20%3Feuropeana%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Fidentifier%3E%20%3Fidentifier%20.%0A%20%20%20%20%20%20%20%3Feuropeana%20%3Chttp%3A%2F%2Fpurl.org%2Fdc%2Felements%2F1.1%2Fsubject%3E%20%3Fsubject%20.%20%20%20%20%20%20%20%0A%20%20%20%20%20%7D%0A%20%20%7D%0A%7D%20AS%20%25europeana%0AWHERE%20%7B%0A%20%20INCLUDE%20%25europeana%20.%20%0A%20%20%0A%20%20%23%203.)%20Translate%20subjects%20to%20YSO%20ontology%20using%20Finto-service.%20%0A%20%20SERVICE%20%3Chttp%3A%2F%2Fapi.finto.fi%2Fsparql%3E%20%7B%0A%20%20%20%20%3Fyso%20skos%3AprefLabel%20%3Fsubject%20%3B%0A%20%20%20%20skos%3AinScheme%20%3Chttp%3A%2F%2Fwww.yso.fi%2Fonto%2Fyso%2F%3E%0A%20%20%7D%0A%20%20%20%0A%20%20%23%204.)%20Translate%20YSO%20items%20to%20Wikidata%20items%20using%20Wikidata%20and%20read%20Commons%20categories%0A%20%20BIND(REPLACE(STR(%3Fyso)%2C%20%22http%3A%2F%2Fwww.yso.fi%2Fonto%2Fyso%2Fp%22%2C%20%22%22)%20as%20%3Fyso_number)%0A%20%20SERVICE%20%3Chttps%3A%2F%2Fquery.wikidata.org%2Fsparql%3E%20%20%7B%0A%20%20%20%20%3Fwikidata%20wdt%3AP2347%20%3Fyso_number%20.%0A%20%20%20%20%3Fwikidata%20wdt%3AP373%20%3Fcommonscat%20%20%0A%20%20%7D%0A%7D)

```java
  # Find Commons category suggestions for a Commons file using subjects stored in Europeana
# 1.) Bind identifier of the photo to variable
# 2.) Read subjects in Finnish of photo defined by identifier from Europeana
# 3.) Translate subjects to YSO ontology using Finto-service. 
# 4.) Translate YSO items to Wikidata items using Wikidata and read Commons categories

SELECT * WITH {
  SELECT * WHERE {     
     # 1.) Bind identifier of the photo to variable
     BIND("HK19700502:254" as ?identifier)

     # 2.) Read subjects in Finnish of photo defined by identifier from Europeana
     SERVICE <http: sparql.europeana.eu=""> {
       ?europeana <http: 1.1="" dc="" elements="" identifier="" purl.org=""> ?identifier .
       ?europeana <http: 1.1="" dc="" elements="" purl.org="" subject=""> ?subject .       
     }
  }
} AS %europeana
WHERE {
  INCLUDE %europeana . 
  
  # 3.) Translate subjects to YSO ontology using Finto-service. 
  SERVICE <http: api.finto.fi="" sparql=""> {
    ?yso skos:prefLabel ?subject ;
    skos:inScheme <http: onto="" www.yso.fi="" yso="">
  }
   
  # 4.) Translate YSO items to Wikidata items using Wikidata and read Commons categories
  BIND(REPLACE(STR(?yso), "http://www.yso.fi/onto/yso/p", "") as ?yso_number)
  SERVICE <https: query.wikidata.org="" sparql="">  {
    ?wikidata wdt:P2347 ?yso_number .
    ?wikidata wdt:P373 ?commonscat  
  }
}
</https:></http:></http:></http:></http:></http:>
```

</details>

### Credits

The initial pilots were set up by [Ontotext](http://www.ontotext.com/) under the framework of the [Europeana Creative](https://pro.europeana.eu/project/europeana-creative-project) project and using the [Ontotext GraphDB](http://graphdb.ontotext.com/) semantic repository (which has been replaced by Virtuoso).
