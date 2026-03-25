"""Tests for the validate module: TTL validation, checksums, manifest I/O."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from europeana_qlever.validate import (
    EntryIssue,
    ZipReport,
    _validate_entry,
    _validate_zip,
    _verify_one_checksum,
    load_manifest,
    save_manifest,
    verify_checksums,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_TTL = b"""\
@prefix edm: <http://www.europeana.eu/schemas/edm/> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix ore: <http://www.openarchives.org/ore/terms/> .

<http://data.europeana.eu/item/123/abc>
    a edm:ProvidedCHO .

<http://data.europeana.eu/proxy/provider/123/abc>
    a ore:Proxy ;
    dc:title "Test Item"@en ;
    dc:language "en" .
"""

INVALID_TTL_BAD_AT = b"""\
@prefix edm: <http://www.europeana.eu/schemas/edm/> .

<http://data.europeana.eu/item/123/abc>
    a edm:ProvidedCHO .

@ spa .
<http://data.europeana.eu/organization/456>
    a <http://xmlns.com/foaf/0.1/Organization> .
"""

INVALID_TTL_UNCLOSED_QUOTE = b"""\
@prefix dc: <http://purl.org/dc/elements/1.1/> .

<http://data.europeana.eu/item/123/abc>
    dc:title "unclosed string ;
    dc:language "en" .
"""

INVALID_TTL_BAD_UTF8 = b"\xff\xfe@prefix dc: <http://purl.org/dc/elements/1.1/> .\n"


def _make_zip(tmp_path: Path, name: str, entries: dict[str, bytes]) -> Path:
    """Create a ZIP file at *tmp_path/name* with the given entries."""
    zp = tmp_path / name
    with zipfile.ZipFile(zp, "w") as zf:
        for entry_name, data in entries.items():
            zf.writestr(entry_name, data)
    return zp


def _make_md5sum(zip_path: Path) -> Path:
    """Create a correct .md5sum file for a ZIP."""
    h = hashlib.md5(zip_path.read_bytes()).hexdigest()
    md5_path = zip_path.with_suffix(".zip.md5sum")
    md5_path.write_text(f"{h}  {zip_path.name}\n")
    return md5_path


# ---------------------------------------------------------------------------
# Entry validation
# ---------------------------------------------------------------------------


class TestEntryValidation:
    def test_valid_entry_returns_none(self):
        assert _validate_entry("good.ttl", VALID_TTL) is None

    def test_malformed_at_line_invalid(self):
        result = _validate_entry("bad_at.ttl", INVALID_TTL_BAD_AT)
        assert result is not None
        assert isinstance(result, EntryIssue)
        assert result.entry_name == "bad_at.ttl"
        assert result.error  # non-empty error message

    def test_encoding_error_invalid(self):
        result = _validate_entry("bad_utf8.ttl", INVALID_TTL_BAD_UTF8)
        assert result is not None
        assert "UTF-8" in result.error or "codec" in result.error.lower()

    def test_unclosed_quote_invalid(self):
        result = _validate_entry("unclosed.ttl", INVALID_TTL_UNCLOSED_QUOTE)
        assert result is not None

    def test_valid_language_tags(self):
        """Language tags like @en, @spa in literals should not cause issues."""
        ttl = b"""\
@prefix dc: <http://purl.org/dc/elements/1.1/> .

<http://example.org/item>
    dc:title "Titulo"@spa, "Title"@en ;
    dc:description "A test"@en .
"""
        assert _validate_entry("lang.ttl", ttl) is None


# ---------------------------------------------------------------------------
# ZIP validation
# ---------------------------------------------------------------------------


class TestZipValidation:
    def test_clean_zip(self, tmp_path):
        zp = _make_zip(tmp_path, "clean.zip", {
            "a.ttl": VALID_TTL,
            "b.ttl": VALID_TTL,
        })
        report = _validate_zip(zp)
        assert report.zip_name == "clean.zip"
        assert report.total_entries == 2
        assert report.valid_count == 2
        assert report.invalid_count == 0
        assert report.invalid_entries == []

    def test_mixed_zip(self, tmp_path):
        zp = _make_zip(tmp_path, "mixed.zip", {
            "good.ttl": VALID_TTL,
            "bad.ttl": INVALID_TTL_BAD_AT,
        })
        report = _validate_zip(zp)
        assert report.total_entries == 2
        assert report.valid_count == 1
        assert report.invalid_count == 1
        assert len(report.invalid_entries) == 1
        assert report.invalid_entries[0].entry_name == "bad.ttl"

    def test_non_ttl_files_ignored(self, tmp_path):
        zp = _make_zip(tmp_path, "other.zip", {
            "readme.txt": b"not turtle",
            "data.ttl": VALID_TTL,
        })
        report = _validate_zip(zp)
        assert report.total_entries == 1  # only .ttl counted
        assert report.valid_count == 1

    def test_corrupt_zip(self, tmp_path):
        zp = tmp_path / "corrupt.zip"
        zp.write_bytes(b"not a zip file")
        report = _validate_zip(zp)
        assert report.invalid_count == 1
        assert "Cannot open ZIP" in report.invalid_entries[0].error


# ---------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------


class TestChecksum:
    def test_matching_checksum(self, tmp_path):
        zp = _make_zip(tmp_path, "test.zip", {"a.ttl": VALID_TTL})
        _make_md5sum(zp)
        name, ok, error = _verify_one_checksum(zp)
        assert name == "test.zip"
        assert ok is True
        assert error is None

    def test_mismatched_checksum(self, tmp_path):
        zp = _make_zip(tmp_path, "test.zip", {"a.ttl": VALID_TTL})
        md5_path = zp.with_suffix(".zip.md5sum")
        md5_path.write_text("0000000000000000000000000000dead  test.zip\n")
        name, ok, error = _verify_one_checksum(zp)
        assert ok is False
        assert "expected" in error

    def test_missing_checksum_file(self, tmp_path):
        zp = _make_zip(tmp_path, "test.zip", {"a.ttl": VALID_TTL})
        name, ok, error = _verify_one_checksum(zp)
        assert ok is None
        assert error is None

    def test_verify_checksums_parallel(self, tmp_path):
        zips = []
        for i in range(5):
            zp = _make_zip(tmp_path, f"test_{i}.zip", {"a.ttl": VALID_TTL})
            _make_md5sum(zp)
            zips.append(zp)
        ok, failed, missing = verify_checksums(zips, workers=2)
        assert len(ok) == 5
        assert len(failed) == 0
        assert len(missing) == 0


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------


class TestManifest:
    def test_roundtrip(self, tmp_path):
        reports = [
            ZipReport(
                zip_name="bad.zip",
                checksum_ok=True,
                invalid_entries=[
                    EntryIssue(entry_name="err.ttl", error="parse error"),
                ],
                total_entries=10,
                valid_count=9,
                invalid_count=1,
            ),
            ZipReport(
                zip_name="good.zip",
                checksum_ok=True,
                total_entries=5,
                valid_count=5,
                invalid_count=0,
            ),
        ]
        path = tmp_path / "manifest.json"
        save_manifest(reports, path)
        loaded = load_manifest(path)

        # Only non-clean ZIPs stored
        assert "bad.zip" in loaded
        assert "good.zip" not in loaded

        bad = loaded["bad.zip"]
        assert bad.invalid_count == 1
        assert bad.invalid_entries[0].entry_name == "err.ttl"
        assert bad.invalid_entries[0].error == "parse error"

    def test_valid_zips_omitted(self, tmp_path):
        reports = [
            ZipReport(
                zip_name="allgood.zip",
                checksum_ok=True,
                total_entries=100,
                valid_count=100,
                invalid_count=0,
            ),
        ]
        path = tmp_path / "manifest.json"
        save_manifest(reports, path)

        raw = json.loads(path.read_text())
        assert len(raw["zips"]) == 0

    def test_missing_manifest_returns_empty(self, tmp_path):
        loaded = load_manifest(tmp_path / "nonexistent.json")
        assert loaded == {}
