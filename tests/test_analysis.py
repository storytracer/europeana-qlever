"""Tests for the analysis module."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from europeana_qlever.analysis import (
    OperationNode,
    QueryAnalysis,
    _walk_algebra,
    analyze_query,
    flatten_tree,
    inject_limit,
    parse_algebra,
    parse_tree,
    render_markdown,
    render_static_markdown,
    static_analyze_query,
)


# ---------------------------------------------------------------------------
# inject_limit
# ---------------------------------------------------------------------------

class TestInjectLimit:
    def test_no_existing_limit(self):
        sparql = "SELECT * WHERE { ?s ?p ?o }\nGROUP BY ?s"
        result = inject_limit(sparql, 1000)
        assert "LIMIT 1000" in result

    def test_replace_larger_limit(self):
        sparql = "SELECT * WHERE { ?s ?p ?o }\nLIMIT 50000"
        result = inject_limit(sparql, 1000)
        assert "LIMIT 1000" in result
        assert "50000" not in result

    def test_keep_smaller_limit(self):
        sparql = "SELECT * WHERE { ?s ?p ?o }\nLIMIT 500"
        result = inject_limit(sparql, 1000)
        assert "LIMIT 500" in result

    def test_keep_equal_limit(self):
        sparql = "SELECT * WHERE { ?s ?p ?o }\nLIMIT 1000"
        result = inject_limit(sparql, 1000)
        assert "LIMIT 1000" in result

    def test_case_insensitive(self):
        sparql = "SELECT * WHERE { ?s ?p ?o }\nlimit 50000"
        result = inject_limit(sparql, 1000)
        assert "LIMIT 1000" in result


# ---------------------------------------------------------------------------
# parse_tree
# ---------------------------------------------------------------------------

SAMPLE_TREE = {
    "description": "SORT by ?item",
    "result_rows": 1000,
    "result_cols": 5,
    "estimated_size": 1200,
    "estimated_operation_cost": 500,
    "operation_time": 120,
    "original_operation_time": 120,
    "cache_status": "computed",
    "was_cached": False,
    "status": "fully materialized",
    "details": {"sort_column": "?item"},
    "children": [
        {
            "description": "JOIN on ?proxy",
            "result_rows": 5000,
            "result_cols": 8,
            "estimated_size": 200,
            "estimated_operation_cost": 300,
            "operation_time": 80,
            "original_operation_time": 80,
            "cache_status": "computed",
            "was_cached": False,
            "status": "fully materialized",
            "details": {},
            "children": [
                {
                    "description": "INDEX_SCAN for ?proxy",
                    "result_rows": 10000,
                    "result_cols": 3,
                    "estimated_size": 10000,
                    "estimated_operation_cost": 100,
                    "operation_time": 15,
                    "original_operation_time": 15,
                    "cache_status": "computed",
                    "was_cached": False,
                    "status": "fully materialized",
                    "details": {},
                    "children": [],
                },
            ],
        },
    ],
}


class TestParseTree:
    def test_root_node(self):
        tree = parse_tree(SAMPLE_TREE)
        assert tree.description == "SORT by ?item"
        assert tree.time_ms == 120
        assert tree.result_rows == 1000
        assert tree.estimated_size == 1200
        assert tree.cache_status == "computed"

    def test_children_parsed(self):
        tree = parse_tree(SAMPLE_TREE)
        assert len(tree.children) == 1
        join = tree.children[0]
        assert join.description == "JOIN on ?proxy"
        assert len(join.children) == 1

    def test_deep_child(self):
        tree = parse_tree(SAMPLE_TREE)
        scan = tree.children[0].children[0]
        assert scan.description == "INDEX_SCAN for ?proxy"
        assert scan.result_rows == 10000
        assert scan.children == []

    def test_cached_uses_original_time(self):
        node = {
            "description": "CACHED OP",
            "result_rows": 100,
            "result_cols": 2,
            "estimated_size": 100,
            "estimated_operation_cost": 50,
            "operation_time": 0,
            "original_operation_time": 45,
            "cache_status": "cached_pinned",
            "was_cached": True,
            "status": "fully materialized",
            "details": {},
            "children": [],
        }
        tree = parse_tree(node)
        assert tree.time_ms == 45

    def test_missing_fields_default(self):
        node = {"description": "MINIMAL"}
        tree = parse_tree(node)
        assert tree.time_ms == 0
        assert tree.result_rows == 0
        assert tree.children == []


# ---------------------------------------------------------------------------
# flatten_tree
# ---------------------------------------------------------------------------

class TestFlattenTree:
    def test_depth_first_order(self):
        tree = parse_tree(SAMPLE_TREE)
        flat = flatten_tree(tree)
        assert len(flat) == 3
        assert flat[0][0] == 0  # root depth
        assert flat[1][0] == 1  # JOIN depth
        assert flat[2][0] == 2  # INDEX_SCAN depth

    def test_descriptions_in_order(self):
        tree = parse_tree(SAMPLE_TREE)
        flat = flatten_tree(tree)
        descs = [op.description for _, op in flat]
        assert descs == [
            "SORT by ?item",
            "JOIN on ?proxy",
            "INDEX_SCAN for ?proxy",
        ]

    def test_single_node(self):
        node = OperationNode(
            description="LEAF",
            time_ms=10,
            result_rows=5,
            result_cols=1,
            estimated_size=5,
            estimated_cost=5,
            cache_status="computed",
            status="fully materialized",
            details={},
            children=[],
        )
        flat = flatten_tree(node)
        assert len(flat) == 1
        assert flat[0] == (0, node)


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def _make_analysis(self, name="test_query"):
        tree = parse_tree(SAMPLE_TREE)
        return QueryAnalysis(
            name=name,
            sparql="SELECT ?item WHERE { ?s ?p ?o }",
            description="A test query",
            total_time="1.23s",
            compute_time="1.10s",
            planning_time_ms=15,
            index_scans_planning_ms=8,
            result_size=1000,
            columns=["?item"],
            tree=tree,
            warnings=["Operation #2: estimation off"],
        )

    def test_contains_header(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "# QLever Query Performance Analysis" in md

    def test_contains_query_section(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "## test_query" in md

    def test_contains_timing_table(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "### Timing" in md
        assert "1.23s" in md
        assert "1.10s" in md

    def test_contains_execution_tree(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "### Execution Tree" in md
        assert "SORT by ?item" in md
        assert "JOIN on ?proxy" in md

    def test_contains_bottlenecks(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "### Top 5 Slowest Operations" in md

    def test_contains_warnings(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "### Warnings" in md
        assert "estimation off" in md

    def test_contains_sparql(self):
        md = render_markdown([self._make_analysis()], "http://localhost:7001", 1000)
        assert "```sparql" in md
        assert "SELECT ?item" in md

    def test_error_query(self):
        qa = QueryAnalysis(
            name="broken",
            sparql="SELECT broken",
            description="",
            total_time="",
            compute_time="",
            planning_time_ms=None,
            index_scans_planning_ms=None,
            result_size=0,
            columns=[],
            tree=None,
            error="QLever returned 400",
        )
        md = render_markdown([qa], "http://localhost:7001", 1000)
        assert "**Error:**" in md
        assert "400" in md

    def test_multiple_queries(self):
        md = render_markdown(
            [self._make_analysis("q1"), self._make_analysis("q2")],
            "http://localhost:7001",
            1000,
        )
        assert "## q1" in md
        assert "## q2" in md


# ---------------------------------------------------------------------------
# analyze_query (with mocked HTTP)
# ---------------------------------------------------------------------------

MOCK_RESPONSE = {
    "query": "SELECT ?item WHERE { ?s ?p ?o } LIMIT 1000",
    "res": [],
    "selected": ["?item"],
    "resultsize": 1000,
    "time": {"computeResult": "110ms", "total": "123ms"},
    "runtimeInformation": {
        "query_execution_tree": SAMPLE_TREE,
        "meta": {
            "time_query_planning": 15,
            "time_index_scans_query_planning": 8,
        },
    },
}


class TestAnalyzeQuery:
    def test_success(self):
        mock_resp = httpx.Response(200, json=MOCK_RESPONSE)
        with patch("europeana_qlever.analysis.httpx.post", return_value=mock_resp):
            result = analyze_query(
                "test", "SELECT ?item WHERE { ?s ?p ?o }",
                "Test query", "http://localhost:7001", 600,
            )
        assert result.error is None
        assert result.name == "test"
        assert result.result_size == 1000
        assert result.tree is not None
        assert result.tree.description == "SORT by ?item"

    def test_http_error(self):
        mock_resp = httpx.Response(400, text="Bad query")
        with patch("europeana_qlever.analysis.httpx.post", return_value=mock_resp):
            result = analyze_query(
                "bad", "INVALID", "Bad query",
                "http://localhost:7001", 600,
            )
        assert result.error is not None
        assert "400" in result.error

    def test_estimation_warnings(self):
        """JOIN has estimated=200, actual=5000 → 0.04× ratio → should warn."""
        mock_resp = httpx.Response(200, json=MOCK_RESPONSE)
        with patch("europeana_qlever.analysis.httpx.post", return_value=mock_resp):
            result = analyze_query(
                "test", "SELECT ?item WHERE { ?s ?p ?o }",
                "Test", "http://localhost:7001", 600,
            )
        # JOIN: estimated 200, actual 5000 → 0.04× (< 0.1) → warning
        join_warnings = [w for w in result.warnings if "JOIN" in w]
        assert len(join_warnings) == 1
        assert "200" in join_warnings[0]
        assert "5000" in join_warnings[0]


# ---------------------------------------------------------------------------
# Static analysis
# ---------------------------------------------------------------------------

SIMPLE_SPARQL = """\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?s ?title WHERE {
  ?s a <http://example.org/Item> .
  ?s dc:title ?title .
}
"""

OPTIONAL_SPARQL = """\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
SELECT ?s ?title ?creator WHERE {
  ?s a <http://example.org/Item> .
  OPTIONAL { ?s dc:title ?title }
  OPTIONAL { ?s dc:creator ?creator }
}
"""

NESTED_OPTIONAL_SPARQL = """\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?s ?label WHERE {
  ?s a <http://example.org/Item> .
  OPTIONAL {
    ?s dc:creator ?creator .
    OPTIONAL {
      ?creator skos:prefLabel ?label .
      OPTIONAL {
        ?label <http://example.org/script> ?script
      }
    }
  }
}
"""

AGGREGATE_SPARQL = """\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?s
  (SAMPLE(?_title) AS ?title)
  (GROUP_CONCAT(DISTINCT ?_subject; SEPARATOR="|") AS ?subjects)
  (GROUP_CONCAT(DISTINCT ?_date; SEPARATOR="|") AS ?dates)
  (GROUP_CONCAT(DISTINCT ?_lang; SEPARATOR="|") AS ?languages)
  (GROUP_CONCAT(DISTINCT ?_creator; SEPARATOR="|") AS ?creators)
WHERE {
  ?s dc:title ?_title .
  OPTIONAL { ?s dc:subject ?_subject }
  OPTIONAL { ?s dc:date ?_date }
  OPTIONAL { ?s dc:language ?_lang }
  OPTIONAL { ?s dc:creator ?_creator }
}
GROUP BY ?s
"""

NOT_EXISTS_SPARQL = """\
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
SELECT ?proxy WHERE {
  ?proxy a edm:ProvidedCHO .
  FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }
}
"""


class TestWalkAlgebra:
    def test_depth_tracking(self):
        translated = parse_algebra(SIMPLE_SPARQL)
        nodes = list(_walk_algebra(translated.algebra))
        depths = [d for d, _ in nodes]
        assert depths[0] == 0  # root
        assert max(depths) > 0  # has children


class TestStaticAnalyzeQuery:
    def test_simple_query(self):
        sa = static_analyze_query("simple", SIMPLE_SPARQL, "A simple query")
        assert sa.error is None
        assert sa.triple_patterns == 2
        assert sa.optional_count == 0
        assert sa.optional_max_depth == 0
        assert sa.warnings == []

    def test_optional_counting(self):
        sa = static_analyze_query("opt", OPTIONAL_SPARQL, "")
        assert sa.optional_count == 2
        assert sa.optional_max_depth == 1

    def test_nested_optional_warning(self):
        sa = static_analyze_query("nested", NESTED_OPTIONAL_SPARQL, "")
        assert sa.optional_max_depth >= 3
        depth_warnings = [w for w in sa.warnings if "Deep OPTIONAL" in w]
        assert len(depth_warnings) == 1

    def test_filter_and_bind_counting(self):
        sparql = """\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?s ?label WHERE {
  ?s dc:title ?title .
  FILTER(LANG(?title) = "en")
  BIND(STR(?title) AS ?label)
}
"""
        sa = static_analyze_query("fb", sparql, "")
        assert sa.filter_count >= 1
        assert sa.bind_count >= 1

    def test_aggregates(self):
        sa = static_analyze_query("agg", AGGREGATE_SPARQL, "")
        assert "SAMPLE" in sa.aggregates
        assert "GROUPCONCAT" in sa.aggregates
        assert len(sa.group_by_vars) == 1
        assert "?s" in sa.group_by_vars
        gc_count = sum(1 for a in sa.aggregates if a == "GROUPCONCAT")
        assert gc_count == 4
        gc_warnings = [w for w in sa.warnings if "GROUP_CONCAT" in w]
        assert len(gc_warnings) == 1

    def test_not_exists(self):
        sa = static_analyze_query("ne", NOT_EXISTS_SPARQL, "")
        assert sa.not_exists_count >= 1
        ne_warnings = [w for w in sa.warnings if "NOT EXISTS" in w]
        assert len(ne_warnings) == 1

    def test_parse_error(self):
        sa = static_analyze_query("bad", "NOT SPARQL AT ALL {{{", "")
        assert sa.error is not None
        assert "Parse error" in sa.error

    def test_items_enriched_real_query(self):
        """Parse the actual items_enriched query from QueryBuilder."""
        from europeana_qlever.query import QueryBuilder

        qb = QueryBuilder()
        sparql = qb.items_enriched()
        sa = static_analyze_query("items_enriched", sparql, "")
        assert sa.error is None
        assert sa.triple_patterns > 5
        assert sa.optional_count > 5
        assert sa.variables > 15
        assert len(sa.aggregates) > 3


class TestRenderStaticMarkdown:
    def _make_static(self, name="test_query"):
        return static_analyze_query(name, AGGREGATE_SPARQL, "A test query")

    def test_contains_header(self):
        md = render_static_markdown([self._make_static()])
        assert "# Static SPARQL Query Analysis" in md

    def test_contains_metrics_table(self):
        md = render_static_markdown([self._make_static()])
        assert "### Complexity Metrics" in md
        assert "Triple patterns" in md
        assert "OPTIONALs" in md

    def test_contains_sparql(self):
        md = render_static_markdown([self._make_static()])
        assert "```sparql" in md

    def test_contains_warnings(self):
        sa = static_analyze_query("nested", NESTED_OPTIONAL_SPARQL, "")
        md = render_static_markdown([sa])
        assert "### Structural Warnings" in md

    def test_error_query(self):
        sa = static_analyze_query("bad", "NOT SPARQL {{{", "")
        md = render_static_markdown([sa])
        assert "**Error:**" in md
