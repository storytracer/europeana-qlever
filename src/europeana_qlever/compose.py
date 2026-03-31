"""DuckDB composition SQL for hybrid SPARQL/DuckDB export pipeline.

Phase 1 exports simple, flat SPARQL scans to Parquet "base tables".
Phase 2 (this module) generates DuckDB SQL that reads those Parquet files,
joins them, resolves languages, aggregates multi-valued properties, and
writes the final denormalized Parquet exports.

SQL templates use ``{exports_dir}`` as a placeholder — replaced at
execution time with the actual path to the exports directory.
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import SEPARATOR


@dataclass
class ComposeStep:
    """A single step in a multi-step DuckDB composition."""

    name: str
    sql: str
    is_final: bool = False


# ---------------------------------------------------------------------------
# Placeholder used in SQL templates — replaced at execution time
# ---------------------------------------------------------------------------
_DIR = "{exports_dir}"


def items_enriched_sql(
    separator: str = SEPARATOR,
    extra_languages: list[str] | None = None,
) -> str:
    """Generate the DuckDB SQL that composes ``items_enriched`` from base tables.

    Reads from: items_core, items_titles, items_descriptions, items_subjects,
    items_dates, items_languages, items_years, items_creators, agents.

    Parameters
    ----------
    separator
        Delimiter for multi-valued columns (default ``" ||| "``).
    extra_languages
        Additional languages beyond English and the item's vernacular.
        Each produces extra title/description columns.
    """
    extras = extra_languages or []

    # -- Title resolution CTE -----------------------------------------------
    extra_title_select = ""
    extra_title_cols = ""
    for lang in extras:
        safe = lang.replace("-", "_")
        extra_title_select += (
            f",\n        MAX(title) FILTER (WHERE lang = '{lang}') AS title_{safe}"
        )
        extra_title_cols += f",\n       t.title_{safe}"

    # -- Description resolution CTE -----------------------------------------
    extra_desc_select = ""
    extra_desc_cols = ""
    for lang in extras:
        safe = lang.replace("-", "_")
        extra_desc_select += (
            f",\n        MAX(description) FILTER (WHERE lang = '{lang}') AS description_{safe}"
        )
        extra_desc_cols += f",\n       d.description_{safe}"

    sep_escaped = separator.replace("'", "''")

    return f"""\
-- items_enriched: composed from component Parquet base tables via DuckDB
WITH
-- Vernacular language per item (pick first dc:language value)
vernacular AS (
    SELECT item, FIRST(language) AS lang
    FROM read_parquet('{_DIR}/items_languages.parquet')
    GROUP BY item
),
-- Language resolution for titles: en → vernacular → extras → any
title_resolved AS (
    SELECT
        t.item,
        MAX(t.title) FILTER (WHERE t.lang = 'en') AS title_en,
        FIRST(t.title) FILTER (WHERE t.lang = vl.lang) AS title_native,
        FIRST(t.lang) FILTER (WHERE t.lang = vl.lang) AS title_native_lang{extra_title_select},
        COALESCE(
            MAX(t.title) FILTER (WHERE t.lang = 'en'),
            FIRST(t.title) FILTER (WHERE t.lang = vl.lang),
            FIRST(t.title)
        ) AS title
    FROM read_parquet('{_DIR}/items_titles.parquet') t
    LEFT JOIN vernacular vl USING (item)
    GROUP BY t.item, vl.lang
),
-- Language resolution for descriptions
desc_resolved AS (
    SELECT
        d.item,
        MAX(d.description) FILTER (WHERE d.lang = 'en') AS description_en,
        FIRST(d.description) FILTER (WHERE d.lang = vl.lang) AS description_native,
        FIRST(d.lang) FILTER (WHERE d.lang = vl.lang) AS description_native_lang{extra_desc_select},
        COALESCE(
            MAX(d.description) FILTER (WHERE d.lang = 'en'),
            FIRST(d.description) FILTER (WHERE d.lang = vl.lang),
            FIRST(d.description)
        ) AS description
    FROM read_parquet('{_DIR}/items_descriptions.parquet') d
    LEFT JOIN vernacular vl USING (item)
    GROUP BY d.item, vl.lang
),
-- Aggregate multi-valued properties
subjects_agg AS (
    SELECT item, STRING_AGG(DISTINCT subject, '{sep_escaped}') AS subjects
    FROM read_parquet('{_DIR}/items_subjects.parquet')
    GROUP BY item
),
dates_agg AS (
    SELECT item, STRING_AGG(DISTINCT date, '{sep_escaped}') AS dates
    FROM read_parquet('{_DIR}/items_dates.parquet')
    GROUP BY item
),
years_agg AS (
    SELECT item, STRING_AGG(DISTINCT year, '{sep_escaped}') AS years
    FROM read_parquet('{_DIR}/items_years.parquet')
    GROUP BY item
),
languages_agg AS (
    SELECT item, STRING_AGG(DISTINCT language, '{sep_escaped}') AS languages
    FROM read_parquet('{_DIR}/items_languages.parquet')
    GROUP BY item
),
-- Resolve agent labels: en → any
agent_labels AS (
    SELECT agent,
           COALESCE(
               MAX(name) FILTER (WHERE lang = 'en'),
               FIRST(name)
           ) AS label
    FROM read_parquet('{_DIR}/agents.parquet')
    GROUP BY agent
),
-- Creator resolution: join with agent labels, aggregate
creators_agg AS (
    SELECT
        c.item,
        STRING_AGG(DISTINCT COALESCE(a.label, c.creator_value), '{sep_escaped}') AS creators,
        STRING_AGG(DISTINCT CASE WHEN c.is_iri THEN c.creator_value END, '{sep_escaped}') AS creator_uris
    FROM read_parquet('{_DIR}/items_creators.parquet') c
    LEFT JOIN agent_labels a ON c.creator_value = a.agent AND c.is_iri
    GROUP BY c.item
)
-- Final denormalized join
SELECT
    i.item,
    t.title, t.title_en, t.title_native, t.title_native_lang{extra_title_cols},
    d.description, d.description_en, d.description_native, d.description_native_lang{extra_desc_cols},
    cr.creators, cr.creator_uris,
    s.subjects, dt.dates, y.years, l.languages,
    i.type, i.country, i.dataProvider AS data_provider,
    i.rights, i.completeness,
    i.isShownAt AS is_shown_at, i.isShownBy AS is_shown_by,
    i.preview, i.landingPage AS landing_page,
    i.datasetName AS dataset_name
FROM read_parquet('{_DIR}/items_core.parquet') i
LEFT JOIN title_resolved t USING (item)
LEFT JOIN desc_resolved d USING (item)
LEFT JOIN subjects_agg s USING (item)
LEFT JOIN creators_agg cr USING (item)
LEFT JOIN dates_agg dt USING (item)
LEFT JOIN years_agg y USING (item)
LEFT JOIN languages_agg l USING (item)
"""


def items_enriched_steps(
    separator: str = SEPARATOR,
    extra_languages: list[str] | None = None,
) -> list[ComposeStep]:
    """Return ``items_enriched`` as discrete steps for progress logging.

    Each step creates a DuckDB temp table for one CTE.  The final step
    is a SELECT (not a CREATE) intended to be wrapped in a COPY statement
    by the caller.

    Parameters are identical to :func:`items_enriched_sql`.
    """
    extras = extra_languages or []
    sep_escaped = separator.replace("'", "''")

    # -- Extra language columns for title/description -----------------------
    extra_title_select = ""
    extra_title_cols = ""
    for lang in extras:
        safe = lang.replace("-", "_")
        extra_title_select += (
            f",\n        MAX(title) FILTER (WHERE lang = '{lang}') AS title_{safe}"
        )
        extra_title_cols += f",\n       t.title_{safe}"

    extra_desc_select = ""
    extra_desc_cols = ""
    for lang in extras:
        safe = lang.replace("-", "_")
        extra_desc_select += (
            f",\n        MAX(description) FILTER (WHERE lang = '{lang}') AS description_{safe}"
        )
        extra_desc_cols += f",\n       d.description_{safe}"

    steps: list[ComposeStep] = []

    # 1. vernacular
    steps.append(ComposeStep("vernacular", f"""\
CREATE TEMP TABLE vernacular AS
    SELECT item, FIRST(language) AS lang
    FROM read_parquet('{_DIR}/items_languages.parquet')
    GROUP BY item"""))

    # 2. title_resolved
    steps.append(ComposeStep("title_resolved", f"""\
CREATE TEMP TABLE title_resolved AS
    SELECT
        t.item,
        MAX(t.title) FILTER (WHERE t.lang = 'en') AS title_en,
        FIRST(t.title) FILTER (WHERE t.lang = vl.lang) AS title_native,
        FIRST(t.lang) FILTER (WHERE t.lang = vl.lang) AS title_native_lang{extra_title_select},
        COALESCE(
            MAX(t.title) FILTER (WHERE t.lang = 'en'),
            FIRST(t.title) FILTER (WHERE t.lang = vl.lang),
            FIRST(t.title)
        ) AS title
    FROM read_parquet('{_DIR}/items_titles.parquet') t
    LEFT JOIN vernacular vl USING (item)
    GROUP BY t.item, vl.lang"""))

    # 3. desc_resolved
    steps.append(ComposeStep("desc_resolved", f"""\
CREATE TEMP TABLE desc_resolved AS
    SELECT
        d.item,
        MAX(d.description) FILTER (WHERE d.lang = 'en') AS description_en,
        FIRST(d.description) FILTER (WHERE d.lang = vl.lang) AS description_native,
        FIRST(d.lang) FILTER (WHERE d.lang = vl.lang) AS description_native_lang{extra_desc_select},
        COALESCE(
            MAX(d.description) FILTER (WHERE d.lang = 'en'),
            FIRST(d.description) FILTER (WHERE d.lang = vl.lang),
            FIRST(d.description)
        ) AS description
    FROM read_parquet('{_DIR}/items_descriptions.parquet') d
    LEFT JOIN vernacular vl USING (item)
    GROUP BY d.item, vl.lang"""))

    # 4. subjects_agg
    steps.append(ComposeStep("subjects_agg", f"""\
CREATE TEMP TABLE subjects_agg AS
    SELECT item, STRING_AGG(DISTINCT subject, '{sep_escaped}') AS subjects
    FROM read_parquet('{_DIR}/items_subjects.parquet')
    GROUP BY item"""))

    # 5. dates_agg
    steps.append(ComposeStep("dates_agg", f"""\
CREATE TEMP TABLE dates_agg AS
    SELECT item, STRING_AGG(DISTINCT date, '{sep_escaped}') AS dates
    FROM read_parquet('{_DIR}/items_dates.parquet')
    GROUP BY item"""))

    # 6. years_agg
    steps.append(ComposeStep("years_agg", f"""\
CREATE TEMP TABLE years_agg AS
    SELECT item, STRING_AGG(DISTINCT year, '{sep_escaped}') AS years
    FROM read_parquet('{_DIR}/items_years.parquet')
    GROUP BY item"""))

    # 7. languages_agg
    steps.append(ComposeStep("languages_agg", f"""\
CREATE TEMP TABLE languages_agg AS
    SELECT item, STRING_AGG(DISTINCT language, '{sep_escaped}') AS languages
    FROM read_parquet('{_DIR}/items_languages.parquet')
    GROUP BY item"""))

    # 8. agent_labels
    steps.append(ComposeStep("agent_labels", f"""\
CREATE TEMP TABLE agent_labels AS
    SELECT agent,
           COALESCE(
               MAX(name) FILTER (WHERE lang = 'en'),
               FIRST(name)
           ) AS label
    FROM read_parquet('{_DIR}/agents.parquet')
    GROUP BY agent"""))

    # 9. creators_agg
    steps.append(ComposeStep("creators_agg", f"""\
CREATE TEMP TABLE creators_agg AS
    SELECT
        c.item,
        STRING_AGG(DISTINCT COALESCE(a.label, c.creator_value), '{sep_escaped}') AS creators,
        STRING_AGG(DISTINCT CASE WHEN c.is_iri THEN c.creator_value END, '{sep_escaped}') AS creator_uris
    FROM read_parquet('{_DIR}/items_creators.parquet') c
    LEFT JOIN agent_labels a ON c.creator_value = a.agent AND c.is_iri
    GROUP BY c.item"""))

    # 10. Final join (to be wrapped in COPY by caller)
    steps.append(ComposeStep("join_and_write", f"""\
SELECT
    i.item,
    t.title, t.title_en, t.title_native, t.title_native_lang{extra_title_cols},
    d.description, d.description_en, d.description_native, d.description_native_lang{extra_desc_cols},
    cr.creators, cr.creator_uris,
    s.subjects, dt.dates, y.years, l.languages,
    i.type, i.country, i.dataProvider AS data_provider,
    i.rights, i.completeness,
    i.isShownAt AS is_shown_at, i.isShownBy AS is_shown_by,
    i.preview, i.landingPage AS landing_page,
    i.datasetName AS dataset_name
FROM read_parquet('{_DIR}/items_core.parquet') i
LEFT JOIN title_resolved t USING (item)
LEFT JOIN desc_resolved d USING (item)
LEFT JOIN subjects_agg s USING (item)
LEFT JOIN creators_agg cr USING (item)
LEFT JOIN dates_agg dt USING (item)
LEFT JOIN years_agg y USING (item)
LEFT JOIN languages_agg l USING (item)""", is_final=True))

    return steps
