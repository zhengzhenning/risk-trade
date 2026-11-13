"""PostgreSQL 快照仓库（P2 启用）。

表结构（与 docs/ARCHITECTURE.md 一致）：

    CREATE TABLE briefing_day (
        day        date    NOT NULL,
        revision   int     NOT NULL,
        payload    jsonb   NOT NULL,
        created_at timestamptz DEFAULT now(),
        PRIMARY KEY (day, revision)
    );
"""
from __future__ import annotations

from datetime import date

from ..domain.aggregates import Briefing, Stock


class PgRepoAdapter:
    def __init__(self, dsn: str) -> None:  # pragma: no cover - 依赖 pg
        import psycopg

        self._conn = psycopg.connect(dsn, autocommit=True)

    def save(self, briefing: Briefing) -> None:  # pragma: no cover
        payload = {
            "stocks": [s.__dict__ for s in briefing.stocks],
        }
        self._conn.execute(
            "INSERT INTO briefing_day(day, revision, payload) VALUES (%s,%s,%s)"
            " ON CONFLICT (day, revision) DO NOTHING",
            (briefing.day, briefing.revision, payload),
        )

    def load(self, day: date) -> Briefing | None:  # pragma: no cover
        row = self._conn.execute(
            "SELECT revision, payload FROM briefing_day WHERE day=%s ORDER BY revision DESC LIMIT 1",
            (day,),
        ).fetchone()
        if not row:
            return None
        revision, payload = row
        stocks = tuple(Stock(**s) for s in payload.get("stocks", []))
        return Briefing(day=day, stocks=stocks, revision=revision)
