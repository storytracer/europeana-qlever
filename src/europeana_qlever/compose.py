"""DuckDB composition SQL for hybrid SPARQL/DuckDB export pipeline.

Phase 1 exports simple, flat SPARQL scans to Parquet "base tables".
Phase 2 (this module) generates DuckDB SQL that reads those Parquet files,
joins them, resolves entity URIs to labels, aggregates multi-valued
properties into native LIST/STRUCT types, and writes the final
denormalized Parquet export.

SQL templates use ``{exports_dir}`` as a placeholder — replaced at
execution time with the actual path to the exports directory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComposeStep:
    """A single step in a multi-step DuckDB composition."""

    name: str
    sql: str
    is_final: bool = False

    # Placeholder used in SQL templates — replaced at execution time.
    _DIR = "{exports_dir}"

    @staticmethod
    def items_resolved_steps() -> list[ComposeStep]:
        """Return ``items_resolved`` as discrete composition steps.

        Each step creates a DuckDB temp table.  The final step is a SELECT
        (not a CREATE) intended to be wrapped in a COPY statement by the caller.

        Output schema
        -------------
        - ``titles``: ``LIST<STRUCT<value VARCHAR, lang VARCHAR>>``
        - ``descriptions``: ``LIST<STRUCT<value VARCHAR, lang VARCHAR>>``
        - ``creators``: ``LIST<STRUCT<name VARCHAR, uri VARCHAR>>``
        - ``subjects``: ``LIST<STRUCT<label VARCHAR, uri VARCHAR>>``
        - ``dates``, ``years``, ``languages``: ``LIST<VARCHAR>``
        - ``reuse_level``: ``VARCHAR`` (open / restricted / prohibited)
        - ``mime_type``, ``width``, ``height``, ``file_bytes``, ``has_iiif``: web resource scalars
        - All other columns: scalar ``VARCHAR`` or ``BIGINT``
        """
        _DIR = ComposeStep._DIR
        steps: list[ComposeStep] = []

        # 1. titles_agg — all titles with language tags
        steps.append(ComposeStep("titles_agg", f"""\
CREATE TEMP TABLE titles_agg AS
    SELECT item,
           LIST({{value: NULLIF(title, ''), lang: NULLIF(lang, '')}}) AS titles
    FROM read_parquet('{_DIR}/items_titles.parquet')
    GROUP BY item"""))

        # 2. descriptions_agg — all descriptions with language tags
        steps.append(ComposeStep("descriptions_agg", f"""\
CREATE TEMP TABLE descriptions_agg AS
    SELECT item,
           LIST({{value: NULLIF(description, ''), lang: NULLIF(lang, '')}}) AS descriptions
    FROM read_parquet('{_DIR}/items_descriptions.parquet')
    GROUP BY item"""))

        # 3. concept_labels (resolve concept URIs to best label)
        steps.append(ComposeStep("concept_labels", f"""\
CREATE TEMP TABLE concept_labels AS
    SELECT concept,
           COALESCE(
               MAX(pref_label) FILTER (WHERE pref_label_lang = 'en'),
               FIRST(pref_label)
           ) AS label
    FROM read_parquet('{_DIR}/concepts_core.parquet')
    GROUP BY concept"""))

        # 4. subject_map (map distinct subject URIs to labels)
        steps.append(ComposeStep("subject_map", f"""\
CREATE TEMP TABLE subject_map AS
    SELECT s.uri, COALESCE(c.label, s.uri) AS label
    FROM (
        SELECT DISTINCT subject_value AS uri
        FROM read_parquet('{_DIR}/items_subjects.parquet')
        WHERE is_iri
    ) s
    LEFT JOIN concept_labels c ON s.uri = c.concept"""))

        # 5. subjects_agg (LIST<STRUCT<label, uri>>)
        steps.append(ComposeStep("subjects_agg", f"""\
CREATE TEMP TABLE subjects_agg AS
    SELECT
        s.item,
        LIST({{
            label: COALESCE(m.label, s.subject_value),
            uri: CASE WHEN s.is_iri THEN s.subject_value END
        }}) AS subjects
    FROM read_parquet('{_DIR}/items_subjects.parquet') s
    LEFT JOIN subject_map m ON s.subject_value = m.uri
    GROUP BY s.item"""))

        # 6. dates_agg
        steps.append(ComposeStep("dates_agg", f"""\
CREATE TEMP TABLE dates_agg AS
    SELECT item, LIST(date) AS dates
    FROM read_parquet('{_DIR}/items_dates.parquet')
    GROUP BY item"""))

        # 7. years_agg
        steps.append(ComposeStep("years_agg", f"""\
CREATE TEMP TABLE years_agg AS
    SELECT item, LIST(year) AS years
    FROM read_parquet('{_DIR}/items_years.parquet')
    GROUP BY item"""))

        # 8. languages_agg
        steps.append(ComposeStep("languages_agg", f"""\
CREATE TEMP TABLE languages_agg AS
    SELECT item, LIST(language) AS languages
    FROM read_parquet('{_DIR}/items_languages.parquet')
    GROUP BY item"""))

        # 9. agent_labels
        steps.append(ComposeStep("agent_labels", f"""\
CREATE TEMP TABLE agent_labels AS
    SELECT agent,
           COALESCE(
               MAX(pref_label) FILTER (WHERE pref_label_lang = 'en'),
               FIRST(pref_label)
           ) AS label
    FROM read_parquet('{_DIR}/agents_core.parquet')
    GROUP BY agent"""))

        # 10. creator_map (resolve unique IRI values to labels)
        steps.append(ComposeStep("creator_map", f"""\
CREATE TEMP TABLE creator_map AS
    SELECT c.uri, COALESCE(a.label, c.uri) AS label
    FROM (
        SELECT DISTINCT creator_value AS uri
        FROM read_parquet('{_DIR}/items_creators.parquet')
        WHERE is_iri
    ) c
    LEFT JOIN agent_labels a ON c.uri = a.agent"""))

        # 11. creators_agg (LIST<STRUCT<name, uri>>)
        steps.append(ComposeStep("creators_agg", f"""\
CREATE TEMP TABLE creators_agg AS
    SELECT
        c.item,
        LIST({{
            name: COALESCE(m.label, c.creator_value),
            uri: CASE WHEN c.is_iri THEN c.creator_value END
        }}) AS creators
    FROM read_parquet('{_DIR}/items_creators.parquet') c
    LEFT JOIN creator_map m ON c.creator_value = m.uri
    GROUP BY c.item"""))

        # 12. wr_agg (web resource metadata aggregation)
        steps.append(ComposeStep("wr_agg", f"""\
CREATE TEMP TABLE wr_agg AS
    SELECT
        item,
        FIRST(mime) AS mime_type,
        FIRST(TRY_CAST(width AS INTEGER)) AS width,
        FIRST(TRY_CAST(height AS INTEGER)) AS height,
        FIRST(TRY_CAST(bytes AS BIGINT)) AS file_bytes,
        BOOL_OR(has_service) AS has_iiif
    FROM read_parquet('{_DIR}/web_resources.parquet')
    GROUP BY item"""))

        # 13. Final join (to be wrapped in COPY by caller)
        steps.append(ComposeStep("join_and_write", f"""\
SELECT
    i.item,
    t.titles,
    d.descriptions,
    cr.creators,
    s.subjects, dt.dates, y.years, l.languages,
    i.type, i.country,
    NULLIF(i.dataProvider, '') AS data_provider,
    i.rights,
    CASE
      WHEN STARTS_WITH(i.rights, 'http://creativecommons.org/publicdomain/') THEN 'open'
      WHEN STARTS_WITH(i.rights, 'http://creativecommons.org/licenses/by/') THEN 'open'
      WHEN STARTS_WITH(i.rights, 'http://creativecommons.org/licenses/by-sa/') THEN 'open'
      WHEN STARTS_WITH(i.rights, 'http://creativecommons.org/licenses/') THEN 'restricted'
      WHEN i.rights IN (
        'http://rightsstatements.org/vocab/NoC-NC/1.0/',
        'http://rightsstatements.org/vocab/NoC-OKLR/1.0/',
        'http://rightsstatements.org/vocab/InC-EDU/1.0/'
      ) THEN 'restricted'
      ELSE 'prohibited'
    END AS reuse_level,
    i.completeness,
    NULLIF(i.isShownAt, '') AS is_shown_at,
    NULLIF(i.isShownBy, '') AS is_shown_by,
    NULLIF(i.preview, '') AS preview,
    NULLIF(i.landingPage, '') AS landing_page,
    NULLIF(i.datasetName, '') AS dataset_name,
    wr.mime_type,
    wr.width,
    wr.height,
    wr.file_bytes,
    wr.has_iiif
FROM read_parquet('{_DIR}/items_core.parquet') i
LEFT JOIN titles_agg t USING (item)
LEFT JOIN descriptions_agg d USING (item)
LEFT JOIN subjects_agg s USING (item)
LEFT JOIN creators_agg cr USING (item)
LEFT JOIN dates_agg dt USING (item)
LEFT JOIN years_agg y USING (item)
LEFT JOIN languages_agg l USING (item)
LEFT JOIN wr_agg wr USING (item)""", is_final=True))

        return steps
