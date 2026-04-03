"""Unit tests for the rights statement registry."""

import pytest

from europeana_qlever.rights import (
    REUSE_LEVELS,
    RIGHTS_REGISTRY,
    RightsStatement,
    generic_rights,
    identifier_for_uri,
    reuse_level_for_uri,
    uris_for_reuse_level,
)


class TestURIGeneration:
    """Verify that all expected CC URIs are generated from the Europeana spec."""

    def test_total_count(self):
        assert len(RIGHTS_REGISTRY) == 580

    def test_cc_license_count_by_version(self):
        def count_version(version: str) -> int:
            prefix = f"http://creativecommons.org/licenses/"
            return sum(
                1 for uri in RIGHTS_REGISTRY
                if uri.startswith(prefix) and f"/{version}/" in uri
            )

        assert count_version("1.0") == 24
        assert count_version("2.0") == 108
        assert count_version("2.1") == 18
        assert count_version("2.5") == 174
        assert count_version("3.0") == 240
        assert count_version("4.0") == 6

    def test_public_domain_count(self):
        pd_uris = [
            u for u in RIGHTS_REGISTRY
            if u.startswith("http://creativecommons.org/publicdomain/")
        ]
        assert len(pd_uris) == 2

    def test_rightsstatements_count(self):
        rs_uris = [
            u for u in RIGHTS_REGISTRY
            if u.startswith("http://rightsstatements.org/vocab/")
        ]
        assert len(rs_uris) == 8

    def test_v1_uses_by_nd_nc(self):
        """v1.0 uses 'by-nd-nc' in the URI, not 'by-nc-nd'."""
        assert "http://creativecommons.org/licenses/by-nd-nc/1.0/" in RIGHTS_REGISTRY
        assert "http://creativecommons.org/licenses/by-nc-nd/1.0/" not in RIGHTS_REGISTRY

    def test_v4_has_no_ported_versions(self):
        v4_uris = [
            u for u in RIGHTS_REGISTRY
            if "creativecommons.org/licenses/" in u and "/4.0/" in u
        ]
        # 6 generic only (by, by-sa, by-nd, by-nc, by-nc-sa, by-nc-nd)
        assert len(v4_uris) == 6
        for uri in v4_uris:
            assert uri.endswith("/4.0/")

    def test_all_cc_uris_match_pattern(self):
        for uri in RIGHTS_REGISTRY:
            assert uri.startswith("http://creativecommons.org/") or \
                   uri.startswith("http://rightsstatements.org/vocab/")


class TestReuseLevels:
    def test_valid_levels(self):
        assert REUSE_LEVELS == ["open", "restricted", "prohibited"]

    def test_all_entries_have_valid_reuse_level(self):
        for uri, rs in RIGHTS_REGISTRY.items():
            assert rs.reuse_level in REUSE_LEVELS, f"{uri} has invalid reuse_level {rs.reuse_level}"

    def test_uris_for_reuse_level_non_empty(self):
        for level in REUSE_LEVELS:
            assert len(uris_for_reuse_level(level)) > 0

    def test_uris_for_reuse_level_invalid(self):
        with pytest.raises(ValueError, match="Unknown reuse level"):
            uris_for_reuse_level("unknown")

    def test_open_includes_public_domain(self):
        open_uris = uris_for_reuse_level("open")
        assert "http://creativecommons.org/publicdomain/zero/1.0/" in open_uris
        assert "http://creativecommons.org/publicdomain/mark/1.0/" in open_uris

    def test_open_includes_by_and_by_sa(self):
        open_uris = uris_for_reuse_level("open")
        assert "http://creativecommons.org/licenses/by/4.0/" in open_uris
        assert "http://creativecommons.org/licenses/by-sa/3.0/au/" in open_uris

    def test_restricted_includes_nc_nd(self):
        restricted = uris_for_reuse_level("restricted")
        assert "http://creativecommons.org/licenses/by-nc/4.0/" in restricted
        assert "http://creativecommons.org/licenses/by-nd/4.0/" in restricted
        assert "http://creativecommons.org/licenses/by-nc-sa/4.0/" in restricted
        assert "http://creativecommons.org/licenses/by-nc-nd/4.0/" in restricted

    def test_restricted_includes_rs_entries(self):
        restricted = uris_for_reuse_level("restricted")
        assert "http://rightsstatements.org/vocab/NoC-NC/1.0/" in restricted
        assert "http://rightsstatements.org/vocab/NoC-OKLR/1.0/" in restricted
        assert "http://rightsstatements.org/vocab/InC-EDU/1.0/" in restricted

    def test_prohibited_includes_rs_entries(self):
        prohibited = uris_for_reuse_level("prohibited")
        assert "http://rightsstatements.org/vocab/InC/1.0/" in prohibited
        assert "http://rightsstatements.org/vocab/InC-OW-EU/1.0/" in prohibited
        assert "http://rightsstatements.org/vocab/CNE/1.0/" in prohibited
        assert "http://rightsstatements.org/vocab/NKC/1.0/" in prohibited
        assert "http://rightsstatements.org/vocab/UND/1.0/" in prohibited

    def test_v1_by_nd_nc_is_restricted(self):
        assert reuse_level_for_uri("http://creativecommons.org/licenses/by-nd-nc/1.0/") == "restricted"


class TestIdentifiers:
    def test_cc_generic_identifiers(self):
        assert identifier_for_uri("http://creativecommons.org/licenses/by/4.0/") == "CC-BY-4.0"
        assert identifier_for_uri("http://creativecommons.org/licenses/by-sa/3.0/") == "CC-BY-SA-3.0"
        assert identifier_for_uri("http://creativecommons.org/licenses/by-nc-nd/2.0/") == "CC-BY-NC-ND-2.0"

    def test_cc_ported_identifiers(self):
        assert identifier_for_uri("http://creativecommons.org/licenses/by-sa/3.0/au/") == "CC-BY-SA-3.0-AU"
        assert identifier_for_uri("http://creativecommons.org/licenses/by/2.5/scotland/") == "CC-BY-2.5-SCOTLAND"

    def test_v1_by_nd_nc_uses_canonical_spdx_order(self):
        """v1.0 'by-nd-nc' maps to the canonical SPDX order 'BY-NC-ND'."""
        assert identifier_for_uri("http://creativecommons.org/licenses/by-nd-nc/1.0/") == "CC-BY-NC-ND-1.0"
        assert identifier_for_uri("http://creativecommons.org/licenses/by-nd-nc/1.0/nl/") == "CC-BY-NC-ND-1.0-NL"

    def test_public_domain_identifiers(self):
        assert identifier_for_uri("http://creativecommons.org/publicdomain/zero/1.0/") == "CC0-1.0"
        assert identifier_for_uri("http://creativecommons.org/publicdomain/mark/1.0/") == "CC-PDDC"

    def test_rightsstatements_identifiers(self):
        assert identifier_for_uri("http://rightsstatements.org/vocab/InC/1.0/") == "InC-1.0"
        assert identifier_for_uri("http://rightsstatements.org/vocab/NoC-NC/1.0/") == "NoC-NC-1.0"
        assert identifier_for_uri("http://rightsstatements.org/vocab/InC-OW-EU/1.0/") == "InC-OW-EU-1.0"
        assert identifier_for_uri("http://rightsstatements.org/vocab/NKC/1.0/") == "NKC-1.0"
        assert identifier_for_uri("http://rightsstatements.org/vocab/UND/1.0/") == "UND-1.0"

    def test_unknown_uri_returns_other(self):
        assert identifier_for_uri("http://example.com/unknown") == "Other"

    def test_unknown_uri_reuse_level_is_prohibited(self):
        assert reuse_level_for_uri("http://example.com/unknown") == "prohibited"


class TestGenericRights:
    def test_returns_only_unported(self):
        generic = generic_rights()
        for rs in generic:
            uri = rs.uri
            if uri.startswith("http://creativecommons.org/licenses/"):
                # Generic CC licenses end with /{version}/ (no port suffix)
                assert uri.count("/") == 6, f"Ported URI in generic: {uri}"

    def test_includes_all_rightsstatements(self):
        generic = generic_rights()
        rs_uris = [rs.uri for rs in generic if rs.uri.startswith("http://rightsstatements.org/")]
        assert len(rs_uris) == 8

    def test_includes_public_domain(self):
        generic = generic_rights()
        pd_uris = [rs.uri for rs in generic if "publicdomain" in rs.uri]
        assert len(pd_uris) == 2

    def test_generic_count(self):
        # 6 versions × 6 properties (only generic) + 2 public domain + 8 RS
        # But v2.1 has no generic version, so 5 × 6 = 30 + 2 + 8 = 40
        generic = generic_rights()
        assert len(generic) == 40
