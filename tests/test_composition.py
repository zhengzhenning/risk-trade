"""组合根测试：装配结果满足端口契约。"""
from a_share_brief.application.ports import AlertPort, IndexQuotePort, KLinePort, QuotePort
from a_share_brief.application.usecases.build_snapshot import BuildSnapshot
from a_share_brief.application.usecases.build_view import BuildView
from a_share_brief.interfaces.composition import (
    build_snapshot_usecase,
    build_view_usecase,
    kline_port,
    quotes_port,
)


def _methods(port) -> list[str]:
    return [name for name in dir(port) if not name.startswith("_")]


def test_quotes_port_is_composed():
    port = quotes_port()
    assert "snapshot" in _methods(port)
    assert isinstance(port, QuotePort)


def test_kline_and_index_and_alert_ports_available():
    assert isinstance(kline_port(), KLinePort)
    from a_share_brief.interfaces.composition import EastmoneyAlertAdapter, EastmoneyIndexAdapter

    assert isinstance(EastmoneyAlertAdapter(), AlertPort)
    assert isinstance(EastmoneyIndexAdapter(), IndexQuotePort)


def test_usecases_are_wired(tmp_path):
    assert isinstance(build_snapshot_usecase(tmp_path), BuildSnapshot)
    assert isinstance(build_view_usecase(tmp_path), BuildView)


def test_proxy_clients_share_one_pool(monkeypatch):
    import threading

    from a_share_brief.infrastructure.qingguo_proxy import QingguoProxyPool
    from a_share_brief.interfaces import composition

    pool = QingguoProxyPool(key="k", fetch=lambda url: "10.0.0.1:8080")
    monkeypatch.setattr(composition, "_proxy_pool", lambda: pool)

    first = composition.proxy_client()
    assert first is composition.proxy_client()      # 同线程复用同一客户端
    assert first.pool is pool                       # 共用进程级租约池

    other = []
    thread = threading.Thread(target=lambda: other.append(composition.proxy_client()))
    thread.start()
    thread.join()
    assert other[0] is not first                    # 客户端线程本地
    assert other[0].pool is pool                    # 租约池仍共用
