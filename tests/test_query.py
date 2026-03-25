"""Unit tests for the dynamic SPARQL query generator."""

import pytest

from europeana_qlever.query import QueryBuilder, QueryFilters


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
        for name, sparql in self.qb.all_queries().items():
            assert "SELECT" in sparql, f"{name} missing SELECT"
            assert "WHERE" in sparql, f"{name} missing WHERE"

    def test_all_queries_have_prefixes(self):
        for name, sparql in self.qb.all_queries().items():
            assert "PREFIX" in sparql, f"{name} missing PREFIX"

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

    def test_items_enriched_uses_group_concat(self):
        sparql = self.qb.items_enriched()
        assert "GROUP_CONCAT" in sparql
        assert "GROUP BY" in sparql

    def test_items_enriched_uses_separator(self):
        sparql = self.qb.items_enriched()
        assert " ||| " in sparql

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

    # --- Language tests ---

    def test_custom_languages(self):
        qb = QueryBuilder(languages=["nl", "en"])
        sparql = qb.items_enriched()
        assert "COALESCE" in sparql

    def test_default_languages(self):
        sparql = self.qb.items_enriched()
        assert "COALESCE" in sparql

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
        sparql = qb.items_enriched()
        assert " ; " in sparql
        assert " ||| " not in sparql
