"""内核测试：只用 Fake 适配器，不触网、不落盘。"""
from datetime import date

import pytest

from a_share_brief.application.usecases.build_snapshot import BuildSnapshot
from a_share_brief.application.usecases.build_view import BuildView
from a_share_brief.domain.aggregates import (
    AlertLevel,
    Board,
    Exchange,
    Index,
    IndexBase,
    IndexQuote,
    LimitState,
    PoolEntry,
    PoolRanking,
    PoolWindow,
    Stock,
    StockAlert,
    StockBase,
    StockQuote,
    StockTheme,
)
from a_share_brief.domain.services.pool import diff, matrix
from a_share_brief.domain.services.theme_cluster import cluster_themes
from a_share_brief.domain.services.theme_switch import (
    ThemeConflict,
    active_theme,
    detect_switches,
    validate_segments,
)

DAY = date(2026, 11, 12)


class FakeRepo:
    def __init__(self):
        self.data = {}

    def save(self, briefing):
        self.data[briefing.day] = briefing

    def load(self, day):
        return self.data.get(day)


class FakePools:
    def month_top(self, n=10):
        return [PoolEntry(code="002578", name="闽发铝业", rank=1, pct=1.2, theme="铝",
                          window=PoolWindow.MONTH)]

    def d60_top(self, n=7):
        return [PoolEntry(code="002086", name="东方海洋", rank=1, pct=10.0,
                          window=PoolWindow.D60)]


class FakeQuotes:
    def snapshot(self, codes):
        base = StockBase(code="002578", name="闽发铝业", exchange=Exchange.SZ, board=Board.MAIN)
        quote = StockQuote(code="002578", day=DAY, ts="2026-11-12T10:00:00+08:00",
                           open=6.0, high=6.2, low=5.9, close=6.1, prev_close=6.0,
                           change=0.1, pct=1.67, turnover=12.3)
        return {"002578": Stock(base=base, quote=quote)}


class _Renderer:
    def render(self, briefing):
        return f"{briefing.day} rev{briefing.revision}"


def test_build_snapshot_keeps_pool_order_and_bumps_revision():
    repo = FakeRepo()
    uc = BuildSnapshot(FakePools(), FakeQuotes(), repo)

    first = uc(DAY)
    assert first.revision == 1
    month = next(r for r in first.rankings if r.window is PoolWindow.MONTH)
    assert [e.code for e in month.top(7)] == ["002578"]
    assert [s.base.code for s in first.stocks] == ["002578", "002086"]
    assert {r.window for r in first.rankings} == {PoolWindow.MONTH, PoolWindow.D60}
    assert first.stocks[0].quote.turnover == 12.3      # 实时聚合覆盖
    assert first.stocks[1].quote is None               # 无行情时保留基础数据

    second = uc(DAY)
    assert second.revision == 2                         # 同日重跑 rev+1


def test_build_view_reads_from_repo_only():
    repo = FakeRepo()
    BuildSnapshot(FakePools(), FakeQuotes(), repo)(DAY)
    assert "rev1" in BuildView(repo, _Renderer())(DAY)


def test_build_view_missing_day_raises_snapshot_not_found():
    from a_share_brief.domain.errors import SnapshotNotFound

    with pytest.raises(SnapshotNotFound):
        BuildView(FakeRepo(), _Renderer())(date(2026, 1, 1))


def test_index_aggregate_composition():
    base = IndexBase(code="000001", name="上证指数", exchange=Exchange.SH)
    quote = IndexQuote(code="000001", day=DAY, ts="2026-11-12T10:00:00+08:00",
                       open=3680.0, high=3690.0, low=3670.0, close=3685.0,
                       prev_close=3682.0, change=3.0, change_pct=0.08,
                       volume=1.2e8, amount=3.1e11)
    index = Index(base=base, quote=quote)
    assert index.base.category.value == "BROAD"
    assert round(index.quote.change_pct, 2) == 0.08


def test_stock_aggregate_composition():
    base = StockBase(code="002086", name="东方海洋", exchange=Exchange.SZ, board=Board.MAIN,
                     themes=("水产养殖",))
    quote = StockQuote(code="002086", day=DAY, ts="2026-11-12T10:00:00+08:00",
                       open=6.0, high=6.6, low=5.9, close=6.6, prev_close=6.0,
                       change=0.6, pct=10.0, turnover=18.8, limit_state=LimitState.UP,
                       consecutive_limit_up=1)
    alert = StockAlert(code="002086", day=DAY, level=AlertLevel.FAR)
    stock = Stock(base=base, quote=quote, alert=alert)
    assert stock.base.themes == ("水产养殖",)
    assert stock.quote.limit_state is LimitState.UP
    assert stock.alert.level is AlertLevel.FAR


def _ranking(day, codes, window=PoolWindow.MONTH):
    entries = tuple(PoolEntry(code=c, name=c, rank=i + 1, window=window) for i, c in enumerate(codes))
    return PoolRanking(day=day, window=window, entries=entries)


def test_pool_diff_detects_added_removed_retained():
    prev = _ranking(date(2026, 11, 11), ["002578", "601599", "600327"])
    curr = _ranking(date(2026, 11, 12), ["002578", "002086", "600327"])

    d = diff(prev, curr)
    assert [e.code for e in d.added] == ["002086"]
    assert [e.code for e in d.removed] == ["601599"]
    assert [e.code for e in d.retained] == ["002578", "600327"]
    assert d.prev_day == date(2026, 11, 11)


def test_pool_diff_first_record_has_no_baseline():
    curr = _ranking(date(2026, 11, 12), ["002578"])
    d = diff(None, curr)
    assert d.prev_day is None
    assert d.removed == ()
    assert len(d.added) == 1


def test_pool_matrix_marks_new_entries():
    r1 = _ranking(date(2026, 11, 11), ["002578", "601599"])
    r2 = _ranking(date(2026, 11, 12), ["002578", "002086"])
    m = matrix([r2, r1], PoolWindow.MONTH, top_n=2, tail_n=2)

    assert m.dates == (date(2026, 11, 11), date(2026, 11, 12))
    assert m.today == date(2026, 11, 12)
    assert m.rows[0][0].code == "002578"
    assert m.rows[1][1].code == "002086"
    assert m.rows[1][1].is_new is True          # 名次 2 换人
    assert m.rows[0][1].is_new is False          # 名次 1 未变


def test_theme_switch_from_homophone_to_east_family():
    """东方海洋：谐音系 -> 东方系，切换事件应被识别。"""
    old = StockTheme(code="002086", theme_id="homophone", start_day=date(2026, 10, 21),
                     end_day=date(2026, 11, 9), evidence=("涨停池：洋/阳/洋 7 只",))
    new = StockTheme(code="002086", theme_id="east-family", start_day=date(2026, 11, 10),
                     switch_from="homophone", evidence=("涨停池：东方系 2 只",))

    assert active_theme((old, new), date(2026, 11, 12)).theme_id == "east-family"
    assert active_theme((old, new), date(2026, 11, 5)).theme_id == "homophone"

    switches = detect_switches((old, new))
    assert len(switches) == 1
    assert switches[0].from_theme == "homophone"
    assert switches[0].to_theme == "east-family"
    assert switches[0].day == date(2026, 11, 10)

    validate_segments((old, new))


def test_theme_overlap_raises_conflict():
    a = StockTheme(code="002086", theme_id="a", start_day=date(2026, 11, 1), end_day=date(2026, 11, 10))
    b = StockTheme(code="002086", theme_id="b", start_day=date(2026, 11, 10))
    with pytest.raises(ThemeConflict):
        active_theme((a, b), date(2026, 11, 10))
    with pytest.raises(ThemeConflict):
        validate_segments((a, b))


def test_cluster_themes_anchors_on_highest_rank_and_keeps_members():
    entries = (
        PoolEntry(code="002086", name="东方海洋", rank=1, theme="东方系", range_pct=82.3),
        PoolEntry(code="603366", name="日出东方", rank=2, theme="东方系", range_pct=67.3),
        PoolEntry(code="002578", name="闽发铝业", rank=3, theme="铝（有色）", range_pct=97.4),
    )
    themes = cluster_themes(entries, PoolWindow.MONTH, {"002086": "水产养殖"})

    assert [t.name for t in themes] == ["东方系", "铝（有色）"]      # 按锚点名次排序
    east = themes[0]
    assert east.anchor_code == "002086"
    assert east.rank == 1
    assert east.sector == "水产养殖"
    assert [m.name for m in east.members] == ["东方海洋", "日出东方"]
    assert east.members[0].is_anchor
    assert not east.members[1].is_anchor
    assert themes[1].members[0].is_anchor
    assert len(themes[1].members) == 1
