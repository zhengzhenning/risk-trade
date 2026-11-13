"""PostgreSQL 快照仓库（P2 拟定，未在无 PG 环境验证）。

表结构见 deploy/schema.sql：briefing_day(day, revision, payload)。
"""
from __future__ import annotations

import json
from datetime import date

from ..domain.aggregates import Briefing
from .snapshot_codec import (
    index_from_dict,
    index_to_dict,
    ranking_from_dict,
    ranking_to_dict,
    stock_from_dict,
    stock_to_dict,
)


class PgRepoAdapter:
    """把快照读写到 PostgreSQL。

    Args:
        dsn: 连接串，如 ``postgresql://user@127.0.0.1/brief``。
    """

    def __init__(self, dsn: str) -> None:  # pragma: no cover - 依赖真实 PG
        import psycopg

        self._conn = psycopg.connect(dsn, autocommit=True)

    def save(self, briefing: Briefing) -> None:  # pragma: no cover
        """写入当前版本快照。

        Args:
            briefing: 当日快照。
        """
        payload = {
            "indexes": [index_to_dict(item) for item in briefing.indexes],
            "rankings": [ranking_to_dict(item) for item in briefing.rankings],
            "stocks": [stock_to_dict(item) for item in briefing.stocks],
        }
        self._conn.execute(
            "INSERT INTO briefing_day(day, revision, payload) VALUES (%s, %s, %s)"
            " ON CONFLICT (day, revision) DO NOTHING",
            (briefing.day, briefing.revision, json.dumps(payload, ensure_ascii=False)),
        )

    def load(self, day: date) -> Briefing | None:  # pragma: no cover
        """读取当日最新版本。

        Args:
            day: 交易日。

        Returns:
            快照；无记录返回 None。
        """
        row = self._conn.execute(
            "SELECT revision, payload FROM briefing_day WHERE day=%s"
            " ORDER BY revision DESC LIMIT 1",
            (day,),
        ).fetchone()
        if not row:
            return None
        revision, payload = row
        if isinstance(payload, str):
            payload = json.loads(payload)
        return Briefing(
            day=day,
            revision=int(revision),
            indexes=tuple(index_from_dict(item) for item in payload.get("indexes", [])),
            rankings=tuple(ranking_from_dict(item) for item in payload.get("rankings", [])),
            stocks=tuple(stock_from_dict(item) for item in payload.get("stocks", [])),
        )
