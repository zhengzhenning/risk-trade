"""HTTP 接口测试：真实读写临时快照目录，不触网。"""
from datetime import date

import pytest

pytest.importorskip("fastapi", reason="需要 HTTP 依赖，见 make api-test")

from fastapi.testclient import TestClient  # noqa: E402

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
from a_share_brief.interfaces.api import create_app

DAY = date(2026, 11, 13)


@pytest.fixture
def client(tmp_path):
    repo = FileRepoAdapter(tmp_path)
    stock = Stock(
        base=StockBase(code="002578", name="闽发铝业", exchange=Exchange.SZ, board=Board.MAIN),
        quote=StockQuote(code="002578", day=DAY, ts="2026-11-13T15:00:00+08:00", open=6.0,
                         high=6.2, low=5.9, close=6.1, prev_close=6.0, change=0.1, pct=1.67),
        alert=StockAlert(code="002578", day=DAY, level=AlertLevel.NEAR, distance_pct=1.2),
    )
    ranking = PoolRanking(day=DAY, window=PoolWindow.MONTH,
                          entries=(PoolEntry(code="002578", name="闽发铝业", rank=1,
                                             window=PoolWindow.MONTH, range_pct=94.2),))
    index = Index(base=IndexBase(code="000001", name="上证指数", exchange=Exchange.SH),
                  quote=IndexQuote(code="000001", day=DAY, ts="2026-11-13T15:00:00+08:00",
                                   open=3665.0, high=3695.0, low=3660.0, close=3689.33,
                                   prev_close=3680.0, change=9.33, change_pct=0.25))
    repo.save(Briefing(day=DAY, indexes=(index,), rankings=(ranking,), stocks=(stock,)))
    return TestClient(create_app(tmp_path))


def test_health_and_history(client):
    assert client.get("/healthz").json()["days"] == 1
    assert client.get("/api/history").json()["days"] == ["2026-11-13"]


def test_briefing_returns_full_snapshot(client):
    payload = client.get("/api/briefing?date=2026-11-13").json()
    assert payload["day"] == "2026-11-13"
    assert payload["indexes"][0]["quote"]["close"] == 3689.33
    assert payload["stocks"][0]["alert"]["level"] == "NEAR"


def test_pool_window_and_errors(client):
    assert client.get("/api/pool/MONTH").json()["entries"][0]["rank"] == 1
    assert client.get("/api/pool/D60").status_code == 404
    assert client.get("/api/pool/BAD").status_code == 400
    assert client.get("/api/briefing?date=bad").status_code == 400


def test_alert_and_live_stream(client):
    alerts = client.get("/api/alert?codes=002578,600000").json()
    assert alerts["002578"]["level"] == "NEAR"

    response = client.get("/api/live?ticks=1&interval=0.01")
    assert response.status_code == 200
    assert "data:" in response.text


def test_pool_history_returns_matrix(tmp_path):
    from a_share_brief.domain.aggregates import PoolEntry, PoolRanking, PoolWindow

    repo = FileRepoAdapter(tmp_path)
    for day, name, code in (
        (date(2026, 11, 10), "闽发铝业", "002578"),
        (date(2026, 11, 11), "东方海洋", "002086"),
    ):
        ranking = PoolRanking(day=day, window=PoolWindow.MONTH,
                              entries=(PoolEntry(code=code, name=name, rank=1,
                                                 window=PoolWindow.MONTH),))
        repo.save(Briefing(day=day, rankings=(ranking,)))

    client = TestClient(create_app(tmp_path))
    payload = client.get("/api/pool/history?window=MONTH&days=6").json()

    assert payload["dates"] == ["2026-11-10", "2026-11-11"]
    assert payload["rows"][0]["cells"][0]["name"] == "闽发铝业"
    assert payload["rows"][0]["cells"][1]["is_new"] is True
    assert client.get("/api/pool/history?window=BAD").status_code == 400


def test_themes_endpoint(tmp_path):
    from a_share_brief.domain.aggregates import Theme, ThemeMember

    repo = FileRepoAdapter(tmp_path)
    theme = Theme(id="铝（有色）", name="铝（有色）", anchor_code="002578", anchor_name="闽发铝业",
                  rank=1, narrative="铝价主线",
                  members=(ThemeMember(code="002578", name="闽发铝业", is_anchor=True,
                                       rank_in_pool=1),))
    repo.save(Briefing(day=DAY, themes=(theme,)))
    client = TestClient(create_app(tmp_path))

    payload = client.get("/api/themes").json()
    assert payload["day"] == "2026-11-13"
    assert payload["themes"][0]["anchor"]["name"] == "闽发铝业"
    assert payload["themes"][0]["narrative"] == "铝价主线"


def test_stock_detail_includes_phases(tmp_path):
    from a_share_brief.domain.aggregates import Phase

    repo = FileRepoAdapter(tmp_path)
    stock = Stock(
        base=StockBase(code="002578", name="闽发铝业", exchange=Exchange.SZ, board=Board.MAIN),
        quote=StockQuote(code="002578", day=DAY, ts="2026-11-13T15:00:00+08:00", open=6.0,
                         high=6.2, low=5.9, close=6.1, prev_close=6.0, change=0.1, pct=1.67),
    )
    repo.save(Briefing(day=DAY, stocks=(stock,),
                       phases={"002578": (Phase(start="2026-10-26", end="2026-11-10", kind="start"),)}))
    client = TestClient(create_app(tmp_path))

    payload = client.get("/api/stock/002578").json()
    assert payload["stock"]["base"]["name"] == "闽发铝业"
    assert payload["phases"][0]["kind"] == "start"
    assert client.get("/api/stock/600000").status_code == 404
