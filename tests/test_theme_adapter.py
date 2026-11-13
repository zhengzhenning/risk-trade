"""F10 题材适配器测试：注入假取数，不触网。"""
from a_share_brief.infrastructure.eastmoney_f10 import EastmoneyThemeAdapter

PAYLOAD = (
    '{"ssbk":[{"BOARD_NAME":"有色金属"},{"BOARD_NAME":"工业金属"},'
    '{"BOARD_NAME":"铝"},{"BOARD_NAME":"福建板块"},{"BOARD_NAME":"光伏概念"}]}'
)


def test_pick_most_specific_industry():
    adapter = EastmoneyThemeAdapter(fetch=lambda url: PAYLOAD)
    assert adapter.themes_of(["002578"]) == {"002578": ("铝",)}


def test_skip_region_and_concept_boards():
    payload = '{"ssbk":[{"BOARD_NAME":"福建板块"},{"BOARD_NAME":"光伏概念"}]}'
    adapter = EastmoneyThemeAdapter(fetch=lambda url: payload)
    assert adapter.themes_of(["002578"]) == {}


def test_fetch_failure_is_skipped():
    def boom(url):
        raise OSError("network")

    assert EastmoneyThemeAdapter(fetch=boom).themes_of(["002578"]) == {}
