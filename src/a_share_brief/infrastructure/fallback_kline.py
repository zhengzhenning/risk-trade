"""K 线主备组合：腾讯为主、东财兜底。"""
from __future__ import annotations

from ..domain.aggregates import Bar


class FallbackKLine:
    def __init__(self, primary, secondary) -> None:
        self._primary = primary
        self._secondary = secondary

    def daily(self, code: str, bars: int = 120) -> list[Bar]:
        try:
            rows = self._primary.daily(code, bars)
        except (OSError, ValueError):
            rows = []
        if rows:
            return rows
        try:
            return self._secondary.daily(code, bars)
        except (OSError, ValueError):
            return []
