"""青果代理池：进程内共享一个租约，120 秒复用，失败才换 IP。"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

_LOG = logging.getLogger(__name__)

_EXTRACT = "https://share.proxy.qg.net/get?key={key}&password={password}&num=1"
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
    ttl: float = 120.0
    failures: int = 0

    def alive(self, now: float | None = None, ttl: float = 170.0) -> bool:
        """租约是否仍可复用（未超过 ``ttl``）。

        Args:
            now: 当前时间戳，缺省取系统时间。
            ttl: 复用上限（秒）。

        Returns:
            未过期返回 True。
        """
        return (now or time.time()) - self.acquired_at < ttl


@dataclass
class QingguoProxyPool:
    """实现 ProxyPort：进程内只保留一个租约，多线程共用一个出口。

    Args:
        key: 接口密钥，缺省读环境变量 ``QG_KEY``，禁止写进代码或日志。
        fetch: HTTP 取数函数，便于测试。
        ttl: 租约时长，默认 120 秒（小于 IP 存活 180 秒）。
        bad_ttl: 坏 IP 冷却时长，默认 600 秒，避免台账无限增长。
    """

    key: Optional[str] = None
    password: Optional[str] = None
    fetch: Fetch | None = None
    ttl: float = 120.0
    bad_ttl: float = 600.0
    extracts: int = 0
    _lease: Optional[ProxyLease] = None
    _bad: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self) -> Optional[ProxyLease]:
        """获取可复用租约；ttl 内复用，未配置密钥时返回 None（直连）。

        Returns:
            可用租约或 None。
        """
        with self._lock:
            now = time.time()
            for ip in [ip for ip, until in self._bad.items() if until <= now]:
                self._bad.pop(ip, None)
            if (self._lease is not None and self._lease.alive(now, self.ttl)
                    and self._lease.ip not in self._bad):
                return self._lease
            return self._extract(now)

    def _extract(self, now: float) -> Optional[ProxyLease]:
        """向青果提取一个新 IP（调用方需持有锁）。

        Args:
            now: 提取时刻。

        Returns:
            新租约；密钥缺失、请求失败或返回异常时为 None。
        """
        key = self.key or os.environ.get("QG_KEY", "")
        if not key:
            return None
        password = self.password or os.environ.get("QG_PASSWORD", "")
        try:
            raw = (self.fetch or _default_fetch)(_EXTRACT.format(
                key=urllib.parse.quote(key, safe=""),
                password=urllib.parse.quote(password, safe="")))
        except (OSError, ValueError):
            return None
        server = self._server_of(raw)
        ip, _, port = server.strip().partition(":")
        if not ip or not port.isdigit():
            return None
        self._lease = ProxyLease(ip=ip, port=int(port), acquired_at=now, ttl=self.ttl)
        self.extracts += 1
        _LOG.info("proxy lease acquired ip=%s ttl=%.0fs extracts=%d",
                  ip, self.ttl, self.extracts)
        return self._lease

    @staticmethod
    def _server_of(raw: str) -> str:
        """从提取结果中取出 ``ip:port``，兼容纯文本与官方 JSON。

        Args:
            raw: 接口原始返回。

        Returns:
            ``ip:port``；非成功响应返回空串。
        """
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if payload.get("code") not in (None, "SUCCESS"):
            return ""
        rows = payload.get("data") or []
        return str((rows[0] if rows else {}).get("server") or "")

    def report_bad(self, lease: Optional[ProxyLease]) -> None:
        """标记坏 IP：冷却期内不再使用，下一次 acquire 换新租约。

        Args:
            lease: 待标记的租约，None 时忽略。
        """
        if lease is None:
            return
        with self._lock:
            self._bad[lease.ip] = time.time() + self.bad_ttl
            if self._lease is not None and self._lease.ip == lease.ip:
                self._lease = None
