---
tags:
  - '#faq'
  - '#apidocs'
---

[Europeana APIs Documentation](../Europeana%20APIs%20Documentation.md)

# API FAQ

- [General public](#general-public)
  - [How do I get access to Europeana's APIs?](#how-do-i-get-access-to-europeana-s-apis)
  - [What APIs does Europeana have, and what purpose do they serve?](#what-apis-does-europeana-have-and-what-purpose-do-they-serve)
  - [How often are the Europeana APIs updated?](#how-often-are-the-europeana-apis-updated)
  - [Can I use the data I get from Europeana's API for my own project? Is any data from Europeana's API protected by copyright?](#can-i-use-the-data-i-get-from-europeana-s-api-for-my-own-project-is-any-data-from-europeana-s-api-protected-by-copyright)
  - [How can I get around Same Origin Policy / CORS issues?](#how-can-i-get-around-same-origin-policy-cors-issues)
    - [Cross-Origin Resource Sharing (CORS)](#cross-origin-resource-sharing-cors)
    - [JSON with padding (JSONP)](#json-with-padding-jsonp)
  - [Can I add any cultural heritage data I have to Europeana's database by using the API?](#can-i-add-any-cultural-heritage-data-i-have-to-europeana-s-database-by-using-the-api)
  - [What metadata format does Europeana use to structure its data?](#what-metadata-format-does-europeana-use-to-structure-its-data)
  - [Are there any limits to using the API? How often can I make queries?](#are-there-any-limits-to-using-the-api-how-often-can-i-make-queries)
  - [Are there any client libraries or packages made so I can more easily use the Europeana APIs in different programming languages?](#are-there-any-client-libraries-or-packages-made-so-i-can-more-easily-use-the-europeana-apis-in-different-programming-languages)
  - [How can I download all of the information about an item?](#how-can-i-download-all-of-the-information-about-an-item)
  - [How do I retrieve all of the items from a single institution?](#how-do-i-retrieve-all-of-the-items-from-a-single-institution)
  - [How do I find openly licensed items?](#how-do-i-find-openly-licensed-items)
  - [My API query only returns a certain number of results. How can I see and download all of the results that match my query?](#my-api-query-only-returns-a-certain-number-of-results-how-can-i-see-and-download-all-of-the-results-that-match-my-query)
  - [I am getting the error "It is not possible to paginate beyond the first 1000 search results. Please use cursor-based pagination instead". How do I fix this?](#i-am-getting-the-error-it-is-not-possible-to-paginate-beyond-the-first-1000-search-results-please-use-cursor-based-pagination-instead-how-do-i-fix-this)
  - [I want to analyse the results of my query in some way, but it's hard to do quantitative analysis on these results in RDF or JSON format. How can I get my data into a CSV or a spreadsheet?](#i-want-to-analyse-the-results-of-my-query-in-some-way-but-it-s-hard-to-do-quantitative-analysis-on-these-results-in-rdf-or-json-format-how-can-i-get-my-data-into-a-csv-or-a-spreadsheet)
  - [Can the API return aggregates, such as the number of times something occurs in my search query? E.g. I'd like to know how many objects in my query come from a certain country or how many of my results are in a certain language.](#can-the-api-return-aggregates-such-as-the-number-of-times-something-occurs-in-my-search-query-e-g-i-d-like-to-know-how-many-objects-in-my-query-come-from-a-certain-country-or-how-many-of-my-results-are-in-a-certain-language)
  - [Where do I find the original 'objects' in the metadata of my API result? How can I find and download the image/video/sound/3D object/text object of a record using the API?](#where-do-i-find-the-original-objects-in-the-metadata-of-my-api-result-how-can-i-find-and-download-the-image-video-sound-3d-object-text-object-of-a-record-using-the-api)
- [Data Providers](#data-providers)

---

# General public

## How do I get access to Europeana's APIs?

**Relevant for:** All APIs except for SPARQL

To access the Europeana APIs, you must first obtain an API key. You can find detailed instructions on how to request and use your key on [Accessing the APIs](Accessing%20the%20APIs.md).

## What APIs does Europeana have, and what purpose do they serve?

It's hard to precisely define where one of our APIs starts and where the other one ends, but we've tried to condense our API suite down to this list of APIs that we've separated based on their function. If you know what kind of data you want and/or how you want to find it, you can go through this list and select the API that suits your needs.

- **Search API**: Use the Search API if you want to search our database with a certain query and want a response containing all the items that match that query. This API is what powers our search bar on <http://europeana.eu> . It takes a query as input and responds with a JSON list of records and some limited metadata about those records, in a paginated format.
- **Record API:** The Record API is meant to return all of the information our database has about a single record. This API powers our item pages on <http://europeana.eu> . It takes a record identifier as input and gives you a JSON file with the metadata for that record as output.
- **Entity API**: Use the Entity API if you want to retrieve the information related to a Europeana Linked Open Data (LOD) Entity, if you want to search for related entities using the Suggest method, or if you want to try and resolve an external Linked Open Data term to a corresponding Europeana entity. The Entity API connects you to our Europeana vocabulary containing Linked Open Data terms.
- **Annotations API**: Use the Annotations API if you want to search through annotations that other services or platforms have provided to Europeana, if you want to retrieve all of the information about a single annotation for which you have the annotation identifier, or if you want to push any annotations you have to Europeana to add that information to the records we have in our database. The annotations API allows us to communicate with external platforms and integrations to send and receive enrichments and annotations of our records.
- **IIIF API**: Our IIIF API is our integration of the IIIF Manifest API standard into Europeana. It holds a database with IIIF manifests for almost every record that Europeana has. It takes a record ID as input and gives a IIIF JSON manifest as output. The IIIF API is also used to store and serve full-text metadata for our Newspapers Collection and other records that have full-text transcriptions.
- **Newspapers API**: use our Newspapers API to search the full-text metadata of our Newspapers collection and our other records that have full-text annotations stored. The Newspapers API takes a query as an input and outputs a list of results that match that query, along with where those query terms can be found in the result full-text.
- **User Set API**: Use our User Sets API if you want to interact with the user galleries that our users have created. You can use our User Sets API to search through public galleries, to access the contents of a public gallery, or to make changes to galleries you have permission to change.
- **SPARQL endpoint**: Europeana's SPARQL endpoint allows you to use SPARQL to search through our database. You can create federated searches using our SPARQL endpoint to query different SPARQL endpoints at the same time.

## How often are the Europeana APIs updated?

We deploy new versions of each API quite regularly. These are minor releases in order to fix issues or make small improvements to the existing or new functionality but without breaking backwards compatibility.

For major releases we follow the standard practices:

|                       |                                                                                                                                                                                                                                                                                               |
|:----------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Alpha**             | A release is done when functionality is made available in an early stage for the purpose of receiving feedback from users, which may result on bug fixes or proposals to add, change or remove features. It is expected that not all functionality is made available, just the core features. |
| **Beta**              | This release is done when all product features are completed and all major bugs have been addressed. It may still contain some bugs and potential performance issues, and functionality can still be changed.                                                                                 |
| **Stable (official)** | This release is done when all product features are completed and all major bugs have been addressed. From this point on, any changes made to the functionality need to be backward compatible with previous versions.                                                                         |

## Can I use the data I get from Europeana's API for my own project? Is any data from Europeana's API protected by copyright?

To read the Terms of Use for Europeana's APIs you can consult points 8 through 18 of our [Terms of Use](https://www.europeana.eu/en/rights/terms-of-use).

All metadata from Europeana's APIs are provided as [CC0](https://creativecommons.org/share-your-work/public-domain/cc0/), meaning you can reuse that metadata as you wish without any restrictions. Some of that metadata may link to content from Europeana's partners, like the content linked in the edm:IsShownBy and edm:Object fields. These objects can be used in accordance with the Rights Statement mentioned in the object metadata, in the europeana:rights/edm:rights field. Always check these fields before using the objects linked in Europeana's metadata!

## How can I get around Same Origin Policy / CORS issues?

A client application running on a web browser is typically prohibited from calling methods of an endpoint that is being served under a domain outside its own because of the [same origin policy](http://en.wikipedia.org/wiki/Same_origin_policy). To get around this restriction, we support [CORS](https://pro.europeana.eu/page/intro#CORS) for all the APIs that we offer. For APIs such as the Record API and Search API, we still offer support for the outdated [JSONP](https://pro.europeana.eu/page/intro#JSONP) mechanism. Given that this mechanism has been superseded by CORS, we may stop supporting it in future versions of these APIs so *we strongly recommend all users to shift from JSONP to CORS*.

### Cross-Origin Resource Sharing (CORS)

The [Cross-Origin Resource Sharing](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing) (CORS) is a transparent mechanism using HTTP headers for client applications to call APIs served from a domain outside the one they are being served. To enable CORS, it is only necessary to supply the [Origin HTTP header](https://tools.ietf.org/id/draft-abarth-origin-03.html) at every request with the domain where your application is running. After handling the request, the API will respond back with a set of headers that will tell the browser to lift the restrictions.

### JSON with padding (JSONP)

[JSONP](http://en.wikipedia.org/wiki/JSONP) (JSON with padding) is an older mechanism for getting around the *same origin policy* enforced by browsers. Unlike CORS, it is limited to GET request and works by supplying a client side (JavaScript) callback function that will be called with the respective response.

> *"Under the same origin policy, a web page served from* [*server1.example.com*](http://server1.example.com) *cannot normally connect to or communicate with a server other than* [*server1.example.com*](http://server1.example.com)*. An exception is the HTML script element. Exploiting the open policy for script elements, some pages use them to retrieve JavaScript code that operates on dynamically generated JSON-formatted data from other origins. This usage pattern is known as JSONP. Requests for JSONP retrieve not JSON, but arbitrary JavaScript code. They are evaluated by the JavaScript interpreter, not parsed by a JSON parser." (Wikipedia:* [*JSONP*](http://en.wikipedia.org/wiki/JSONP)*)*

A callback can be added to any JSON-based call by appending &callback=callbackname to the call, where the callbackname should be an existing JavaScript function existing on the client side. The API returns JSONP response, like this one:

<details>
<summary>example JSON callback</summary>

<https://api.europeana.eu/record/v2/>[RECORD\_ID].json?**callback=processEuropeanaSearch**

Which returns

```java
processEuropeanaSearch({
  "apikey":"xxxxx",
  "action":"record.json",
  "success":true,
  "statsDuration":22,
  "requestNumber":8,
  "object": {
    "type":"TEXT",
    "title":["Bibliotheca Indica"],
    "about":"[record ID]",
    ...
  }
})

```

The JSON response is wrapped into your function, and the function use JSON as input parameter, and it immediatelly runs when it returns. In your client you have to define the callback function before you call the API. A client side example:

```java
<script>
function processEuropeanaSearch(json) {
  alert(json.object.title.join(', '));
}
</script>
<script src="https://api.europeana.eu/record/v2/0000/1111.json?callback=processEuropeanaSearch"></script>
```

</details>

## Can I add any cultural heritage data I have to Europeana's database by using the API?

Most of Europeana's APIs are read-only. They're meant to allow you to search for, find, download and re-use digital cultural heritage data from our database. There are, however, ways to enrich our metadata and send information to our APIs. When asking for information from our APIs you're almost always executing a GET request. When sending new information to our APIs, you'll most likely do so using a POST or PUT request.

If you want to add completely new records to Europeana's database, you'll have to go through the ingestion process. To read more about how this process works and how you can join Europeana as a new Data Provider, go to <https://pro.europeana.eu/share-your-data/process>

Europeana APIs that allow for POST requests currently are:

<details>
<summary>Annotations API</summary>

If you're a trusted partner from Europeana, you'll receive an API key that allows you to make POST, PUT and DELETE requests, along with one or more User Tokens allowing you to authenticate yourself as that user. If you want to create a new annotation, here's an example of what that POST request could look like:

`POST  http://annotations.europeana.eu/annotation/ HTTP/1.1`

`Accept: application/ld+json`

`Content-Type: application/ld+json`

`Content-Length: 999`

`{`

`"motivation": "tagging",`

`"bodyValue": "Trombone",`

`"target": "http://data.europeana.eu/item/09102/_UEDIN_214"`

`}`

</details>

<details>
<summary>User Set API</summary>

[[TODO]]

</details>

## What metadata format does Europeana use to structure its data?

Europeana's metadata is structured using the Europeana Data Model, abbreviated as EDM. The metadata we receive from our partner institutions all over Europe are all formatted in different ways using different standards and best practices. We map all of this information to EDM so we can provide one standard metadata model for all digital cultural heritage in Europe.  You can learn about the EDM standard here: <https://pro.europeana.eu/page/edm-documentation> .

Europeana's APIs return metadata using several standard file formats, too. A response from the Search API, for instance, will always be in the JSON format. For some APIs you can choose which metadata format to receive your response in. In the Record API. You can request a response in JSON, JSON-LD, or RDF/XML

<details>
<summary>Example</summary>

Requesting a Record in JSON

`https://api.europeana.eu/record/v2/90402/SK_A_3262.json`

Requesting the same record in RDF

`https://api.europeana.eu/record/v2/90402/SK_A_3262.rdf`

</details>

## Are there any limits to using the API? How often can I make queries?

Europeana gives access to all of its APIs free of charge. All API methods that read information from our databases will always be free to use and will never have limitations posed upon them. That means you can use Europeana's APIs to build platforms, products, apps, services and projects that scale as much as you'd like, for free. You can query our APIs as often as you like without any throttling or limiting. We do ask that you are courteous with your API calls by leaving some time between calls if you are making a bunch of them. Leaving at least a few milliseconds between each request will make it easier for our servers to handle the load.

If you'd like to contribute data to Europeana's database by sending data and metadata to us through our APIs, you'll have to receive specific credentials from us. Please email us at [api@europeana.eu](mailto:api@europeana.eu) to discuss your project and set up a partnership.

Are you building something using Europeana's APIs? Do you have a project or product you're working on that uses our API services as a component? We'd love to hear from you! We can support you and your work in a multitude of ways, from technical support to promotion of your project, or by connecting you to our network of cultural heritage partners.

## Are there any client libraries or packages made so I can more easily use the Europeana APIs in different programming languages?

Yes there are! Most client libraries and packages for Europeana's APIs were made by external users and aren't maintained or verified by Europeana. You can find a list of plugins and libraries here: <https://pro.europeana.eu/page/api-libraries-and-plugins>

## How can I download all of the information about an item?

To retrieve all information in our database about a single Europeana item, use the [Record API](https://pro.europeana.eu/page/record). You'll need the Dataset and Record ID of the item you want to retrieve information from. You can find these identifiers in the URL of the Europeana item you're looking at, formatted as follows: /datasetID/recordID. Then add this information to the base URL <https://api.europeana.eu/record/v2/>.

**Example**: if you want to retrieve all the metadata of this item by Van Gogh: <https://www.europeana.eu/en/item/90402/SK_A_3262>

Your Record API request would be <https://api.europeana.eu/record/v2/90402/SK_A_3262.json>

The response you get will be formatted in JSON by default. You can also retrieve record data in:   
RDF XML: <https://api.europeana.eu/record/v2/90402/SK_A_3262.rdf>

JSON-LD: <https://api.europeana.eu/record/v2/90402/SK_A_3262.jsonld>

## How do I retrieve all of the items from a single institution?

To find all of the items that correspond to a term in a single metadata field, use the Search API. To find out which search fields exist, see the chapter on ['Search Fields' in the Search API documentation](https://pro.europeana.eu/page/search#search-fields). To use a search field, add that search field to either the "query" parameter or the "qf" parameter. To retrieve all the items from a single institution, enter the name of that institution in the 'DATA\_PROVIDER' field.

**Example**: to retrieve all of the data from the Rijksmuseum:

<https://api.europeana.eu/record/v2/search.json?query=DATA_PROVIDER:%22Rijksmuseum%22>

## How do I find openly licensed items?

To search for openly licensed items on Europeana, use the Search API.

Fill in the required fields: wskey with your API key, and query with what you want to search for. Then add the reusability parameter and set it to open. This will restrict your search to only openly licensed content. You can see which copyright licenses correspond to the which parameter in [this table](https://pro.europeana.eu/page/search#reusability). When you set the reusability field to 'open' the API will only return items with a copyright license of Public Domain Mark, CC0, CC BY, or CC BY-SA.

Example: I want to find all works about or from Leonardo Da Vinci that are openly licensed

**Request:** <https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&reusability=open>

## My API query only returns a certain number of results. How can I see and download all of the results that match my query?

Almost all Europeana APIs have a rows parameter that dictates how many rows of results you will get in your API response. This row parameter will have a default value when you don't specify anything. For the Search API, the default row parameter value is 12. Even if you get thousands of results for your query, the Search API will only return the first 12 by default. You can change the rows parameter value by using the rows field in your query. The rows parameter often has a maximum value. For the Search API, the maximum value is 100. To get the first 100 results in response to your query, set rows=100. If you want to see the next 100 results, you can use the start parameter. This parameter dictates hows many search results to skip. If you have 200 items as a response to your request, using rows=100 will allow you to see the first 100 items. To see the next 100 items, set start to 101 and rows at 100. This will skip the first 100 results and show you the next 100 results, from result number 101 to result number 200.

Example:  I want to receive the first 300 items of a query with all works from or about Leonardo da Vinci.

**Request:**

<https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)>

This query has over 2000 results. By default, it will return the first 12. To get the first 100 results:

<https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&rows=100>

To get the next 100 results:

<https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&rows=100&start=101>

And to get results numbers 201-300:

<https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&rows=100&start=201>

## I am getting the error "It is not possible to paginate beyond the first 1000 search results. Please use cursor-based pagination instead". How do I fix this?

To get results from the Search API beyond the first 1000, you need to use [cursor-based pagination](https://pro.europeana.eu/page/search#pagination-cursor). To start cursor-based pagination, add cursor=\* to your query URL. To go to the next page of results, Take the nextCursor value from the response and pass it to the cursor parameter to paginate to the next page (you will need to urlescape the key).

When the nextCursor value is not returned anymore, you have reached the end of the search result set.

Example: I want to get the first 100 results after the first 1000 results of a query with all works from or about Leonardo da Vinci.

<https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&rows=100&start=1001>

When executing this query, you get the error "It is not possible to paginate beyond the first 1000 search results. Please use cursor-based pagination instead"

To start using cursor-based pagination:

[https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&rows=100&cursor=\*](https://api.europeana.eu/record/v2/search.json?query=who:(Leonardo%20da%20Vinci)&rows=100&cursor=*)

 This shows the first 100 results. To paginate to results 101-200, take the nextCursor value from that result and reinsert it in your query:

## I want to analyse the results of my query in some way, but it's hard to do quantitative analysis on these results in RDF or JSON format. How can I get my data into a CSV or a spreadsheet?

## Can the API return aggregates, such as the number of times something occurs in my search query? E.g. I'd like to know how many objects in my query come from a certain country or how many of my results are in a certain language.

## Where do I find the original 'objects' in the metadata of my API result? How can I find and download the image/video/sound/3D object/text object of a record using the API?

# Data Providers

This section provides guidance for data providers on how to use the Europeana APIs to assess and analyse their collections.

- all data providers per provider: <https://api.europeana.eu/record/v2/search.json?query=PROVIDER:"Daguerreobase"&profile=facets&facet=DATA_PROVIDER&rows=0>
- content and metadata tier per provider: <https://api.europeana.eu/record/v2/search.json?query=PROVIDER:"CulturaItalia"&profile=facets&facet=contentTier&facet=metadataTier&rows=0>
- content and metadata tier per dataset: [https://api.europeana.eu/record/v2/search.json?query=edm\_datasetName%3A2022706\*&profile=facets&facet=contentTier&facet=metadataTier&rows=0](https://api.europeana.eu/record/v2/search.json?query=edm_datasetName%3A2022706*&profile=facets&facet=contentTier&facet=metadataTier&rows=0)
- all datasets with LCNAF vocabulary: [https://api.europeana.eu/record/v2/search.json?query=skos\_concept:\*id.loc.gov\*&profile=facets&facet=edm\_datasetName&rows=0](https://api.europeana.eu/record/v2/search.json?query=skos_concept:*id.loc.gov*&profile=facets&facet=edm_datasetName&rows=0)
- example record with LCNAF vocabulary: [https://api.europeana.eu/record/v2/search.json?query=skos\_concept:\*id.loc.gov\*](https://api.europeana.eu/record/v2/search.json?query=skos_concept:*id.loc.gov*)
- europeana id of enriched records: [https://api.europeana.eu/record/v2/search.json?query=edm\_datasetName:718\_Museu\_AjuntamentDeGirona\*+AND+skos\_concept:\*vocab.getty.edu\*+AND+((skos\_concept:\*wikidata.org\*)+OR+(edm\_agent:\*wikidata.org\*))&profile=facets&facet=europeana\_id&f.europeana\_id.facet.limit=2000&rows=0](https://api.europeana.eu/record/v2/search.json?query=edm_datasetName:718_Museu_AjuntamentDeGirona*+AND+skos_concept:*vocab.getty.edu*+AND+((skos_concept:*wikidata.org*)+OR+(edm_agent:*wikidata.org*))&profile=facets&facet=europeana_id&f.europeana_id.facet.limit=2000&rows=0)
- number of records in a dataset: <https://api.europeana.eu/record/v2/search.json?&query=edm_datasetName:9200519_Ag_BnF_Gallica_typedoc_manuscrits&profile=facets&facet=edm_datasetName&rows=0&f.edm_datasetName.facet.limit=10>
- IIIF resources in a dataset**:** [https://api.europeana.eu/record/v2/search.json?query=edm\_datasetName:15515\*&rows=0&start=1&facet=wr\_svcs\_hasservice&profile=facets&f.wr\_svcs\_hasservice.facet.limit=2000](https://api.europeana.eu/record/v2/search.json?query=edm_datasetName:15515*&rows=0&start=1&facet=wr_svcs_hasservice&profile=facets&f.wr_svcs_hasservice.facet.limit=2000)
- IIIF resources with manifest: [https://api.europeana.eu/record/v2/search.json?rows=0&query=wr\_svcs\_hasservice:\*+AND+wr\_dcterms\_isReferencedBy:\*&profile=facets&facet=edm\_datasetName&f.edm\_datasetName.facet.limit=2000](https://api.europeana.eu/record/v2/search.json?rows=0&query=wr_svcs_hasservice:*+AND+wr_dcterms_isReferencedBy:*&profile=facets&facet=edm_datasetName&f.edm_datasetName.facet.limit=2000)
- IIIF resources without manifest**:** [https://api.europeana.eu/record/v2/search.json?rows=0&query=wr\_svcs\_hasservice:\*+AND+NOT+wr\_dcterms\_isReferencedBy:\*&profile=facets&facet=edm\_datasetName&f.edm\_datasetName.facet.limit=2000](https://api.europeana.eu/record/v2/search.json?rows=0&query=wr_svcs_hasservice:*+AND+NOT+wr_dcterms_isReferencedBy:*&profile=facets&facet=edm_datasetName&f.edm_datasetName.facet.limit=2000)
