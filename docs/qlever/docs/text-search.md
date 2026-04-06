
# Text Search in QLever

QLever allows the combination of SPARQL and full-text search in a collection of
text records. The text records can be the literals from the RDF data, or
additional text that is not part of the RDF data, or both.

The additional text can contain mentions of entities from the RDF data. A
SPARQL+Text query can then specify co-occurrence of words from the text with
entities from the RDF data. This is a powerful concept. See below for the input
format and an example query.

## Building a combined RDF and text index

The `qlever` script makes it very easy to build a text index and to start a
server using that text index. Just download the script using `pip install qlever`
or from <https://github.com/ad-freiburg/qlever-control> and follow the
instructions from `qlever --help`. As a quick summary, there are the following
commands and options related to SPARQL+Text:

```
qlever index --text-index [OPTIONS] ...
qlever add-text-index [OPTIONS]
qlever start --use-text-index [OPTIONS] ...
```

Note that `qlever index` builds both the RDF index and the text index in one
go, while `qlever add-text-index` adds a text index to an already existing RDF
index. Use `qlever <command> --help` to get detailed information about the
options for each of these commands.

## Format of the text input files

This section describes the format of the input files for additional text that
is not part of the RDF data. These text records may contain mentions of
entities from the RDF data. This information can be passed to QLever via two
files, a so-called "wordsfile" and a so-called "docsfile". The wordsfile
specifies which words and entities occur in which text record. The docsfile is
just the text record that is returned in query results.

The wordsfile is a tab-separated file with one line per word occurrence, in
the following format:

```
word    is_entity    record_id   score
```

Here is an example excerpt for the text record `In 1928, Fleming discovered
penicillin`, assuming that the id of the text record is `17`and that the
scientist and the drug are annotated with the IRIs of the corresponding
entities in the RDF data. Note that the IRI can be syntactically completely
different from the words used to refer to that entity in the text.

```
In                  0   17   1
1928                0   17   1
<Alexander_Fleming> 1   17   1
Fleming             0   17   1
discovered          0   17   1
penicillin          0   17   1
<Penicillin>        1   17   1
```

The docsfile is a tab-separated file with one line per text record, in the
following format:

```
record_id  text
```

For example, for the sentence above:

```
17   Alexander Fleming discovered penicillin, a drug.
```

## Simple Text Search

QLever supports a simple text search using the special predicates `ql:contains-entity` and `ql:contains-word`. Additionally, a version with more configuration options is available: see [Advanced Text Search](#advanced-text-search).

??? note "Example SPARQL+Text queries"

    Here is an example query on Wikidata, which returns astronauts that are
    mentioned in a sentence from the English Wikipedia that also contains the word
    "moon" and the prefix "walk", ordered by the number of matching sentences.

    ```sparql {data-demo-engine="wikidata"}
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX ql: <http://qlever.cs.uni-freiburg.de/builtin-functions/>
    SELECT ?astronaut ?astronaut_name (COUNT(?text) AS ?count) (SAMPLE(?text) AS ?example_text) WHERE {
      ?astronaut wdt:P106 wd:Q11631 .
      ?astronaut rdfs:label ?astronaut_name .
      FILTER (LANG(?astronaut_name) = "en")
      ?text ql:contains-entity ?astronaut .
      ?text ql:contains-word "moon walk*" .
    }
    GROUP BY ?astronaut ?astronaut_name
    ORDER BY DESC(?count)
    ```

## Advanced Text Search

QLever also provides a Text Search `SERVICE` which provides additional control over text search compared to `ql:contains-word` and `ql:contains-entity`. It allows binding the score and prefix match of the searches to self defined variables. This feature is accessed using the `SERVICE` keyword and the service IRI `<https://qlever.cs.uni-freiburg.de/textSearch/>`.

### Full Syntax

The complete structure of a Text Search with every predicate used is as follows:

```sparql
PREFIX textSearch: <https://qlever.cs.uni-freiburg.de/textSearch/>

SELECT * WHERE {
  SERVICE textSearch: {
    ?t textSearch:contains [
      textSearch:word "prefix*" ;
      textSearch:prefix-match ?prefix_match ;
      textSearch:score ?prefix_score
    ] .
    ?t textSearch:contains [
      textSearch:entity ?entity ;
      textSearch:score ?entity_score
    ] .
  }
}
```

### Parameters

`textSearch:contains`: Connects a text variable to a configuration for text search. One text variable can be connected to multiple configurations leading to multiple searches on the same text where the searches are later joined. One config shouldn't be linked to multiple text variables.

`textSearch:word`: Defines the word or prefix used in the text search. Doesn't support multiple words separated by spaces like `ql:word` does. It is instead intended to use multiple searches.

`textSearch:entity`: Defines the entity used in text search. Can be a literal or IRI for fixed entities or a variable to get matches for multiple entities. An entity search on a text variable needs at least one word search on the same variable.

`textSearch:prefix-match` (optional): Binds prefix completion to a variable that can be used outside of the `SERVICE`. If not specified the column will be omitted. Should only be used in a word search configuration where the word is a prefix.

`textSearch:score` (optional): Binds score to a variable that can be used outside of the `SERVICE`. If not specified the column will be omitted.

A configuration is either a word search configuration specified with `textSearch:word` or an entity search configuration with `textSearch:entity`.

??? note "Example queries"

    **Example 1:  Simple word search**

    A simple word search:

    ```sparql
    PREFIX textSearch: <https://qlever.cs.uni-freiburg.de/textSearch/>

    SELECT * WHERE {
      SERVICE textSearch: {
        ?t textSearch:contains [ textSearch:word "word" ] .
      }
    }
    ```

    The output columns are: `?t`

    **Example 2: Prefix search**

    A simple prefix search where the prefix variable is bound:

    ```sparql
    PREFIX textSearch: <https://qlever.cs.uni-freiburg.de/textSearch/>

    SELECT * WHERE {
      SERVICE textSearch: {
        ?t textSearch:contains [ textSearch:word "prefix*" ; textSearch:prefix-match ?prefix_match ] .
      }
    }
    ```

    The output columns are: `?t`, `?prefix_match`

    **Example 3: Score word search with filter**

    A word search where the score variable is bound and later used to filter the result:

    ```sparql
    PREFIX textSearch: <https://qlever.cs.uni-freiburg.de/textSearch/>

    SELECT * WHERE {
      SERVICE textSearch: {
        ?t textSearch:contains [ textSearch:word "word" ; textSearch:score ?score ] .
      }
      FILTER(?score > 1)
    }
    ```

    The output columns are: `?t`, `?score`

    **Example 4: Simple entity search**

    A simple entity search, where an entity is contained in a text together with a word:

    ```sparql
    PREFIX textSearch: <https://qlever.cs.uni-freiburg.de/textSearch/>

    SELECT * WHERE {
      SERVICE textSearch: {
        ?t textSearch:contains [ textSearch:word "word" ] .
        ?t textSearch:contains [ textSearch:entity ?e ] .
      }
    }
    ```

    The output columns are: `?t`, `?e`

    **Example 5: Multiple word and or prefix search**

    A text search with multiple word and prefix searches:

    ```sparql
    PREFIX textSearch: <https://qlever.cs.uni-freiburg.de/textSearch/>

    SELECT * WHERE {
      SERVICE textSearch: {
        ?t textSearch:contains [ textSearch:word "word" ] .
        ?t textSearch:contains [ textSearch:word "prefix*" ] .
        ?t textSearch:contains [ textSearch:word "term" ] .
      }
    }
    ```

    The output columns are: `?t`

## Error Handling

The Text Search feature will throw errors in the following scenarios:

- **No Basic Graph Pattern**: If the inner syntax of the `SERVICE` isn't only triples, an error will be raised.
- **Faulty Triples**: If predicates aren't used with subjects and objects of correct type, an error will be raised. E.g. `textSearch:word` with a variable as object.
- **Multiple Occurrences of Predicates**: If predicates occur multiple times in one configuration, an error will be raised.
- **Config linked to multiple Text Variables**: If manually defining a configuration variable and linking that to different text variables, an error will be raised. It is good practice to use the [ ] syntax and thus not manually defining the configuration variables.
- **Missing necessary Predicates**: If predicate `textSearch:contains` is missing inside the `SERVICE`, an error will be raised. If a configuration doesn't contain exactly one occurrence of either `textSearch:word` or `textSearch:entity`, an error will be raised.
- **Word and Entity Search in one Configuration**: If one configuration contains both predicates `textSearch:word` and `textSearch:entity` , an error will be raised.
- **Entity Search on a Text without Word Search**: If a configuration with `textSearch:entity` is connected to a text variable that is not connected to a configuration with `textSearch:word`, an error will be raised.
- **Empty Word Search**: If the object of `textSearch:word` is an empty literal, an error will be raised.
