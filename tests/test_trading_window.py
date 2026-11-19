"""采集时段测试：午休与收盘都不再消耗代理 IP。"""
from datetime import datetime

from a_share_brief.interfaces.live_loop import _in_lunch, _trading
from a_share_brief.interfaces.tasks import _trading_now


def _at(hour: int, minute: int, day: int = 19) -> datetime:
    return datetime(2026, 11, day, hour, minute)      # 2026-11-19 周四


def test_tasks_skip_lunch_break():
    assert _trading_now(_at(10, 0)) is True
    assert _trading_now(_at(12, 0)) is False
    assert _trading_now(_at(13, 30)) is True
    assert _trading_now(_at(15, 30)) is False


def test_tasks_skip_weekend():
    assert _trading_now(datetime(2026, 11, 21, 10, 0)) is False   # 周六


def test_live_loop_skips_lunch_break():
    assert _trading(_at(11, 29)) is True
    assert _trading(_at(11, 31)) is False
    assert _trading(_at(13, 1)) is True
    assert _in_lunch(_at(12, 0)) is True
