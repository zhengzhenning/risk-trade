"""股池与指数适配器测试：注入假取数函数，不触网。"""
from datetime import date

import pytest

from a_share_brief.domain.aggregates import PoolWindow
from a_share_brief.infrastructure.eastmoney_index import EastmoneyIndexAdapter
from a_share_brief.infrastructure.eastmoney_pool import EastmoneyPoolAdapter

POOL_OK = {
    "code": "100",
    "data": {
        "result": {
            "columns": [
                {"key": "SECURITY_CODE", "title": "股票代码"},
                {"key": "SECURITY_NAME_ABBR", "title": "股票名称"},
                {"key": "RANGE_PCT", "title": "本月涨幅"},
                {"key": "CHANGE_RATE", "title": "涨跌幅"},
                {"key": "TURNOVERRATE", "title": "换手率"},
                {"key": "AUCTION", "title": "集合竞价涨跌幅"},
            ],
            "dataList": [
                {"SECURITY_CODE": "002086", "SECURITY_NAME_ABBR": "东方海洋",
                 "RANGE_PCT": "82.31", "CHANGE_RATE": "10.02", "TURNOVERRATE": "18.8", "AUCTION": "3.2"},
                {"SECURITY_CODE": "603366", "SECURITY_NAME_ABBR": "日出东方",
                 "RANGE_PCT": "67.30", "CHANGE_RATE": "4.10", "TURNOVERRATE": "9.2", "AUCTION": "-1.1"},
            ],
        }
    },
}

INDEX_OK = {
    "data": {"f43": 3689.33, "f44": 3695.0, "f45": 3660.0, "f46": 3665.0,
             "f47": 1.2e8, "f48": 3.1e11, "f58": "上证指数", "f60": 3680.0,
             "f169": 9.33, "f170": 0.25}
}


def test_pool_adapter_maps_columns_to_entries():
    adapter = EastmoneyPoolAdapter(post=lambda body: POOL_OK)
    entries = adapter.month_top(10)

    assert [e.code for e in entries] == ["002086", "603366"]
    assert entries[0].rank == 1
    assert entries[0].window is PoolWindow.MONTH
    assert entries[0].range_pct == 82.31
    assert entries[0].auction_pct == 3.2


def test_pool_adapter_empty_result_is_not_error():
    adapter = EastmoneyPoolAdapter(post=lambda body: {"code": "201"})
    assert adapter.d60_top(7) == []


def test_pool_adapter_raises_on_api_error():
    adapter = EastmoneyPoolAdapter(post=lambda body: {"code": "500", "msg": "busy"})
    with pytest.raises(RuntimeError, match="500"):
        adapter.month_top(10)


def test_index_adapter_maps_quote():
    adapter = EastmoneyIndexAdapter(fetch=lambda url: __import__("json").dumps(INDEX_OK))
    indexes = adapter.snapshot(["000001"], day=date(2026, 11, 12))

    quote = indexes["000001"].quote
    assert indexes["000001"].base.name == "上证指数"
    assert quote.close == 3689.33
    assert quote.change_pct == 0.25
    assert quote.amount == 3.1e11
