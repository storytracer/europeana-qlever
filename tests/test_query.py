"""Unit tests for the dynamic SPARQL query generator."""

import pytest

from europeana_qlever.query import CompositeQuery, QueryBuilder, QueryFilters


class TestQueryBuilder:
    def setup_method(self):
        self.qb = QueryBuilder()

    # --- Structure tests ---

    def test_core_metadata_has_expected_columns(self):
        sparql = self.qb.core_metadata()
        for col in [
            "?item", "?title", "?creator", "?date", "?type",
            "?subject", "?language", "?rights", "?country", "?dataProvider",
        ]:
            assert col in sparql

    def test_all_queries_have_select_and_where(self):
        for name, query in self.qb.all_queries().items():
            if isinstance(query, CompositeQuery):
                for part_name, sparql in query.parts.items():
                    assert "SELECT" in sparql, f"{part_name} missing SELECT"
                    assert "WHERE" in sparql, f"{part_name} missing WHERE"
            else:
                assert "SELECT" in query, f"{name} missing SELECT"
                assert "WHERE" in query, f"{name} missing WHERE"

    def test_all_queries_have_prefixes(self):
        for name, query in self.qb.all_queries().items():
            if isinstance(query, CompositeQuery):
                for part_name, sparql in query.parts.items():
                    assert "PREFIX" in sparql, f"{part_name} missing PREFIX"
            else:
                assert "PREFIX" in query, f"{name} missing PREFIX"

    # --- Registry tests ---

    def test_all_base_queries_count(self):
        assert len(self.qb.all_base_queries()) == 7

    def test_all_ai_queries_count(self):
        assert len(self.qb.all_ai_queries()) == 5

    def test_all_analytics_queries_count(self):
        assert len(self.qb.all_analytics_queries()) == 24

    def test_all_queries_count(self):
        assert len(self.qb.all_queries()) == 36

    def test_no_duplicate_names(self):
        queries = self.qb.all_queries()
        assert len(queries) == len(set(queries.keys()))

    # --- Filter tests ---

    def test_country_filter(self):
        f = QueryFilters(countries=["Netherlands", "France"])
        sparql = self.qb.core_metadata(f)
        assert "Netherlands" in sparql
        assert "France" in sparql

    def test_type_filter(self):
        f = QueryFilters(types=["IMAGE"])
        sparql = self.qb.core_metadata(f)
        assert '"IMAGE"' in sparql

    def test_open_rights_filter(self):
        f = QueryFilters(rights_category="open")
        sparql = self.qb.core_metadata(f)
        assert "publicdomain" in sparql

    def test_limit(self):
        f = QueryFilters(limit=100)
        sparql = self.qb.core_metadata(f)
        assert "LIMIT 100" in sparql

    def test_offset(self):
        f = QueryFilters(limit=100, offset=500)
        sparql = self.qb.core_metadata(f)
        assert "OFFSET 500" in sparql

    # --- Specific query tests ---

    def test_items_enriched_returns_composite(self):
        result = self.qb.items_enriched()
        assert isinstance(result, CompositeQuery)
        assert "items_enriched_core" in result.parts
        assert "items_enriched_creators" in result.parts
        assert "items_enriched_subjects" in result.parts
        assert "items_enriched_dates" in result.parts
        assert "items_enriched_years" in result.parts
        assert "items_enriched_languages" in result.parts

    def test_items_enriched_join_uses_separator(self):
        result = self.qb.items_enriched()
        assert " ||| " in result.join_sql

    def test_entity_links_agent(self):
        sparql = self.qb.entity_links(entity_type="agent")
        assert "edm:Agent" in sparql

    def test_entity_links_place(self):
        sparql = self.qb.entity_links(entity_type="place")
        assert "edm:Place" in sparql

    def test_rights_category_bind_in_analytics(self):
        sparql = self.qb.open_reusable_inventory()
        assert "rights_category" in sparql
        assert "open" in sparql

    def test_temporal_distribution_uses_europeana_proxy(self):
        sparql = self.qb.temporal_distribution()
        assert "europeanaProxy" in sparql
        assert "edm:year" in sparql

    def test_describe_returns_string(self):
        for name in self.qb.all_queries():
            desc = self.qb.describe(name)
            assert isinstance(desc, str)
            assert len(desc) > 10

    # --- Language resolution tests ---

    def test_default_produces_en_native_any(self):
        """Default config: title_en, title_native, title (resolved), no extra lang columns."""
        qb = QueryBuilder()
        core = qb.items_enriched().parts["items_enriched_core"]
        assert "title_en" in core
        assert "title_native" in core
        assert "title_native_lang" in core
        # No French/German/etc. unless user specifies
        assert "title_fr" not in core
        assert "title_de" not in core

    def test_parallel_columns_in_items_enriched(self):
        """items_enriched core exposes en, native, and resolved columns."""
        qb = QueryBuilder()
        core = qb.items_enriched().parts["items_enriched_core"]
        assert "SAMPLE(" in core
        for col in ["title_en", "title_native", "title_native_lang"]:
            assert col in core

    def test_base_query_single_resolved_column(self):
        """core_metadata produces a single ?title column, not parallel columns."""
        qb = QueryBuilder()
        sparql = qb.core_metadata()
        assert "?title" in sparql
        # Should NOT expose title_en, title_native as separate SELECT columns
        select_clause = sparql.split("WHERE")[0]
        assert "title_en" not in select_clause
        assert "title_native" not in select_clause

    def test_extra_languages_add_columns(self):
        """Extra languages produce additional columns."""
        qb = QueryBuilder(languages=["fr", "de"])
        core = qb.items_enriched().parts["items_enriched_core"]
        assert "title_fr" in core
        assert "title_de" in core

    def test_filter_languages_override_constructor(self):
        """QueryFilters.languages overrides constructor."""
        qb = QueryBuilder(languages=["fr"])
        f = QueryFilters(languages=["nl", "pl"])
        core = qb.items_enriched(f).parts["items_enriched_core"]
        assert "title_nl" in core
        assert "title_pl" in core
        assert "title_fr" not in core

    def test_entity_resolution_no_vernacular(self):
        """Entity labels resolve via en → extras → any, no vernacular."""
        qb = QueryBuilder()
        sparql = qb.entity_links(entity_type="agent")
        assert "vernacular" not in sparql.lower()

    def test_entity_resolution_has_wildcard(self):
        """Entity label chain ends with a wildcard fallback."""
        qb = QueryBuilder()
        sparql = qb.entity_links(entity_type="agent")
        assert "_any" in sparql

    def test_vernacular_bound_from_dc_language(self):
        """The vernacular language is bound from dc:language and reused."""
        qb = QueryBuilder()
        core = qb.items_enriched().parts["items_enriched_core"]
        assert "dc:language ?_language" in core
        assert "LANG(?_title_native) = ?_language" in core

    def test_coalesce_in_resolved_title(self):
        """The resolved title uses COALESCE."""
        core = self.qb.items_enriched().parts["items_enriched_core"]
        assert "COALESCE" in core

    # --- Web resources query tests ---

    def test_web_resources_columns(self):
        sparql = self.qb.web_resources()
        for col in ["?item", "?url", "?mime", "?width", "?height", "?bytes"]:
            assert col in sparql

    # --- Rights providers query tests ---

    def test_rights_providers_columns(self):
        sparql = self.qb.rights_providers()
        for col in ["?item", "?rights", "?dataProvider", "?provider", "?country", "?completeness"]:
            assert col in sparql

    # --- Entity query tests ---

    def test_agents_columns(self):
        sparql = self.qb.agents()
        for col in ["?agent", "?name", "?lang", "?birth", "?death", "?profession", "?wikidata"]:
            assert col in sparql

    def test_places_columns(self):
        sparql = self.qb.places()
        for col in ["?place", "?name", "?lang", "?lat", "?lon", "?wikidata"]:
            assert col in sparql

    def test_concepts_columns(self):
        sparql = self.qb.concepts()
        for col in ["?concept", "?label", "?lang", "?scheme", "?broader", "?exactMatch"]:
            assert col in sparql

    def test_timespans_columns(self):
        sparql = self.qb.timespans()
        for col in ["?timespan", "?label", "?lang", "?begin", "?end"]:
            assert col in sparql
        assert "edm:TimeSpan" in sparql

    # --- Entity links for all entity types ---

    def test_entity_links_concept(self):
        sparql = self.qb.entity_links(entity_type="concept")
        assert "skos:Concept" in sparql

    def test_entity_links_timespan(self):
        sparql = self.qb.entity_links(entity_type="timespan")
        assert "edm:TimeSpan" in sparql

    # --- Multiple filters combined ---

    def test_combined_filters(self):
        f = QueryFilters(
            countries=["Germany"],
            types=["TEXT"],
            rights_category="open",
            limit=500,
        )
        sparql = self.qb.core_metadata(f)
        assert "Germany" in sparql
        assert '"TEXT"' in sparql
        assert "publicdomain" in sparql
        assert "LIMIT 500" in sparql

    # --- Provider filter ---

    def test_provider_filter(self):
        f = QueryFilters(providers=["Rijksmuseum"])
        sparql = self.qb.core_metadata(f)
        assert "Rijksmuseum" in sparql

    # --- Year filters ---

    def test_year_filters_in_temporal_coverage(self):
        f = QueryFilters(year_from=1800, year_to=1900)
        sparql = self.qb.temporal_coverage(f)
        assert "1800" in sparql
        assert "1900" in sparql

    # --- Separator customisation ---

    def test_custom_separator(self):
        qb = QueryBuilder(separator=" ; ")
        result = qb.items_enriched()
        assert " ; " in result.join_sql
        assert " ||| " not in result.join_sql

    # --- Description columns in AI queries ---

    def test_items_enriched_has_description_columns(self):
        core = self.qb.items_enriched().parts["items_enriched_core"]
        assert "description_en" in core
        assert "description_native" in core
        assert "description_native_lang" in core

    def test_text_corpus_has_parallel_columns(self):
        sparql = self.qb.text_corpus()
        assert "title_en" in sparql
        assert "title_native" in sparql
        assert "description_en" in sparql

    def test_image_metadata_has_parallel_title_columns(self):
        sparql = self.qb.image_metadata()
        assert "title_en" in sparql
        assert "title_native" in sparql

    # --- Geolocated places uses entity resolution ---

    def test_geolocated_places_uses_entity_resolution(self):
        sparql = self.qb.geolocated_places()
        assert "COALESCE" in sparql
        assert "_any" in sparql
