"""适配器测试：注入假取数函数，不触网。"""
from datetime import date

from a_share_brief.domain.aggregates import AlertLevel
from a_share_brief.domain.services.trading_calendar import trading_days_after
from a_share_brief.infrastructure.eastmoney_alert import EastmoneyAlertAdapter
from a_share_brief.infrastructure.tencent_kline import TencentKLineAdapter, symbol_of

PREDICT = (
    'cb({"data":[{"c":"002578","n":"闽发铝业","x":"90.6","d":"9","t":"5.66","a":"0.99","o":0},'
    '{"c":"002086","n":"东方海洋","x":"40.1","d":"9","t":"3.20","a":"10.02","o":0}]})'
)
RECORD = (
    '{"result":{"data":[{"SECURITY_CODE":"002086","SECURITY_NAME_ABBR":"东方海洋",'
    '"TRADE_DATE":"2026-11-09 00:00:00","MAX_DAYS":"9","IS_HAPPEN":"1",'
    '"UNUSUAL_TYPE":"连续十个交易日内收盘价格跌幅偏离值累计达到 +100%"}]}}'
)


def _fetch(url: str) -> str:
    return PREDICT if "price-anomaly" in url else RECORD


def test_alert_adapter_maps_levels_and_monitor_end():
    adapter = EastmoneyAlertAdapter(fetch=_fetch)
    alerts = adapter.unusual(["002578", "002086"], day=date(2026, 11, 12))

    assert alerts["002578"].level is AlertLevel.WATCH         # 距触发 4.67%，≤5%
    assert alerts["002578"].distance_pct == 4.67

    triggered = alerts["002086"]
    assert triggered.level is AlertLevel.TRIGGERED
    assert triggered.triggered_day == date(2026, 11, 9)
    assert triggered.monitor_end == trading_days_after(date(2026, 11, 9), 10)
    assert "100%" in triggered.rule


def test_alert_adapter_ignores_codes_outside_filter():
    adapter = EastmoneyAlertAdapter(fetch=_fetch)
    assert adapter.unusual(["600000"], day=date(2026, 11, 12)) == {}


def test_kline_adapter_parses_qfq_rows():
    payload = (
        '{"data":{"sz002578":{"qfqday":['
        '["2026-11-11","6.00","6.09","6.20","5.90","120000"],'
        '["2026-11-12","6.05","6.18","6.25","6.00","98000"]]}}}'
    )
    adapter = TencentKLineAdapter(fetch=lambda url: payload)
    bars = adapter.daily("002578", 2)

    assert [bar.day for bar in bars] == ["2026-11-11", "2026-11-12"]
    assert bars[-1].close == 6.18
    assert bars[-1].volume == 98000


def test_symbol_prefix_by_exchange():
    assert symbol_of("600327") == "sh600327"
    assert symbol_of("002578") == "sz002578"
