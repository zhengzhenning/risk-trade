"""快照仓库测试：写入后可完整读回，不丢类型。"""
from datetime import date

from a_share_brief.domain.aggregates import (
    AlertLevel,
    Board,
    Briefing,
    Exchange,
    Index,
    IndexBase,
    IndexQuote,
    PoolEntry,
    PoolRanking,
    PoolWindow,
    Stock,
    StockAlert,
    StockBase,
    StockQuote,
)
from a_share_brief.infrastructure.file_repo import FileRepoAdapter

DAY = date(2026, 11, 13)


def _briefing(revision: int = 1) -> Briefing:
    stock = Stock(
        base=StockBase(code="002578", name="闽发铝业", exchange=Exchange.SZ, board=Board.MAIN),
        quote=StockQuote(code="002578", day=DAY, ts="2026-11-13T15:00:00+08:00", open=6.0,
                         high=6.2, low=5.9, close=6.1, prev_close=6.0, change=0.1, pct=1.67,
                         turnover=12.3),
        alert=StockAlert(code="002578", day=DAY, level=AlertLevel.NEAR, distance_pct=1.2,
                         triggered_day=date(2026, 11, 9), monitor_end=date(2026, 11, 23)),
    )
    ranking = PoolRanking(
        day=DAY,
        window=PoolWindow.MONTH,
        entries=(PoolEntry(code="002578", name="闽发铝业", rank=1, window=PoolWindow.MONTH,
                           range_pct=94.2),),
    )
    index = Index(
        base=IndexBase(code="000001", name="上证指数", exchange=Exchange.SH),
        quote=IndexQuote(code="000001", day=DAY, ts="2026-11-13T15:00:00+08:00", open=3665.0,
                         high=3695.0, low=3660.0, close=3689.33, prev_close=3680.0,
                         change=9.33, change_pct=0.25),
    )
    return Briefing(day=DAY, revision=revision, indexes=(index,), rankings=(ranking,),
                    stocks=(stock,))


def test_snapshot_round_trip_keeps_types(tmp_path):
    repo = FileRepoAdapter(tmp_path)
    repo.save(_briefing())
    loaded = repo.load(DAY)

    assert loaded is not None
    assert loaded.revision == 1
    assert loaded.stocks[0].base.exchange is Exchange.SZ
    assert loaded.stocks[0].base.board is Board.MAIN
    assert loaded.stocks[0].alert.level is AlertLevel.NEAR
    assert loaded.stocks[0].alert.triggered_day == date(2026, 11, 9)
    assert loaded.rankings[0].window is PoolWindow.MONTH
    assert loaded.indexes[0].quote.close == 3689.33


def test_missing_day_returns_none(tmp_path):
    assert FileRepoAdapter(tmp_path).load(date(2026, 1, 1)) is None
