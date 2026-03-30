"""Unit tests for export: RDF term parsing, Parquet conversion, retry logic, continue-on-failure."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import httpx
import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from europeana_qlever.export import (
    _cleanup_partial,
    _is_transient,
    export_all,
    parse_rdf_term,
    run_query_to_tsv,
    tsv_to_parquet,
)
from europeana_qlever.query import QuerySpec


class TestParseRdfTerm:
    """Test rdflib-based RDF term parsing from SPARQL TSV cells."""

    def test_iri(self):
        assert parse_rdf_term("<http://example.org/item/1>") == "http://example.org/item/1"

    def test_iri_https(self):
        assert parse_rdf_term("<https://www.europeana.eu/item/123>") == "https://www.europeana.eu/item/123"

    def test_iri_urn(self):
        assert parse_rdf_term("<urn:isbn:0451450523>") == "urn:isbn:0451450523"

    def test_language_tagged_literal(self):
        assert parse_rdf_term('"Soldiers in the trenches"@en') == "Soldiers in the trenches"

    def test_language_tagged_literal_fr(self):
        assert parse_rdf_term('"Bonjour le monde"@fr') == "Bonjour le monde"

    def test_quoted_literal(self):
        assert parse_rdf_term('"en"') == "en"

    def test_typed_literal_integer(self):
        result = parse_rdf_term('"42"^^<http://www.w3.org/2001/XMLSchema#integer>')
        assert result == "42"

    def test_typed_literal_decimal(self):
        result = parse_rdf_term('"3.14"^^<http://www.w3.org/2001/XMLSchema#decimal>')
        assert result == "3.14"

    def test_escaped_quotes(self):
        assert parse_rdf_term(r'"text with \"quotes\""@en') == 'text with "quotes"'

    def test_bare_value_string(self):
        assert parse_rdf_term("IMAGE") == "IMAGE"

    def test_bare_value_country(self):
        assert parse_rdf_term("Portugal") == "Portugal"

    def test_bare_value_integer(self):
        assert parse_rdf_term("42") == "42"

    def test_empty_string(self):
        assert parse_rdf_term("") == ""

    def test_blank_node(self):
        result = parse_rdf_term("_:b1")
        assert result  # Should produce a non-empty string

    def test_rdflib_roundtrip_uri(self):
        """parse_rdf_term undoes n3() serialization for URIRef."""
        term = URIRef("http://data.europeana.eu/item/123")
        assert parse_rdf_term(term.n3()) == str(term)

    def test_rdflib_roundtrip_literal_lang(self):
        """parse_rdf_term undoes n3() serialization for language-tagged Literal."""
        term = Literal("hello", lang="en")
        assert parse_rdf_term(term.n3()) == str(term)

    def test_rdflib_roundtrip_literal_typed(self):
        """parse_rdf_term undoes n3() serialization for typed Literal."""
        term = Literal("42", datatype=XSD.integer)
        assert parse_rdf_term(term.n3()) == str(term)

    def test_rdflib_roundtrip_literal_plain(self):
        """parse_rdf_term undoes n3() serialization for plain Literal."""
        term = Literal("hello")
        assert parse_rdf_term(term.n3()) == str(term)


class TestIsTransient:
    def test_transport_error(self):
        assert _is_transient(httpx.TransportError("conn reset"))

    def test_timeout_exception(self):
        assert _is_transient(httpx.TimeoutException("timed out"))

    def test_http_502(self):
        response = MagicMock()
        response.status_code = 502
        exc = httpx.HTTPStatusError("bad gateway", request=MagicMock(), response=response)
        assert _is_transient(exc)

    def test_http_503(self):
        response = MagicMock()
        response.status_code = 503
        exc = httpx.HTTPStatusError("unavailable", request=MagicMock(), response=response)
        assert _is_transient(exc)

    def test_http_429(self):
        response = MagicMock()
        response.status_code = 429
        exc = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=response)
        assert _is_transient(exc)

    def test_http_400_not_transient(self):
        response = MagicMock()
        response.status_code = 400
        exc = httpx.HTTPStatusError("bad request", request=MagicMock(), response=response)
        assert not _is_transient(exc)

    def test_value_error_not_transient(self):
        assert not _is_transient(ValueError("oops"))


class TestCleanupPartial:
    def test_removes_existing_file(self, tmp_path: Path):
        f = tmp_path / "test.tsv"
        f.write_text("partial data")
        _cleanup_partial(f)
        assert not f.exists()

    def test_ignores_missing_file(self, tmp_path: Path):
        f = tmp_path / "nonexistent.tsv"
        _cleanup_partial(f)  # should not raise

    def test_removes_multiple(self, tmp_path: Path):
        f1 = tmp_path / "a.tsv"
        f2 = tmp_path / "b.parquet"
        f1.write_text("data")
        f2.write_text("data")
        _cleanup_partial(f1, f2)
        assert not f1.exists()
        assert not f2.exists()


class TestTsvToParquet:
    """End-to-end tests for rdflib + PyArrow TSV→Parquet conversion."""

    def test_all_rdf_forms(self, tmp_path: Path):
        """All SPARQL TSV serialization forms are parsed correctly."""
        tsv = tmp_path / "test.tsv"
        tsv.write_text(
            "?item\t?title\t?lang\t?rights\t?count\n"
            '<http://example.org/1>\t"Hello World"@en\t"en"\t<http://cc.org/by/4.0/>\t42\n'
            '<http://example.org/2>\t"Bonjour"@fr\t"fr"\t<http://cc.org/by/3.0/>\t7\n'
        )
        parquet = tmp_path / "test.parquet"
        count = tsv_to_parquet(tsv, parquet)
        assert count == 2

        rows = duckdb.execute(
            f"SELECT item, title, lang, rights, count FROM '{parquet}'"
        ).fetchall()
        # IRIs: <> stripped
        assert rows[0][0] == "http://example.org/1"
        assert rows[0][3] == "http://cc.org/by/4.0/"
        # Language-tagged literals: quotes + @lang stripped
        assert rows[0][1] == "Hello World"
        assert rows[1][1] == "Bonjour"
        # Quoted literals: quotes stripped
        assert rows[0][2] == "en"
        assert rows[1][2] == "fr"
        # Bare integer values — DuckDB infers as int
        assert rows[0][4] == 42

    def test_plain_literals_unchanged(self, tmp_path: Path):
        tsv = tmp_path / "test.tsv"
        tsv.write_text("?type\t?country\nIMAGE\tPortugal\n")
        parquet = tmp_path / "test.parquet"
        tsv_to_parquet(tsv, parquet)

        rows = duckdb.execute(f"SELECT * FROM '{parquet}'").fetchall()
        assert rows[0] == ("IMAGE", "Portugal")

    def test_empty_cells(self, tmp_path: Path):
        tsv = tmp_path / "test.tsv"
        tsv.write_text("?item\t?opt\n<http://example.org/1>\t\n")
        parquet = tmp_path / "test.parquet"
        count = tsv_to_parquet(tsv, parquet)
        assert count == 1

        rows = duckdb.execute(f"SELECT item, opt FROM '{parquet}'").fetchall()
        assert rows[0][0] == "http://example.org/1"
        # Empty TSV field → empty string or NULL
        assert rows[0][1] is None or rows[0][1] == ""

    def test_empty_tsv(self, tmp_path: Path):
        tsv = tmp_path / "test.tsv"
        tsv.write_text("")
        parquet = tmp_path / "test.parquet"
        count = tsv_to_parquet(tsv, parquet)
        assert count == 0

    def test_question_mark_prefix_stripped(self, tmp_path: Path):
        tsv = tmp_path / "test.tsv"
        tsv.write_text("?item\t?title\nfoo\tbar\n")
        parquet = tmp_path / "test.parquet"
        tsv_to_parquet(tsv, parquet)

        rows = duckdb.execute(f"SELECT item, title FROM '{parquet}'").fetchall()
        assert rows[0] == ("foo", "bar")

    def test_batching(self, tmp_path: Path):
        """Rows exceeding batch_size are correctly handled across batches."""
        tsv = tmp_path / "test.tsv"
        lines = ["?item\t?val"]
        for i in range(150):
            lines.append(f"<http://example.org/{i}>\t{i}")
        tsv.write_text("\n".join(lines) + "\n")
        parquet = tmp_path / "test.parquet"
        count = tsv_to_parquet(tsv, parquet, batch_size=50)
        assert count == 150


class TestRunQueryToTsvRetry:
    @patch("europeana_qlever.export._stream_query")
    @patch("europeana_qlever.export.time.sleep")
    def test_retries_on_transport_error(self, mock_sleep, mock_stream):
        mock_stream.side_effect = [
            httpx.TransportError("connection reset"),
            42,
        ]
        result = run_query_to_tsv("SELECT 1", Path("/tmp/test.tsv"))
        assert result == 42
        assert mock_stream.call_count == 2
        mock_sleep.assert_called_once_with(5)

    @patch("europeana_qlever.export._stream_query")
    @patch("europeana_qlever.export.time.sleep")
    def test_retries_on_timeout(self, mock_sleep, mock_stream):
        mock_stream.side_effect = [
            httpx.TimeoutException("read timeout"),
            100,
        ]
        result = run_query_to_tsv("SELECT 1", Path("/tmp/test.tsv"))
        assert result == 100
        assert mock_stream.call_count == 2

    @patch("europeana_qlever.export._stream_query")
    def test_no_retry_on_non_transient(self, mock_stream):
        mock_stream.side_effect = ValueError("bad query")
        with pytest.raises(ValueError, match="bad query"):
            run_query_to_tsv("SELECT 1", Path("/tmp/test.tsv"))
        assert mock_stream.call_count == 1

    @patch("europeana_qlever.export._stream_query")
    @patch("europeana_qlever.export.time.sleep")
    def test_exhausts_retries(self, mock_sleep, mock_stream):
        mock_stream.side_effect = httpx.TransportError("persistent failure")
        with pytest.raises(httpx.TransportError):
            run_query_to_tsv("SELECT 1", Path("/tmp/test.tsv"))
        assert mock_stream.call_count == 3  # 1 + 2 retries


class TestExportAllContinueOnFailure:
    @patch("europeana_qlever.export.run_query_to_tsv")
    @patch("europeana_qlever.export.tsv_to_parquet")
    def test_continues_past_failure(self, mock_parquet, mock_tsv, tmp_path: Path):
        """If query 1 fails, query 2 should still run."""
        output_dir = tmp_path / "exports"

        # First query fails, second succeeds
        def tsv_side_effect(query, output_path, *args, **kwargs):
            if "fail" in query:
                raise httpx.TransportError("connection lost")
            # Create the TSV file so stat() works
            output_path.write_text("col1\nval1\n")
            return 1

        mock_tsv.side_effect = tsv_side_effect

        def parquet_side_effect(tsv_path, parquet_path, **kwargs):
            parquet_path.write_bytes(b"PAR1fake")
            return 1

        mock_parquet.side_effect = parquet_side_effect

        queries = {
            "bad_query": QuerySpec(name="bad_query", sparql="SELECT fail"),
            "good_query": QuerySpec(name="good_query", sparql="SELECT 1"),
        }

        result = export_all(
            output_dir=output_dir,
            queries=queries,
            qlever_url="http://localhost:7001",
        )

        assert "good_query" in result.succeeded
        assert "bad_query" in result.failed
        assert len(result.parquet_files) == 1

    @patch("europeana_qlever.export.run_query_to_tsv")
    @patch("europeana_qlever.export.tsv_to_parquet")
    def test_skip_existing(self, mock_parquet, mock_tsv, tmp_path: Path):
        output_dir = tmp_path / "exports"
        output_dir.mkdir(parents=True)

        # Pre-create a parquet file
        existing = output_dir / "q1.parquet"
        existing.write_bytes(b"PAR1fake")

        result = export_all(
            output_dir=output_dir,
            queries={"q1": QuerySpec(name="q1", sparql="SELECT 1")},
            skip_existing=True,
        )

        assert "q1" in result.succeeded
        assert mock_tsv.call_count == 0  # should have been skipped
