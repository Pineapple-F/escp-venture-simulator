"""Select enterprises with enough past event history for model inference."""

from pathlib import Path

import duckdb


MIN_EVENT_MONTHS = 3
MIN_HISTORY_SPAN_MONTHS = 6


def model_ready_companies(candidate_ids, history_paths, cutoff):
    """Apply the clean_v1 past-only history threshold at a deployment cutoff."""
    candidates = {str(value) for value in candidate_ids}
    paths = [Path(path) for path in history_paths if Path(path).is_file()]
    if not paths:
        raise FileNotFoundError("找不到模型清洗历史，不能构建预测企业池")

    union = " UNION ALL ".join(
        "SELECT CAST(id AS VARCHAR) AS id, CAST(day AS DATE) AS day "
        "FROM read_parquet(?)" for _ in paths
    )
    query = f"""
        WITH history AS ({union}),
        event_months AS (
          SELECT DISTINCT id, date_trunc('month', day) AS event_month
          FROM history WHERE day <= CAST(? AS DATE)
        ),
        company_history AS (
          SELECT id, count(*) AS event_month_count,
                 min(event_month) AS first_event_month,
                 max(event_month) AS last_event_month
          FROM event_months GROUP BY id
        )
        SELECT id, event_month_count, first_event_month, last_event_month
        FROM company_history
        WHERE event_month_count >= ?
          AND date_diff('month', first_event_month, last_event_month) >= ?
    """
    rows = duckdb.connect().execute(
        query,
        [str(path) for path in paths] +
        [cutoff, MIN_EVENT_MONTHS, MIN_HISTORY_SPAN_MONTHS],
    ).fetchall()
    eligible = candidates.intersection(row[0] for row in rows)
    return eligible, {
        "history_filter": (
            f"至少{MIN_EVENT_MONTHS}个不同事件月份，且首末事件跨度至少"
            f"{MIN_HISTORY_SPAN_MONTHS}个月"
        ),
        "history_filter_cutoff": cutoff,
        "history_filter_sources": [path.name for path in paths],
        "cohort_before_history_filter": len(candidates),
        "history_model_ready_companies": len(eligible),
        "history_sparse_excluded": len(candidates) - len(eligible),
    }
