"""题材适配器装饰：成功即缓存，失败回退最近一次结果。"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date

from .labels_cache import load_latest, save

_LOG = logging.getLogger(__name__)


class CachedThemeAdapter:
    """包装主题端口，保证空结果不覆盖历史。

    Args:
        inner: 真实题材适配器。
        day: 交易日，用于缓存文件命名。
    """

    def __init__(self, inner, day: date | None = None) -> None:
        self._inner = inner
        self._day = (day or date.today()).isoformat()

    def themes_of(self, codes: Iterable[str]) -> dict[str, tuple[str, ...]]:
        """抓取标签，失败时回退缓存。"""
        codes = list(codes)
        rows: dict[str, tuple[str, ...]] = {}
        for start in range(0, len(codes), 5):   # 分批，整批失败不影响已取到的
            chunk = codes[start:start + 5]
            for _ in range(2):
                try:
                    rows.update(self._inner.themes_of(chunk))
                    break
                except (OSError, ValueError):
                    continue
        if rows:
            cached_old = load_latest(self._day)
            merged = {**cached_old, **{code: list(labels) for code, labels in rows.items()}}
            save(self._day, merged)
            return {code: tuple(labels) for code, labels in merged.items()}
        cached = load_latest(self._day)
        if cached:
            _LOG.warning("theme fetch empty, fallback cache day=%s size=%d",
                         self._day, len(cached))
            return {code: tuple(labels) for code, labels in cached.items()}
        return rows

    def sectors_of(self, codes: Iterable[str]) -> dict[str, str]:
        """透传板块查询，失败返回空。

        Args:
            codes: 标的代码。

        Returns:
            代码到板块名。
        """
        try:
            return self._inner.sectors_of(codes)
        except (OSError, ValueError, AttributeError):
            return {}
