"""Unit tests for the DuckDB composition SQL generator."""

from europeana_qlever.compose import items_enriched_steps


def _all_sql():
    """Concatenate all step SQL for easy assertion."""
    return "\n".join(s.sql for s in items_enriched_steps())


class TestItemsEnrichedSteps:
    def test_contains_placeholder(self):
        assert "{exports_dir}" in _all_sql()

    def test_reads_all_base_tables(self):
        sql = _all_sql()
        for table in [
            "items_core", "items_titles", "items_descriptions",
            "items_subjects", "items_dates", "items_languages",
            "items_years", "items_creators", "agents", "concepts",
        ]:
            assert f"{table}.parquet" in sql

    def test_titles_are_struct_list(self):
        """Titles are LIST<STRUCT<value, lang>>, not flat columns."""
        sql = _all_sql()
        assert "t.titles" in sql
        assert "title_en" not in sql
        assert "title_native" not in sql

    def test_descriptions_are_struct_list(self):
        sql = _all_sql()
        assert "d.descriptions" in sql
        assert "description_en" not in sql
        assert "description_native" not in sql

    def test_uses_list_aggregation(self):
        sql = _all_sql()
        assert "LIST" in sql
        assert "STRING_AGG" not in sql

    def test_creators_use_struct(self):
        sql = _all_sql()
        assert "name:" in sql
        assert "uri:" in sql

    def test_subjects_use_struct(self):
        sql = _all_sql()
        assert "label:" in sql
        assert "concept_labels" in sql
        assert "subject_map" in sql

    def test_nullif_for_empty_strings(self):
        sql = _all_sql()
        assert "NULLIF" in sql

    def test_output_column_aliases(self):
        sql = _all_sql()
        assert "data_provider" in sql
        assert "is_shown_at" in sql
        assert "landing_page" in sql
        assert "dataset_name" in sql

    def test_step_count(self):
        steps = items_enriched_steps()
        assert len(steps) == 12

    def test_final_step_is_marked(self):
        steps = items_enriched_steps()
        assert steps[-1].is_final is True
        assert all(not s.is_final for s in steps[:-1])
