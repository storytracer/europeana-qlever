"""Unit tests for pipeline state tracking, result dataclasses, and logging."""

import json
from pathlib import Path

import pytest

from europeana_qlever.state import (
    ExportResult,
    MergeResult,
    PipelineState,
    StageState,
    setup_logging,
)


class TestMergeResult:
    def test_error_rate_no_zips(self):
        r = MergeResult(total_zips=0)
        assert r.error_rate == 0.0

    def test_error_rate_all_ok(self):
        r = MergeResult(
            total_zips=100,
            processed_zips=[f"f{i}.zip" for i in range(100)],
        )
        assert r.error_rate == 0.0

    def test_error_rate_some_failures(self):
        r = MergeResult(
            total_zips=100,
            processed_zips=[f"f{i}.zip" for i in range(95)],
            failed_zips=[f"bad{i}.zip" for i in range(5)],
        )
        assert r.error_rate == pytest.approx(0.05)


class TestExportResult:
    def test_defaults(self):
        r = ExportResult()
        assert r.succeeded == []
        assert r.failed == {}
        assert r.parquet_files == []


class TestStageState:
    def test_roundtrip(self):
        s = StageState(
            status="complete",
            completed_at="2026-01-01T00:00:00+00:00",
            processed_zips=["a.zip", "b.zip"],
            failed_zips=["c.zip"],
            chunks_written=3,
        )
        d = s.to_dict()
        s2 = StageState.from_dict(d)
        assert s2.status == "complete"
        assert s2.processed_zips == ["a.zip", "b.zip"]
        assert s2.failed_zips == ["c.zip"]
        assert s2.chunks_written == 3

    def test_from_dict_defaults(self):
        s = StageState.from_dict({})
        assert s.status == "pending"
        assert s.processed_zips == []

    def test_minimal_serialization(self):
        """Pending stage with no data should serialize minimally."""
        s = StageState()
        d = s.to_dict()
        assert d == {"status": "pending"}


class TestPipelineState:
    def test_fresh(self):
        state = PipelineState.fresh()
        assert state.started_at
        assert state.updated_at

    def test_mark_complete(self):
        state = PipelineState.fresh()
        state.mark_complete("merge")
        assert state.is_complete("merge")
        assert not state.is_complete("export")

    def test_mark_failed(self):
        state = PipelineState.fresh()
        state.mark_failed("index", "segfault")
        stage = state.get_stage("index")
        assert stage.status == "failed"
        assert stage.error == "segfault"

    def test_update_merge(self):
        state = PipelineState.fresh()
        result = MergeResult(
            chunk_files=[Path("/tmp/c0.ttl")],
            total_zips=10,
            processed_zips=[f"f{i}.zip" for i in range(9)],
            failed_zips=["bad.zip"],
            total_bytes=1_000_000,
        )
        state.update_merge(result)
        assert state.is_complete("merge")
        stage = state.get_stage("merge")
        assert stage.chunks_written == 1
        assert stage.failed_zips == ["bad.zip"]

    def test_update_export_all_ok(self):
        state = PipelineState.fresh()
        result = ExportResult(
            succeeded=["q1", "q2"],
            failed={},
            parquet_files=[Path("/tmp/q1.parquet"), Path("/tmp/q2.parquet")],
        )
        state.update_export(result)
        assert state.is_complete("export")

    def test_update_export_partial(self):
        state = PipelineState.fresh()
        result = ExportResult(
            succeeded=["q1"],
            failed={"q2": "HTTP 500"},
            parquet_files=[Path("/tmp/q1.parquet")],
        )
        state.update_export(result)
        # Has succeeded queries, so still marked complete
        assert state.is_complete("export")
        stage = state.get_stage("export")
        assert stage.failed_queries == {"q2": "HTTP 500"}

    def test_update_export_all_failed(self):
        state = PipelineState.fresh()
        result = ExportResult(
            succeeded=[],
            failed={"q1": "timeout"},
            parquet_files=[],
        )
        state.update_export(result)
        stage = state.get_stage("export")
        assert stage.status == "failed"

    def test_save_and_load(self, tmp_path: Path):
        state = PipelineState.fresh()
        state.mark_complete("merge")
        state.mark_complete("index")

        path = tmp_path / "state.json"
        state.save(path)

        loaded = PipelineState.load(path)
        assert loaded.is_complete("merge")
        assert loaded.is_complete("index")
        assert not loaded.is_complete("export")

    def test_save_is_valid_json(self, tmp_path: Path):
        state = PipelineState.fresh()
        state.mark_complete("merge")
        path = tmp_path / "state.json"
        state.save(path)

        data = json.loads(path.read_text())
        assert data["version"] == 1
        assert "merge" in data["stages"]

    def test_load_missing_file(self, tmp_path: Path):
        state = PipelineState.load(tmp_path / "nonexistent.json")
        assert state.started_at == ""
        assert state.stages == {}

    def test_load_corrupt_json(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("not json{{{")
        state = PipelineState.load(path)
        assert state.stages == {}

    def test_roundtrip_preserves_data(self, tmp_path: Path):
        state = PipelineState.fresh()
        state.update_merge(MergeResult(
            chunk_files=[],
            total_zips=5,
            processed_zips=["a.zip", "b.zip"],
            failed_zips=["c.zip"],
            total_bytes=100,
        ))
        state.update_export(ExportResult(
            succeeded=["q1"],
            failed={"q2": "error"},
            parquet_files=[],
        ))

        path = tmp_path / "state.json"
        state.save(path)
        loaded = PipelineState.load(path)

        merge = loaded.get_stage("merge")
        assert merge.processed_zips == ["a.zip", "b.zip"]
        assert merge.failed_zips == ["c.zip"]

        export = loaded.get_stage("export")
        assert export.completed_queries == ["q1"]
        assert export.failed_queries == {"q2": "error"}


class TestSetupLogging:
    def test_creates_log_file(self, tmp_path: Path):
        logger = setup_logging(tmp_path)
        logger.info("test message")

        # Flush handlers
        for h in logger.handlers:
            h.flush()

        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text()
        assert "test message" in content

    def test_idempotent(self, tmp_path: Path):
        logger1 = setup_logging(tmp_path)
        handler_count = len(logger1.handlers)
        logger2 = setup_logging(tmp_path)
        assert len(logger2.handlers) == handler_count
        assert logger1 is logger2
