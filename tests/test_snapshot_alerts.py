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


class _Indexes:
    def snapshot(self, codes, day=None):
        from a_share_brief.domain.aggregates import Exchange, Index, IndexBase, IndexQuote

        base = IndexBase(code="000001", name="上证指数", exchange=Exchange.SH)
        quote = IndexQuote(code="000001", day=DAY, ts="2026-11-12T15:00:00+08:00",
                           open=3665.0, high=3695.0, low=3660.0, close=3689.33,
                           prev_close=3680.0, change=9.33, change_pct=0.25)
        return {"000001": Index(base=base, quote=quote)}


def test_snapshot_attaches_indexes_from_port():
    briefing = BuildSnapshot(_Pools(), _Quotes(), _Repo(), indexes=_Indexes())(DAY)
    assert [index.base.code for index in briefing.indexes] == ["000001"]
    assert briefing.indexes[0].quote.close == 3689.33
