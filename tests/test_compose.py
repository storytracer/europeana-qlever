"""Unit tests for the DuckDB composition SQL generator."""

from europeana_qlever.compose import items_enriched_steps


def _all_sql(extra_languages=None):
    """Concatenate all step SQL for easy assertion."""
    return "\n".join(s.sql for s in items_enriched_steps(extra_languages))


class TestItemsEnrichedSteps:
    def test_contains_placeholder(self):
        assert "{exports_dir}" in _all_sql()

    def test_reads_all_base_tables(self):
        sql = _all_sql()
        for table in [
            "items_core", "items_titles", "items_descriptions",
            "items_subjects", "items_dates", "items_languages",
            "items_years", "items_creators", "agents",
        ]:
            assert f"{table}.parquet" in sql

    def test_has_language_resolution(self):
        sql = _all_sql()
        assert "title_en" in sql
        assert "title_native" in sql
        assert "title_native_lang" in sql
        assert "description_en" in sql
        assert "description_native" in sql

    def test_uses_list_aggregation(self):
        sql = _all_sql()
        assert "LIST" in sql
        assert "STRING_AGG" not in sql
        assert "subjects" in sql
        assert "dates" in sql
        assert "years" in sql
        assert "languages" in sql
        assert "creators" in sql

    def test_creators_use_struct(self):
        sql = _all_sql()
        assert "name:" in sql
        assert "uri:" in sql

    def test_no_separate_creator_uris_column(self):
        sql = _all_sql()
        assert "cr.creator_uris" not in sql

    def test_extra_languages(self):
        sql = _all_sql(extra_languages=["fr", "de"])
        assert "title_fr" in sql
        assert "title_de" in sql
        assert "description_fr" in sql
        assert "description_de" in sql

    def test_agent_label_resolution(self):
        sql = _all_sql()
        assert "agent_labels" in sql

    def test_output_column_aliases(self):
        """Final SELECT uses clean column names."""
        sql = _all_sql()
        assert "data_provider" in sql
        assert "is_shown_at" in sql
        assert "landing_page" in sql
        assert "dataset_name" in sql

    def test_step_count(self):
        steps = items_enriched_steps()
        assert len(steps) == 11

    def test_final_step_is_marked(self):
        steps = items_enriched_steps()
        assert steps[-1].is_final is True
        assert all(not s.is_final for s in steps[:-1])
