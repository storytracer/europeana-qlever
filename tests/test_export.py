"""Unit tests for export resilience: retry logic and continue-on-failure."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from europeana_qlever.export import (
    _cleanup_partial,
    _is_transient,
    export_all,
    run_query_to_tsv,
)


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
            "bad_query": "SELECT fail",
            "good_query": "SELECT 1",
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
            queries={"q1": "SELECT 1"},
            skip_existing=True,
        )

        assert "q1" in result.succeeded
        assert mock_tsv.call_count == 0  # should have been skipped
