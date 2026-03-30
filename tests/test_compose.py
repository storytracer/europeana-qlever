"""Unit tests for the DuckDB composition SQL generator."""

from europeana_qlever.compose import items_enriched_sql


class TestItemsEnrichedSql:
    def test_contains_placeholder(self):
        sql = items_enriched_sql()
        assert "{exports_dir}" in sql

    def test_default_separator(self):
        sql = items_enriched_sql()
        assert " ||| " in sql

    def test_custom_separator(self):
        sql = items_enriched_sql(separator=" ; ")
        assert " ; " in sql
        assert " ||| " not in sql

    def test_reads_all_base_tables(self):
        sql = items_enriched_sql()
        for table in [
            "items_core", "items_titles", "items_descriptions",
            "items_subjects", "items_dates", "items_languages",
            "items_years", "items_creators", "agents",
        ]:
            assert f"{table}.parquet" in sql

    def test_has_language_resolution(self):
        sql = items_enriched_sql()
        assert "title_en" in sql
        assert "title_native" in sql
        assert "title_native_lang" in sql
        assert "description_en" in sql
        assert "description_native" in sql

    def test_has_aggregations(self):
        sql = items_enriched_sql()
        assert "STRING_AGG" in sql
        assert "subjects" in sql
        assert "dates" in sql
        assert "years" in sql
        assert "languages" in sql
        assert "creators" in sql

    def test_extra_languages(self):
        sql = items_enriched_sql(extra_languages=["fr", "de"])
        assert "title_fr" in sql
        assert "title_de" in sql
        assert "description_fr" in sql
        assert "description_de" in sql

    def test_agent_label_resolution(self):
        sql = items_enriched_sql()
        assert "agent_labels" in sql
        assert "creator_uris" in sql

    def test_output_column_aliases(self):
        """Final SELECT uses clean column names (data_provider, not dataProvider)."""
        sql = items_enriched_sql()
        assert "data_provider" in sql
        assert "is_shown_at" in sql
        assert "landing_page" in sql
        assert "dataset_name" in sql
