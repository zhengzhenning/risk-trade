"""带代理与退避的 HTTP 客户端：失败先退避，仍失败才换 IP，最后降级网页抓取。"""
from __future__ import annotations

import base64
import logging
import time
import urllib.request
from collections.abc import Callable
from typing import Optional

from .qingguo_proxy import ProxyLease, QingguoProxyPool

_LOG = logging.getLogger(__name__)
Fetch = Callable[[str, Optional[str]], str]


def _fetch_via(url: str, proxy: Optional[str], auth: Optional[str] = None,
               timeout: float = 5.0) -> str:
    # httpx 支持把代理账密写在代理 URL 里（青果用 Basic 认证，实测可行）
    if proxy:
        try:
            import httpx

            try:
                with httpx.Client(proxy=proxy, timeout=timeout) as client:
                    response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:  # 统一转成 OSError，适配器按约定捕获
                raise OSError(str(exc)) from exc
        except ImportError:
            pass
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    opener = urllib.request.build_opener(handler)
    headers = {"User-Agent": "Mozilla/5.0"}
    if auth:
        headers["Proxy-Authorization"] = auth
    request = urllib.request.Request(url, headers=headers)
    return opener.open(request, timeout=timeout).read().decode("utf-8", "ignore")


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
        retries: int = 1,
        backoff: float = 0.5,
        max_rotations: int = 1,
    ) -> None:
        self._pool = pool
        auth = None
        self._proxy_cred = None
        if pool is not None and pool.key and pool.password:
            raw = f"{pool.key}:{pool.password}".encode()
            auth = "Basic " + base64.b64encode(raw).decode()
            self._proxy_cred = f"{pool.key}:{pool.password}"
        self._auth = auth
        self._fetch = fetch or (lambda url, proxy: _fetch_via(url, proxy, auth))
        self._retries = retries
        self._backoff = backoff
        self._max_rotations = max_rotations
        self._rotations = 0
        self._consecutive_failures = 0
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
        if lease and self._proxy_cred:
            proxy = f"http://{self._proxy_cred}@{lease.ip}:{lease.port}"
        else:
            proxy = f"http://{lease.ip}:{lease.port}" if lease else None

        for attempt in range(self._retries + 1):
            self.stats["requests"] += 1
            if self.stats["requests"] % 20 == 0:
                _LOG.info("proxy stats requests=%d rotations=%d failures=%d",
                          self.stats["requests"], self.stats["rotations"], self.stats["failures"])
            try:
                text = self._fetch(url, proxy)
                self._consecutive_failures = 0
                return text
            except (OSError, ValueError):
                if attempt < self._retries:
                    time.sleep(self._backoff * (2 ** attempt))
                    continue
                self._consecutive_failures += 1
                if (lease and self._pool and self._rotations < self._max_rotations
                        and self._consecutive_failures >= 2):
                    self._pool.report_bad(lease)
                    self.stats["rotations"] += 1
                    self._rotations += 1
                    try:
                        return self.get(url)  # 换 IP 后重试一次
                    finally:
                        self._rotations -= 1
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
