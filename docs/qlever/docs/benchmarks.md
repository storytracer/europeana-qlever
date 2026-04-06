# Benchmarks

QLever's performance has been evaluated extensively and compared to other graph
database that implement the RDF and SPARQL standards.

[DBLP benchmark](https://github.com/ad-freiburg/qlever/wiki/QLever-performance-evaluation-and-comparison-to-other-SPARQL-engines):
Performance comparison of Oxigraph, Jena, Stardog, GraphDB, Blazegraph, Virtuoso, and QLever on the DBLP knowledge graph (500 million triples). Evaluates loading time, index size, and average query time. Exact command lines to reproduce the results are provided.

[Wikidata benchmark](https://www.wikidata.org/wiki/Wikidata:Scaling_Wikidata/Benchmarking/Final_Report):
Performance comparison of QLever, Virtuoso, and MillenniumDB on the complete Wikidata dataset (20 billion triples), for a variety of queries. Independent study sponsored by Wikimedia CH.

[Sparqloscope benchmark](https://qlever.cs.uni-freiburg.de/evaluation):
Performance comparison of QLever, Virtuoso, MillenniumDB, GraphDB, Blazegraph,
and Jena on DBLP (500 million triples) and Wikidata Truthy (8 billion triples),
on a wide variety of queries spanning the full spectrum of SPARQL features.
Interactive display of individual results and queries. This is the most
comprehensive evaluation to date.
