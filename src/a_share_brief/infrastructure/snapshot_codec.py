"""快照序列化：仅本文件处理 JSON 与领域对象的互转。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, fields
from datetime import date
from typing import Any

from ..domain.aggregates import (
    AlertLevel,
    Board,
    Exchange,
    Index,
    IndexBase,
    IndexCategory,
    IndexQuote,
    LimitState,
    PoolEntry,
    PoolRanking,
    PoolWindow,
    Stock,
    StockAlert,
    StockBase,
    StockQuote,
)


def _plain(value: Any) -> Any:
    """把枚举与日期转成可 JSON 化的值。"""
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    return value


def _as_dict(entity: Any) -> dict[str, Any]:
    return {key: _plain(value) for key, value in asdict(entity).items()}


def stock_to_dict(stock: Stock) -> dict[str, Any]:
    return {
        "base": _as_dict(stock.base),
        "quote": _as_dict(stock.quote) if stock.quote else None,
        "alert": _as_dict(stock.alert) if stock.alert else None,
    }


def stock_from_dict(payload: dict[str, Any]) -> Stock:
    base = StockBase(**_convert(payload["base"], StockBase))
    quote = StockQuote(**_convert(payload["quote"], StockQuote)) if payload.get("quote") else None
    alert = StockAlert(**_convert(payload["alert"], StockAlert)) if payload.get("alert") else None
    return Stock(base=base, quote=quote, alert=alert)


def index_to_dict(index: Index) -> dict[str, Any]:
    return {
        "base": _as_dict(index.base),
        "quote": _as_dict(index.quote) if index.quote else None,
    }


def index_from_dict(payload: dict[str, Any]) -> Index:
    base = IndexBase(**_convert(payload["base"], IndexBase))
    quote = IndexQuote(**_convert(payload["quote"], IndexQuote)) if payload.get("quote") else None
    return Index(base=base, quote=quote)


def ranking_to_dict(ranking: PoolRanking) -> dict[str, Any]:
    return {
        "day": ranking.day.isoformat(),
        "window": ranking.window.value,
        "captured_at": ranking.captured_at,
        "baseline": ranking.baseline,
        "entries": [_as_dict(entry) for entry in ranking.entries],
    }


def ranking_from_dict(payload: dict[str, Any]) -> PoolRanking:
    window = PoolWindow(payload["window"])
    entries = tuple(
        PoolEntry(**{**entry, "window": PoolWindow(entry["window"])})
        for entry in payload.get("entries", [])
    )
    return PoolRanking(
        day=date.fromisoformat(payload["day"]),
        window=window,
        entries=entries,
        captured_at=payload.get("captured_at", ""),
        baseline=bool(payload.get("baseline", False)),
    )


def _to_date(value: Any) -> date | None:
    return date.fromisoformat(value) if isinstance(value, str) else None


_FIELD_CONVERTERS: dict[type, dict[str, Callable[[Any], Any]]] = {
    StockBase: {"exchange": Exchange, "board": Board, "list_date": _to_date},
    StockQuote: {"day": _to_date, "limit_state": LimitState},
    StockAlert: {"day": _to_date, "level": AlertLevel, "triggered_day": _to_date, "monitor_end": _to_date},
    IndexBase: {"exchange": Exchange, "category": IndexCategory, "launch_date": _to_date},
    IndexQuote: {"day": _to_date},
}


def _convert(payload: dict[str, Any], entity: type) -> dict[str, Any]:
    """按实体声明做最小反序列化：日期与枚举字段需要还原类型。"""

    converters = _FIELD_CONVERTERS.get(entity, {})
    result = dict(payload)
    for field in fields(entity):
        name = field.name
        if name not in result:
            continue
        converter = converters.get(name)
        if converter and result[name] is not None:
            result[name] = converter(result[name])
    return result
