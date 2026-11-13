"""带代理与退避的 HTTP 客户端：失败先退避，仍失败才换 IP，最后降级网页抓取。"""
from __future__ import annotations

import time
import urllib.request
from collections.abc import Callable
from typing import Optional

from .qingguo_proxy import ProxyLease, QingguoProxyPool

Fetch = Callable[[str, Optional[str]], str]


def _fetch_via(url: str, proxy: Optional[str]) -> str:
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    opener = urllib.request.build_opener(handler)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return opener.open(request, timeout=15).read().decode("utf-8", "ignore")


class ProxyHttpClient:
    """实现在「复用租约 → 退避 → 换 IP」之间取平衡。

    Args:
        pool: 代理池，None 表示直连。
        fetch: 底层取数函数，参数为 (url, proxy)，便于测试。
        retries: 同一 IP 的最大尝试次数。
        backoff: 退避基数（秒）。
    """

    def __init__(
        self,
        pool: Optional[QingguoProxyPool] = None,
        fetch: Fetch | None = None,
        retries: int = 2,
        backoff: float = 0.5,
    ) -> None:
        self._pool = pool
        self._fetch = fetch or _fetch_via
        self._retries = retries
        self._backoff = backoff
        self.stats = {"requests": 0, "reused": 0, "rotations": 0, "failures": 0}

    def get(self, url: str) -> str:
        """取页面文本。

        Args:
            url: 目标地址。

        Returns:
            响应文本。

        Raises:
            OSError: 重试与换 IP 均失败。
        """
        lease: Optional[ProxyLease] = self._pool.acquire() if self._pool else None
        proxy = f"http://{lease.ip}:{lease.port}" if lease else None

        for attempt in range(self._retries + 1):
            self.stats["requests"] += 1
            try:
                return self._fetch(url, proxy)
            except (OSError, ValueError):
                if attempt < self._retries:
                    time.sleep(self._backoff * (2 ** attempt))
                    continue
                if lease and self._pool:
                    self._pool.report_bad(lease)
                    self.stats["rotations"] += 1
                    return self.get(url)  # 换 IP 后重试一次
                self.stats["failures"] += 1
                raise
        raise OSError(f"抓取失败: {url}")

    def get_or_scrape(self, url: str, scraper: Callable[[str], Optional[str]]) -> Optional[str]:
        """接口失败后降级到网页抓取。

        Args:
            url: API 地址。
            scraper: 网页抓取函数，接收代码或地址返回文本。

        Returns:
            接口结果或网页结果；都失败返回 None。
        """
        try:
            return self.get(url)
        except (OSError, ValueError):
            return scraper(url)
