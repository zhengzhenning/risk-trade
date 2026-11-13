"""题材归属：个股题材段与切换事件。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .theme import StockRole


@dataclass(frozen=True)
class StockTheme:
    """个股与题材的归属区间，可多段以支持题材切换。

    Attributes:
        code: 股票代码。
        theme_id: 题材标识。
        start_day: 归属开始日。
        end_day: 归属结束日，仍在其中为 None。
        role: 在题材中的角色。
        switch_from: 由哪个题材切换而来，首次归属为 None。
        confidence: 归属置信度 0–1，名字系需涨停池联动佐证。
        evidence: 归属证据（涨停池同系标的、公告、新闻）。
    """

    code: str
    theme_id: str
    start_day: date
    end_day: date | None = None
    role: StockRole = StockRole.FOLLOW
    switch_from: str | None = None
    confidence: float = 0.5
    evidence: tuple[str, ...] = ()

    def covers(self, day: date) -> bool:
        """判断该归属是否覆盖指定交易日。

        Args:
            day: 交易日。

        Returns:
            在区间内（含首尾）返回 True。
        """
        return self.start_day <= day and (self.end_day is None or day <= self.end_day)


@dataclass(frozen=True)
class ThemeSwitch:
    """题材切换事件：同一标的从旧题材进入新题材。

    Attributes:
        code: 股票代码。
        day: 切换日。
        from_theme: 旧题材标识。
        to_theme: 新题材标识。
        reason: 切换原因，如「原谐音系无新首板，东方系出现 2 只涨停」。
        evidence: 证据（涨停池、资讯链接）。
    """

    code: str
    day: date
    from_theme: str
    to_theme: str
    reason: str = ""
    evidence: tuple[str, ...] = ()
