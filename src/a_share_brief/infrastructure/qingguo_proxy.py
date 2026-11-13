"""青果代理池：3 分钟租约内复用同一出口，失败才换 IP。"""
from __future__ import annotations

import os
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

_EXTRACT = "https://proxy.qg.net/extract?key={key}&num=1&format=txt"
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(request, timeout=10).read().decode("utf-8", "ignore")


@dataclass
class ProxyLease:
    """一次 IP 租约。"""

    ip: str
    port: int
    acquired_at: float
    ttl: float = 170.0
    failures: int = 0

    def alive(self, now: float | None = None, ttl: float = 170.0) -> bool:
        """租约是否仍可复用。"""
        return (now or time.time()) - self.acquired_at < ttl


@dataclass
class QingguoProxyPool:
    """实现 ProxyPort：同一进程内复用租约。

    Args:
        key: 接口密钥，缺省读环境变量 ``QG_KEY``，禁止写进代码或日志。
        fetch: HTTP 取数函数，便于测试。
        ttl: 租约时长，默认 170 秒（小于 IP 存活 180 秒）。
    """

    key: Optional[str] = None
    fetch: Fetch | None = None
    ttl: float = 170.0
    _lease: Optional[ProxyLease] = None
    _bad: set[str] = field(default_factory=set)

    def _key(self) -> str:
        value = self.key or os.environ.get("QG_KEY", "")
        if not value:
            raise RuntimeError("缺少 QG_KEY 环境变量")
        return value

    def acquire(self) -> Optional[ProxyLease]:
        """获取可复用租约；未配置密钥时返回 None（直连）。

        Returns:
            可用租约或 None。
        """
        now = time.time()
        if self._lease and self._lease.alive(now, self.ttl) and self._lease.ip not in self._bad:
            return self._lease
        try:
            key = self._key()
        except RuntimeError:
            return None
        try:
            raw = (self.fetch or _default_fetch)(_EXTRACT.format(key=urllib.parse.quote(key)))
        except (OSError, ValueError):
            return None
        ip, _, port = raw.strip().partition(":")
        if not ip or not port.isdigit():
            return None
        self._lease = ProxyLease(ip=ip, port=int(port), acquired_at=now, ttl=self.ttl)
        return self._lease

    def report_bad(self, lease: Optional[ProxyLease]) -> None:
        """标记坏 IP，下一次 acquire 会换新租约。"""
        if lease is None:
            return
        self._bad.add(lease.ip)
        self._lease = None
