"""代理池与 HTTP 客户端测试：全部使用假取数，不消耗真实额度。"""
from __future__ import annotations

import contextlib
import time

from a_share_brief.infrastructure.proxy_client import ProxyHttpClient
from a_share_brief.infrastructure.qingguo_proxy import QingguoProxyPool


def test_lease_reused_within_ttl():
    calls = {"n": 0}

    def fake_extract(url: str) -> str:
        calls["n"] += 1
        return f"10.0.0.{calls['n']}:8080"

    pool = QingguoProxyPool(key="k", fetch=fake_extract)
    first = pool.acquire()
    second = pool.acquire()
    assert first.ip == second.ip == "10.0.0.1"
    assert calls["n"] == 1                      # 3 分钟内只消耗 1 个 IP


def test_expired_lease_rotates():
    pool = QingguoProxyPool(key="k", fetch=lambda url: "10.0.0.9:8080", ttl=0)
    pool.acquire()
    time.sleep(0.01)
    assert pool.acquire().ip == "10.0.0.9"


def test_bad_ip_is_replaced():
    pool = QingguoProxyPool(key="k", fetch=lambda url: "10.0.0.2:8080")
    lease = pool.acquire()
    pool.report_bad(lease)
    assert pool.acquire().ip == "10.0.0.2"      # 假取数仍返回同 IP，验证会重新提取


def test_missing_key_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("QG_KEY", raising=False)
    assert QingguoProxyPool().acquire() is None


def test_client_retries_then_fails(monkeypatch):
    attempts = {"n": 0}

    def boom(url: str, proxy: str | None) -> str:
        attempts["n"] += 1
        raise OSError("429")

    client = ProxyHttpClient(fetch=boom, retries=2, backoff=0)
    with contextlib.suppress(OSError):
        client.get("https://example.com/api")
    assert attempts["n"] == 3                   # 首次 + 2 次重试
    assert client.stats["failures"] == 1


def test_client_falls_back_to_scraper():
    def boom(url: str, proxy: str | None) -> str:
        raise OSError("501")

    client = ProxyHttpClient(fetch=boom, retries=0)
    assert client.get_or_scrape("https://api", lambda url: "web-fallback") == "web-fallback"
