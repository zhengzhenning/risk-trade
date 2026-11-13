"""东财严重异动适配器：把预测与记录接口映射为领域异动聚合。

第三方字段（c/x/t/a/o/MAX_DAYS 等）只在本文件出现。
"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Iterable
from datetime import date

from ..domain.aggregates import AlertLevel, StockAlert
from ..domain.services.trading_calendar import MONITOR_DAYS, trading_days_after

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120 Safari/537.36",
    "Referer": "https://vipmoney.eastmoney.com/",
}
_PREDICT = (
    "https://dycalchis.eastmoney.com/price-anomaly/list?team=h5&product=EastMoney&client=WAP"
    "&version=9001&name=WAP&user=12&pageSize=500&pageNo=1&riseOnly=0&showBJS=1&cb=cb"
)
_RECORD = (
    "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    "?reportName=RPT_WATCH_UNUSUAL_FLUCTUATE"
    "&columns=SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,MAX_DAYS,"
    "DEVUATION_VALUE,CHANGE_RATE_TARGET,IS_HAPPEN,UNUSUAL_TYPE"
    "&quoteColumns=&filter=&pageNumber=1&pageSize=500&sortTypes=-1"
    "&sortColumns=&source=SECURITIES&client=APP"
)

Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=15).read().decode("utf-8", "ignore")


def _jsonp(raw: str) -> dict:
    start, end = raw.find("("), raw.rfind(")")
    return json.loads(raw[start + 1 : end]) if start >= 0 and end > start else json.loads(raw)


def _level_of(need: float | None, current: float | None) -> AlertLevel:
    if need is None or current is None:
        return AlertLevel.FAR
    distance = round(float(need) - float(current), 2)
    if distance <= 0:
        return AlertLevel.TRIGGERED
    if distance <= 2:
        return AlertLevel.NEAR
    if distance <= 5:
        return AlertLevel.WATCH
    return AlertLevel.FAR


class EastmoneyAlertAdapter:
    """实现 AlertPort：返回代码到异动聚合的映射。

    Args:
        fetch: HTTP 取数函数，注入后便于测试。
        holidays: 当年休市日，用于推算监管期结束日。
    """

    def __init__(
        self,
        fetch: Fetch | None = None,
        holidays: frozenset[date] = frozenset(),
    ) -> None:
        self._fetch = fetch or _default_fetch
        self._holidays = holidays

    def unusual(self, codes: Iterable[str], day: date | None = None) -> dict[str, StockAlert]:
        """拉取并映射异动数据。

        Args:
            codes: 需要过滤的股票代码集合。
            day: 统计日，默认今天。

        Returns:
            代码到异动聚合的映射；无数据返回空字典。
        """
        wanted = set(codes)
        today = day or date.today()
        predictions = self._predictions(wanted)
        records = self._records(wanted)

        result: dict[str, StockAlert] = {}
        for code in set(predictions) | set(records):
            items = predictions.get(code, [])
            triggered = records.get(code, [])
            alert = StockAlert(
                code=code,
                day=today,
                level=AlertLevel.TRIGGERED if triggered else self._best_level(items),
                rule=(triggered[0]["rule"] if triggered else (items[0].get("rule") or "")),
                dev_pct=items[0].get("dev", 0.0) if items else 0.0,
                need_pct=items[0].get("need", 0.0) if items else 0.0,
                current_pct=items[0].get("now", 0.0) if items else 0.0,
                distance_pct=items[0].get("dist", 0.0) if items else 0.0,
                triggered_day=triggered[0]["day"] if triggered else None,
                monitor_end=triggered[0]["monitor_end"] if triggered else None,
            )
            result[code] = alert
        return result

    def _predictions(self, wanted: set[str]) -> dict[str, list[dict]]:
        rows = (_jsonp(self._fetch(_PREDICT)).get("data")) or []
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            code = str(row.get("c") or "")
            if code not in wanted or int(row.get("o") or 0) != 0:
                continue
            need, current = row.get("t"), row.get("a")
            grouped.setdefault(code, []).append({
                "dev": float(row.get("x") or 0),
                "need": float(need) if need is not None else None,
                "now": float(current) if current is not None else None,
                "dist": round(float(need) - float(current), 2)
                if need is not None and current is not None else 99.0,
                "rule": "",
            })
        for items in grouped.values():
            items.sort(key=lambda item: abs(item["dist"]))
        return grouped

    def _records(self, wanted: set[str]) -> dict[str, list[dict]]:
        payload = json.loads(self._fetch(_RECORD))
        rows = ((payload.get("result") or {}).get("data")) or []
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            code = str(row.get("SECURITY_CODE") or "")
            trade_day = (row.get("TRADE_DATE") or "")[:10]
            if code not in wanted or str(row.get("IS_HAPPEN")) != "1" or not trade_day:
                continue
            triggered_on = date.fromisoformat(trade_day)
            grouped.setdefault(code, []).append({
                "day": triggered_on,
                "rule": row.get("UNUSUAL_TYPE") or "",
                "monitor_end": trading_days_after(triggered_on, MONITOR_DAYS, self._holidays),
            })
        for items in grouped.values():
            items.sort(key=lambda item: item["day"], reverse=True)
        return grouped

    @staticmethod
    def _best_level(items: list[dict]) -> AlertLevel:
        if not items:
            return AlertLevel.FAR
        order = {AlertLevel.TRIGGERED: 0, AlertLevel.NEAR: 1, AlertLevel.WATCH: 2, AlertLevel.FAR: 3}
        levels = [_level_of(item.get("need"), item.get("now")) for item in items]
        return min(levels, key=lambda level: order[level])
