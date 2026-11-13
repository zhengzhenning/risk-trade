"""用例测试：异动端口注入后应写入股票聚合。"""
from datetime import date

from a_share_brief.application.usecases.build_snapshot import BuildSnapshot
from a_share_brief.domain.aggregates import AlertLevel, PoolEntry, StockAlert

DAY = date(2026, 11, 12)


class _Repo:
    def __init__(self):
        self.saved = []

    def save(self, briefing):
        self.saved.append(briefing)

    def load(self, day):
        return None


class _Pools:
    def month_top(self, n=10):
        return [PoolEntry(code="002086", name="东方海洋", rank=1, theme="东方系")]

    def d60_top(self, n=7):
        return []


class _Quotes:
    def snapshot(self, codes):
        return {}


class _Alerts:
    def unusual(self, codes, day=None):
        return {"002086": StockAlert(code="002086", day=DAY, level=AlertLevel.TRIGGERED)}


def test_snapshot_attaches_alert_from_port():
    repo = _Repo()
    briefing = BuildSnapshot(_Pools(), _Quotes(), repo, alerts=_Alerts())(DAY)

    assert briefing.stocks[0].base.code == "002086"
    assert briefing.stocks[0].alert is not None
    assert briefing.stocks[0].alert.level is AlertLevel.TRIGGERED
