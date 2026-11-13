"""交易日历：监管期等按交易日推算的业务规则。

节假日为外部数据，默认空集合；调用方需注入当年休市日，未注入时只跳过周末。
"""
from __future__ import annotations

from datetime import date, timedelta

# 严重异动后的重点监控期（交易日），交易所口径
MONITOR_DAYS = 10


def trading_days_after(start: date, days: int, holidays: frozenset[date] = frozenset()) -> date:
    """计算 start 之后第 N 个交易日（不含 start 当日）。

    Args:
        start: 起始交易日。
        days: 交易日数量，必须为正。
        holidays: 休市日集合，默认空（仅跳过周末）。

    Returns:
        第 N 个交易日的日期。

    Raises:
        ValueError: days 不为正。
    """
    if days <= 0:
        raise ValueError(f"交易日数量必须为正: {days}")
    current = start
    counted = 0
    while counted < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            counted += 1
    return current
