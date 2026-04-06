# Update

QLever supports [SPARQL 1.1 Update](https://www.w3.org/TR/sparql11-update/) and the [SPARQL 1.1 Graph Store HTTP Protocol](https://www.w3.org/TR/sparql11-http-rdf-update/) for updating the data at runtime after building an index.

## Configuration

**Required**: The execution of update operations requires an access token. You can set the access
token via `ACCESS_TOKEN` in the `[server]` section of the QLeverfile or via the
command-line option `--access-token`. When the server is started with `--no-access-check`, no
access token is required.

**Optional**: To persist the updates across server restarts, set
`PERSIST_UPDATES = true` in the `[server]` section of the QLeverfile or use the
command-line option `--persist-updates`.

## SPARQL 1.1 Update

### Via HTTP

The access token can be provided either via the query parameter
`access-token=...` or via the HTTP header `Authorization: Bearer ...`. Here is
an example using `curl`:

=== "Access token as query parameter"
    ```bash
    curl -X "POST"
         -H "Content-Type: application/sparql-update"
         -d "DELETE WHERE { ?s ?p ?o }"
         "http://localhost:7019?access-token={token}"
    ```
=== "Access token as header"
    ```bash
    curl -X "POST"
         -H "Content-Type: application/sparql-update"
         -H "Authorization: Bearer {token}"
         -d "DELETE WHERE { ?s ?p ?o }"
         "http://localhost:7019"
    ```

### Via the QLever UI

You can insert the access token into the `Access Token` field under the
`Backend Information`. You can use the editor to write and execute updates,
analogous to how you would do for queries. In particular, syntax highlighting,
formatting and basic autocompletion are available. When an access token has
been entered, additional buttons for the privileged operations `Reset Updates`
and `Clear Cache (Complete)` become available below the editor.


## SPARQL 1.1 Graph Store HTTP Protocol

Here are some example `curl` commands for the different HTTP methods, extended
by the non-standard `TSOP` method.

=== "GET"
    ```bash title="Get all triples from a graph"
    curl -X "GET" \
         -H "Accept: text/turtle" \
         "http://localhost:7019?graph=http://example.com/person/1.ttl"
    ```
=== "PUT"
    ```bash title="Replace all triples in a graph"
    curl -X "PUT" \
         -H "Content-Type: text/turtle" \
         -H "Authorization: Bearer {token}" \
         --data-binary @graph.ttl \
         "http://localhost:7019?graph=http://example.com/person/1.ttl"
    ```
=== "DELETE"
    ```bash title="Delete all triples from a graph"
    curl -X "DELETE" \
         -H "Authorization: Bearer {token}" \
         "http://localhost:7019?graph=http://example.com/person/1.ttl"
    ```
=== "POST"
    ```bash title="Add triples to a graph"
    curl -X "POST" \
         -H "Content-Type: text/turtle" \
         -H "Authorization: Bearer {token}" \
         --data-binary @graph.ttl \
         "http://localhost:7019?graph=http://example.com/person/1.ttl"
    ```
=== "TSOP"
    ```bash title="Delete triples from a graph"
    curl -X "TSOP" \
         -H "Content-Type: text/turtle" \
         -H "Authorization: Bearer {token}" \
         --data-binary @graph.ttl \
         "http://localhost:7019?graph=http://example.com/person/1.ttl"
    ```
=== "HEAD"
    ```bash title="Same as GET, but without response body"
    curl -I "http://localhost:7019?graph=http://example.com/person/1.ttl"
    ```


## Updates involving large files

When sending large files with `curl`, you should use `--data-binary @file`
instead of `--data @file` or `--data-urlencode @file`. The first sends the data
as is, the last both process the input before sending it, which leads to
problems for large files.
