"""东财选股器股池适配器：自然语言条件直连，列名自描述。

中文列名只在本文件出现，对外输出领域股池条目。
"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable

from ..domain.aggregates import PoolEntry, PoolWindow

_URL = "https://np-tjxg-b.eastmoney.com/api/smart-tag/stock/v3/pw/search-code"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/129.0 Safari/537.36",
    "Content-Type": "application/json",
    "Origin": "https://xuangu.eastmoney.com",
    "Referer": "https://xuangu.eastmoney.com/",
}
_MONTH_CONDITION = (
    "本月涨幅前十；不要ST股；不要退市股；不要北交所；不要科创板；不要创业板；竞价涨幅大于-11%"
)
_D60_CONDITION = (
    "近60日涨幅前七；不要ST股；不要退市股；不要北交所；不要科创板；不要创业板；"
    "不要新股和次新股；竞价涨幅大于-11%"
)
_POST = Callable[[dict], dict]


def _default_post(body: dict) -> dict:
    request = urllib.request.Request(
        _URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=_HEADERS,
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=15).read().decode("utf-8", "ignore"))


def _pick(row: dict, *keywords: str) -> str:
    for key, value in row.items():
        if any(word in key for word in keywords):
            return str(value)
    return ""


def _number(row: dict, *keywords: str) -> float:
    raw = _pick(row, *keywords).replace("%", "").replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


class EastmoneyPoolAdapter:
    """实现 PoolPort：双窗口股池。

    Args:
        post: 提交函数，注入后便于测试。
    """

    def __init__(self, post: _POST | None = None) -> None:
        self._post = post or _default_post

    def month_top(self, n: int = 10) -> list[PoolEntry]:
        """月度涨幅前十。

        Args:
            n: 条数上限。

        Returns:
            按名次升序的股池条目。
        """
        return self._query(_MONTH_CONDITION, PoolWindow.MONTH, n)

    def d60_top(self, n: int = 7) -> list[PoolEntry]:
        """近 60 日涨幅前七。

        Args:
            n: 条数上限。

        Returns:
            按名次升序的股池条目。
        """
        return self._query(_D60_CONDITION, PoolWindow.D60, n)

    def _query(self, condition: str, window: PoolWindow, limit: int) -> list[PoolEntry]:
        payload = self._post(self._body(condition))
        if payload.get("code") == "201":
            # 盘前集合竞价字段尚未生成，带竞价条件会返回空结果；去掉该条件重试
            payload = self._post(self._body(condition.replace("；竞价涨幅大于-11%", "")))
        if payload.get("code") == "201":
            return []
        if payload.get("code") != "100":
            raise RuntimeError(f"选股器返回异常 code={payload.get('code')} msg={payload.get('msg')}")
        result = (payload.get("data") or {}).get("result") or {}
        titles = {column["key"]: column["title"] for column in result.get("columns") or []}
        rows = [{titles.get(k, k): v for k, v in row.items()} for row in result.get("dataList") or []]

        entries: list[PoolEntry] = []
        for index, row in enumerate(rows[:limit], start=1):
            code = _pick(row, "股票代码", "代码")
            if not code:
                continue
            entries.append(PoolEntry(
                code=code[-6:],
                name=_pick(row, "股票名称", "名称"),
                rank=index,
                window=window,
                range_pct=_number(row, "区间涨跌幅", "本月涨幅", "近60日涨幅", "区间涨幅"),
                pct=_number(row, "涨跌幅"),
                turnover=_number(row, "换手率"),
                auction_pct=_number(row, "集合竞价"),
            ))
        return entries

    @staticmethod
    def _body(condition: str) -> dict:
        return {
            "needAmbiguousSuggest": True,
            "pageSize": 50,
            "pageNo": 1,
            "fingerprint": "84151842d0ff834d33c1b482db9020f7",
            "matchWord": "",
            "shareToGuba": False,
            "timestamp": "0",
            "requestId": "brief",
            "removedConditionIdList": [],
            "allCode": True,
            "ownSelectAll": False,
            "needCorrect": True,
            "client": "WEB",
            "product": "",
            "needShowStockNum": False,
            "biz": "web_ai_select_stocks",
            "xcId": "",
            "gids": [],
            "dxInfoNew": [],
            "keyWordNew": condition,
            "customDataNew": json.dumps(
                [{"type": "text", "value": condition, "extra": ""}], ensure_ascii=False
            ),
        }
