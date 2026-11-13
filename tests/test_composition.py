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
