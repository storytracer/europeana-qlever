"""Unit tests for export resilience: retry logic, continue-on-failure, and ?-stripping."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from europeana_qlever.export import (
    _build_select_clause,
    _cleanup_partial,
    _is_transient,
    _read_tsv_header,
    _strip_question_mark_aliases,
    export_all,
    run_query_to_tsv,
    tsv_to_parquet,
)
from europeana_qlever.query import QuerySpec


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


class TestQuestionMarkStripping:
    def test_read_tsv_header(self, tmp_path: Path):
        tsv = tmp_path / "test.tsv"
        tsv.write_text("?item\t?title\t?type\nval1\tval2\tval3\n")
        headers = _read_tsv_header(tsv)
        assert headers == ["?item", "?title", "?type"]

    def test_read_tsv_header_no_prefix(self, tmp_path: Path):
        tsv = tmp_path / "test.tsv"
        tsv.write_text("item\ttitle\ttype\n")
        headers = _read_tsv_header(tsv)
        assert headers == ["item", "title", "type"]

    def test_strip_aliases_with_prefix(self):
        result = _strip_question_mark_aliases(["?item", "?title", "?type"])
        assert result is not None
        assert '"?item" AS "item"' in result
        assert '"?title" AS "title"' in result

    def test_strip_aliases_no_prefix(self):
        result = _strip_question_mark_aliases(["item", "title", "type"])
        assert result is None

    def test_strip_aliases_mixed(self):
        result = _strip_question_mark_aliases(["?item", "count"])
        assert result is not None
        assert '"?item" AS "item"' in result
        assert '"count"' in result


class TestBuildSelectClause:
    def test_strips_question_marks_and_iri_brackets(self):
        result = _build_select_clause(["?item", "?title", "?type"])
        # All columns get IRI stripping + ?-prefix removal
        assert 'AS "item"' in result
        assert 'AS "title"' in result
        assert 'AS "type"' in result
        assert "LIKE '<%%>'" in result

    def test_no_question_mark_prefix(self):
        result = _build_select_clause(["item", "title"])
        assert 'AS "item"' in result
        assert 'AS "title"' in result

    def test_end_to_end_parquet(self, tmp_path: Path):
        """IRI brackets are stripped and non-IRI values pass through."""
        tsv = tmp_path / "test.tsv"
        tsv.write_text(
            "?item\t?title\t?rights\t?count\n"
            "<http://example.org/1>\tHello\t<http://cc.org/by/4.0/>\t42\n"
            "<http://example.org/2>\tWorld\t<http://cc.org/by/3.0/>\t7\n"
        )
        parquet = tmp_path / "test.parquet"
        count = tsv_to_parquet(tsv, parquet)
        assert count == 2

        import duckdb
        rows = duckdb.execute(
            f"SELECT item, title, rights, count FROM '{parquet}'"
        ).fetchall()
        assert rows[0][0] == "http://example.org/1"
        assert rows[0][1] == "Hello"
        assert rows[0][2] == "http://cc.org/by/4.0/"
        assert rows[1][0] == "http://example.org/2"

    def test_preserves_integer_types(self, tmp_path: Path):
        """Numeric columns are not cast to VARCHAR by IRI stripping."""
        tsv = tmp_path / "test.tsv"
        tsv.write_text(
            "?item\t?completeness\n"
            "<http://example.org/1>\t5\n"
            "<http://example.org/2>\t10\n"
        )
        parquet = tmp_path / "test.parquet"
        tsv_to_parquet(tsv, parquet)

        import duckdb
        types = duckdb.execute(
            f"SELECT typeof(item), typeof(completeness) FROM '{parquet}' LIMIT 1"
        ).fetchone()
        assert types[0] == "VARCHAR"
        assert types[1] == "BIGINT"

    def test_null_and_empty_values(self, tmp_path: Path):
        """NULL and empty values are not mangled by IRI stripping."""
        tsv = tmp_path / "test.tsv"
        tsv.write_text("?item\t?opt\n<http://example.org/1>\t\n")
        parquet = tmp_path / "test.parquet"
        count = tsv_to_parquet(tsv, parquet)
        assert count == 1

        import duckdb
        rows = duckdb.execute(
            f"SELECT item, opt FROM '{parquet}'"
        ).fetchall()
        assert rows[0][0] == "http://example.org/1"
        # Empty TSV field → NULL or empty string
        assert rows[0][1] is None or rows[0][1] == ""


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
