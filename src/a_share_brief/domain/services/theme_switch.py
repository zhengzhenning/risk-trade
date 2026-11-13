"""题材切换：归属段校验、当日题材解析与切换事件识别。"""
from __future__ import annotations

from datetime import date

from ..aggregates import StockTheme, ThemeSwitch


class ThemeConflict(ValueError):
    """题材区间冲突：同一日出现两个生效归属。"""


def active_theme(segments: tuple[StockTheme, ...], day: date) -> StockTheme | None:
    """取指定交易日生效的题材归属。

    Args:
        segments: 同一标的的题材归属段。
        day: 交易日。

    Returns:
        生效段；无归属返回 None。

    Raises:
        ThemeConflict: 同日命中多个归属。
    """
    hits = [s for s in segments if s.covers(day)]
    if len(hits) > 1:
        raise ThemeConflict(f"code={hits[0].code} day={day} themes={[h.theme_id for h in hits]}")
    return hits[0] if hits else None


def detect_switches(segments: tuple[StockTheme, ...]) -> tuple[ThemeSwitch, ...]:
    """按时间顺序识别题材切换。

    Args:
        segments: 同一标的的题材归属段。

    Returns:
        切换事件列表；相邻段题材相同则跳过。
    """
    ordered = sorted(segments, key=lambda s: s.start_day)
    out: list[ThemeSwitch] = []
    for prev, curr in zip(ordered, ordered[1:]):
        if prev.theme_id == curr.theme_id:
            continue
        out.append(ThemeSwitch(
            code=curr.code,
            day=curr.start_day,
            from_theme=curr.switch_from or prev.theme_id,
            to_theme=curr.theme_id,
            evidence=curr.evidence,
        ))
    return tuple(out)


def validate_segments(segments: tuple[StockTheme, ...]) -> None:
    """校验归属段合法：不重叠、切换来源连续。

    Args:
        segments: 同一标的的题材归属段。

    Raises:
        ThemeConflict: 区间重叠或 switch_from 与上一段不一致。
    """
    ordered = sorted(segments, key=lambda s: s.start_day)
    for prev, curr in zip(ordered, ordered[1:]):
        if prev.end_day is None or curr.start_day <= prev.end_day:
            raise ThemeConflict(f"overlap code={curr.code} theme={curr.theme_id} at {curr.start_day}")
        if curr.switch_from and curr.switch_from != prev.theme_id:
            raise ThemeConflict(f"switch_from mismatch code={curr.code} expect={prev.theme_id} got={curr.switch_from}")
