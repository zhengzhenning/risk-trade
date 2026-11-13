"""东财 F10 适配器：取个股所属板块，提炼为题材标签。"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Iterable

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120 Safari/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}
_URL = "https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code={symbol}"
Fetch = Callable[[str], str]

# 板块名里出现的非题材标签（地域、财务、资金属性）
_NOISE = ("板块", "概念", "首亏", "预亏", "预增", "微利", "题材股", "多板", "融资融券",
          "沪股通", "深股通", "转债标的", "机构重仓", "基金重仓", "昨日", "涨停")


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=12).read().decode("utf-8", "ignore")


def _symbol(code: str) -> str:
    return ("SH" if code.startswith("6") else "SZ") + code


class EastmoneyThemeAdapter:
    """实现 ThemePort：返回代码到题材标签的映射。

    Args:
        fetch: HTTP 取数函数，注入后便于测试。
        max_labels: 每只股票保留的题材数量。
    """

    def __init__(self, fetch: Fetch | None = None, max_labels: int = 1) -> None:
        self._fetch = fetch or _default_fetch
        self._max_labels = max_labels

    def themes_of(self, codes: Iterable[str]) -> dict[str, tuple[str, ...]]:
        """取多只股票的题材标签。

        Args:
            codes: 股票代码集合。

        Returns:
            代码到题材元组的映射；取不到或全为噪声的标的省略。
        """
        result: dict[str, tuple[str, ...]] = {}
        for code in codes:
            try:
                payload = json.loads(self._fetch(_URL.format(symbol=_symbol(code))))
                labels = _labels(payload.get("ssbk") or [])
            except (OSError, ValueError, KeyError):
                continue
            if labels:
                result[code] = labels[: self._max_labels]
        return result


def _labels(boards: list[dict]) -> tuple[str, ...]:
    """从板块列表提炼行业题材。

    东财 F10 的 ssbk 前三条为「一级行业 → 二级行业 → 三级行业」，其后是地域与概念；
    取前三条中最细的一级作为题材，避免把「光伏概念」这类炒作标签当成行业。

    Args:
        boards: F10 返回的板块条目。

    Returns:
        题材名元组；无有效行业时取首个非噪声板块。
    """
    names = [str(item.get("BOARD_NAME") or "") for item in boards[:3]]
    industries = [name for name in names if name and not any(word in name for word in _NOISE)]
    if industries:
        return (industries[-1],)
    fallback = [str(item.get("BOARD_NAME") or "") for item in boards]
    for name in fallback:
        if name and not any(word in name for word in _NOISE):
            return (name,)
    return ()
