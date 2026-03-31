"""Unit tests for the dynamic SPARQL query generator."""

import pytest

from europeana_qlever.query import QueryBuilder, QueryFilters, QuerySpec


class TestQuerySpec:
    def test_simple_spec(self):
        spec = QuerySpec(name="test", sparql="SELECT 1")
        assert not spec.is_composite
        assert spec.sparql == "SELECT 1"
        assert spec.compose_steps is None
        assert spec.depends_on == []

    def test_composite_spec(self):
        from europeana_qlever.compose import ComposeStep

        spec = QuerySpec(
            name="composed",
            compose_steps=[ComposeStep("step1", "CREATE TEMP TABLE step1 AS SELECT 1")],
            depends_on=["dep1", "dep2"],
        )
        assert spec.is_composite
        assert spec.sparql is None
        assert len(spec.compose_steps) == 1
        assert spec.depends_on == ["dep1", "dep2"]


class TestQueryBuilder:
    def setup_method(self):
        self.qb = QueryBuilder()

    # --- Structure tests ---

    def test_all_sparql_queries_have_select_and_where(self):
        for name, spec in self.qb.all_queries().items():
            if spec.sparql:
                assert "SELECT" in spec.sparql, f"{name} missing SELECT"
                assert "WHERE" in spec.sparql, f"{name} missing WHERE"

    def test_all_sparql_queries_have_prefixes(self):
        for name, spec in self.qb.all_queries().items():
            if spec.sparql:
                assert "PREFIX" in spec.sparql, f"{name} missing PREFIX"

    # --- Registry tests ---

    def test_all_base_queries_count(self):
        assert len(self.qb.all_base_queries()) == 6

    def test_all_component_queries_count(self):
        assert len(self.qb.all_component_queries()) == 8

    def test_all_enriched_queries_count(self):
        assert len(self.qb.all_enriched_queries()) == 1

    def test_all_example_queries_count(self):
        assert len(self.qb.all_example_queries()) == 11

    def test_all_queries_count(self):
        assert len(self.qb.all_queries()) == 18

    def test_no_duplicate_names(self):
        queries = self.qb.all_queries()
        assert len(queries) == len(set(queries.keys()))

    def test_registry_returns_query_specs(self):
        for name, spec in self.qb.all_queries().items():
            assert isinstance(spec, QuerySpec), f"{name} is not a QuerySpec"
            assert spec.name == name

    # --- Filter tests ---

    def test_country_filter(self):
        f = QueryFilters(countries=["Netherlands", "France"])
        sparql = self.qb.rights_providers(f)
        assert "Netherlands" in sparql
        assert "France" in sparql

    def test_type_filter(self):
        f = QueryFilters(types=["IMAGE"])
        sparql = self.qb.items_core(f)
        assert '"IMAGE"' in sparql

    def test_open_rights_filter(self):
        f = QueryFilters(rights_category="open")
        sparql = self.qb.rights_providers(f)
        assert "publicdomain" in sparql

    def test_limit(self):
        f = QueryFilters(limit=100)
        sparql = self.qb.rights_providers(f)
        assert "LIMIT 100" in sparql

    def test_offset(self):
        f = QueryFilters(limit=100, offset=500)
        sparql = self.qb.rights_providers(f)
        assert "OFFSET 500" in sparql

    # --- Specific query tests ---

    def test_items_enriched_is_composite(self):
        specs = self.qb.all_enriched_queries()
        spec = specs["items_enriched"]
        assert spec.is_composite
        assert spec.compose_steps is not None
        assert spec.sparql is None
        assert len(spec.depends_on) > 0

    def test_items_enriched_depends_on_component_tables(self):
        specs = self.qb.all_enriched_queries()
        spec = specs["items_enriched"]
        for dep in [
            "items_core", "items_titles", "items_descriptions",
            "items_subjects", "items_dates", "items_languages",
            "items_years", "items_creators", "agents",
        ]:
            assert dep in spec.depends_on, f"Missing dependency: {dep}"

    def test_items_enriched_steps_have_placeholders(self):
        specs = self.qb.all_enriched_queries()
        all_sql = "\n".join(s.sql for s in specs["items_enriched"].compose_steps)
        assert "{exports_dir}" in all_sql

    def test_items_enriched_steps_use_list(self):
        specs = self.qb.all_enriched_queries()
        all_sql = "\n".join(s.sql for s in specs["items_enriched"].compose_steps)
        assert "LIST" in all_sql
        assert "STRING_AGG" not in all_sql

    def test_items_by_year_uses_europeana_proxy(self):
        sparql = self.qb.items_by_year()
        assert "europeanaProxy" in sparql
        assert "edm:year" in sparql

    def test_describe_returns_string(self):
        for name in self.qb.all_queries():
            desc = self.qb.describe(name)
            assert isinstance(desc, str)
            assert len(desc) > 10

    # --- Language resolution tests ---

    def test_items_enriched_steps_have_language_columns(self):
        """Composite items_enriched has en/native/resolved columns."""
        specs = self.qb.all_enriched_queries()
        all_sql = "\n".join(s.sql for s in specs["items_enriched"].compose_steps)
        assert "title_en" in all_sql
        assert "title_native" in all_sql
        assert "title_native_lang" in all_sql
        assert "description_en" in all_sql
        assert "description_native" in all_sql

    def test_extra_languages_in_steps(self):
        """Extra languages produce additional columns in composition steps."""
        qb = QueryBuilder(languages=["fr", "de"])
        specs = qb.all_enriched_queries()
        all_sql = "\n".join(s.sql for s in specs["items_enriched"].compose_steps)
        assert "title_fr" in all_sql
        assert "title_de" in all_sql
        assert "description_fr" in all_sql
        assert "description_de" in all_sql

    # --- Component query tests ---

    def test_items_core_columns(self):
        sparql = self.qb.items_core()
        for col in ["?item", "?type", "?rights", "?country", "?dataProvider",
                     "?isShownAt", "?isShownBy", "?preview", "?landingPage",
                     "?datasetName", "?completeness"]:
            assert col in sparql

    def test_items_core_no_group_by(self):
        sparql = self.qb.items_core()
        assert "GROUP BY" not in sparql
        assert "GROUP_CONCAT" not in sparql

    def test_items_titles_columns(self):
        sparql = self.qb.items_titles()
        for col in ["?item", "?title", "?lang"]:
            assert col in sparql
        assert "GROUP BY" not in sparql

    def test_items_descriptions_columns(self):
        sparql = self.qb.items_descriptions()
        for col in ["?item", "?description", "?lang"]:
            assert col in sparql

    def test_items_subjects_columns(self):
        sparql = self.qb.items_subjects()
        for col in ["?item", "?subject"]:
            assert col in sparql

    def test_items_dates_columns(self):
        sparql = self.qb.items_dates()
        for col in ["?item", "?date"]:
            assert col in sparql

    def test_items_languages_columns(self):
        sparql = self.qb.items_languages()
        for col in ["?item", "?language"]:
            assert col in sparql

    def test_items_years_uses_europeana_proxy(self):
        sparql = self.qb.items_years()
        assert "europeanaProxy" in sparql
        assert "edm:year" in sparql
        assert "?item" in sparql
        assert "?year" in sparql

    def test_items_creators_columns(self):
        sparql = self.qb.items_creators()
        for col in ["?item", "?creator_value", "?is_iri"]:
            assert col in sparql

    def test_component_queries_use_provider_proxy(self):
        """Component queries that access proxy properties use the provider proxy filter."""
        for method in [self.qb.items_titles, self.qb.items_descriptions,
                       self.qb.items_subjects, self.qb.items_dates,
                       self.qb.items_languages, self.qb.items_creators]:
            sparql = method()
            assert "ore:proxyFor" in sparql

    def test_component_queries_all_have_select_where(self):
        for name, spec in self.qb.all_component_queries().items():
            assert spec.sparql is not None
            assert "SELECT" in spec.sparql, f"{name} missing SELECT"
            assert "WHERE" in spec.sparql, f"{name} missing WHERE"

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

    # --- Multiple filters combined ---

    def test_combined_filters(self):
        f = QueryFilters(
            countries=["Germany"],
            rights_category="open",
            limit=500,
        )
        sparql = self.qb.rights_providers(f)
        assert "Germany" in sparql
        assert "publicdomain" in sparql
        assert "LIMIT 500" in sparql

    # --- Provider filter ---

    def test_provider_filter(self):
        f = QueryFilters(providers=["Rijksmuseum"])
        sparql = self.qb.rights_providers(f)
        assert "Rijksmuseum" in sparql

    # --- Year filters ---


    # --- Geolocated places ---

    def test_geolocated_places_has_coordinates(self):
        sparql = self.qb.geolocated_places()
        assert "wgs84_pos:lat" in sparql
        assert "wgs84_pos:long" in sparql
