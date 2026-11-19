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


def test_repeated_requests_consume_one_ip():
    calls = {"n": 0}

    def fake_extract(url: str) -> str:
        calls["n"] += 1
        return f"10.0.0.{calls['n']}:8080"

    pool = QingguoProxyPool(key="k", fetch=fake_extract)
    client = ProxyHttpClient(pool=pool, fetch=lambda url, proxy: "ok", retries=0)
    for _ in range(10):
        assert client.get("https://example.com/api") == "ok"
    assert pool.extracts == 1                   # 10 次请求只提取 1 个 IP
    assert calls["n"] == 1


def test_rotation_needs_two_consecutive_failures():
    calls = {"n": 0}

    def fake_extract(url: str) -> str:
        calls["n"] += 1
        return f"10.0.0.{calls['n']}:8080"

    def boom(url: str, proxy: str | None) -> str:
        raise OSError("429")

    pool = QingguoProxyPool(key="k", fetch=fake_extract)
    client = ProxyHttpClient(pool=pool, fetch=boom, retries=0, backoff=0, rotate_after=2)

    with contextlib.suppress(OSError):
        client.get("https://example.com/api")   # 第 1 次失败：不换 IP
    assert pool.extracts == 1

    with contextlib.suppress(OSError):
        client.get("https://example.com/api")   # 连续第 2 次失败：才换 1 个 IP
    assert pool.extracts == 2
    assert client.stats["rotations"] == 1


def test_bad_ip_expires_after_cooldown():
    calls = {"n": 0}

    def fake_extract(url: str) -> str:
        calls["n"] += 1
        return "10.0.0.2:8080"

    pool = QingguoProxyPool(key="k", fetch=fake_extract, bad_ttl=0)
    pool.report_bad(pool.acquire())
    assert pool.acquire().ip == "10.0.0.2"
    assert calls["n"] == 2                      # 冷却期 0 秒，允许重新提取


def test_concurrent_requests_share_one_lease():
    import threading

    calls = {"n": 0}

    def fake_extract(url: str) -> str:
        calls["n"] += 1
        return f"10.0.0.{calls['n']}:8080"

    pool = QingguoProxyPool(key="k", fetch=fake_extract)
    clients = [ProxyHttpClient(pool=pool, fetch=lambda url, proxy: "ok", retries=0)
               for _ in range(8)]

    def run(client: ProxyHttpClient) -> None:
        for _ in range(20):
            client.get("https://example.com/api")

    threads = [threading.Thread(target=run, args=(client,)) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert pool.extracts == 1                   # 8 线程 160 次请求仍只 1 个 IP
