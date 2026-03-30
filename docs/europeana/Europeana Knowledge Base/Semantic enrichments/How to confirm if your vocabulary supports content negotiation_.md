
[Semantic enrichments](../Semantic%20enrichments.md)

# How to confirm if your vocabulary supports content negotiation?

Content negotiation is a mechanism defined in the HTTP specification that makes it possible to serve different representations of a resource using the same URI, so that user agents can indicate what kind(s) of representation(s) they prefer and how well they can understand them. More precisely, the user agent provides an [Accept HTTP header](http://tools.ietf.org/html/rfc7231#section-5.3) that lists acceptable media types and associated quality factors, the server is then able to supply the representation of the resource that best fits the user agent's needs. A concrete example is your own browser which indicates its preference for HTML formats (ie. “`text/html,application/xhtml+xml,application/xml`") so that it can display a page to an end-user, while a data consumer might otherwise indicate its preference for machine readable formats such as XML or JSON.

## How to?

### Direct approach

The user agent performs an HTTP GET request on a URI identifying a non-information resource. If the user agent prefers an RDF/XML representation of the resource, it sends an “`Accept: application/rdf+xml`" header along with the request.

```java
GET http://viaf.org/viaf/110233335 HTTP/1.1
Accept: application/rdf+xml
```

The server responds with a HTTP “200 OK” to the user agent with a RDF/XML resource containing the description of the original resource URI.

```java
HTTP/1.x 200 OK
Content-Type: application/rdf+xml; charset=UTF-8

<?xml version="1.0" encoding="UTF-8"?>
... remaining XML content ...
```

### 303 redirect approach

![](../../attachments/4f287e6a-01da-476f-b81f-5c7dbc8e2bd3.png)

Alternative to responding directly to the user agent with a HTTP “`200 OK`", the server can also redirect with an HTTP "`303 See Other`" pointing to an URL which can serve directly the resource.

```java
HTTP/1.x 303 See Other
Location: http://www.wikidata.org/entity/Q604667
Content-Type: application/rdf+xml; charset=UTF-8
```

Upon receiving the response, the user agent now asks the server to GET a representation of this information resource, requesting again `application/rdf+xml`.

```java
GET https://www.wikidata.org/wiki/Special:EntityData/Q604667.rdf HTTP/1.1
Accept: application/rdf+xml
```

The server will respond now with a HTTP “`200 OK`" to the user agent with a RDF/XML resource containing the description of the original resource URI.

```java
HTTP/1.x 200 OK
Content-Type: application/rdf+xml; charset=UTF-8

<?xml version="1.0" encoding="UTF-8"?>
... remaining XML content ...
```

## How can I test if my resource is content negotiable?

You can use a Linked Data validator such as [Vapour](http://uriburner.com:8000/vapour) which will run several tests to see how your service is compliant with the content negotiation rules, but you can also test yourself using simple tools such as [Postman](https://www.postman.com/) (on Windows) or [Curl](https://curl.se/) (on Linux) and replicate the requests that were presented in this page.
