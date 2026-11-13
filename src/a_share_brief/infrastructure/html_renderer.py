"""渲染适配器：把快照渲染成 HTML（P2 接入正式模板，当前为最小可用视图）。"""
from __future__ import annotations

from ..domain.aggregates import Briefing


class HtmlRendererAdapter:
    """最小渲染器：指数、股池前七、个股行情。

    渲染只读聚合，不做业务计算。
    """

    def render(self, briefing: Briefing) -> str:
        """渲染快照。

        Args:
            briefing: 当日快照。

        Returns:
            HTML 字符串。
        """
        index_rows = "".join(
            f"<li>{item.base.name} {_num(item.quote.close if item.quote else None)} "
            f"{_pct(item.quote.change_pct if item.quote else None)}</li>"
            for item in briefing.indexes
        )
        pool_rows = ""
        for ranking in briefing.rankings:
            rows = "".join(
                f"<tr><td>{entry.rank}</td><td>{entry.name}</td>"
                f"<td>{_pct(entry.range_pct)}</td><td>{_pct(entry.pct)}</td></tr>"
                for entry in ranking.top(7)
            )
            pool_rows += (
                f"<h2>{ranking.window.value}</h2>"
                f"<table><tr><th>#</th><th>名称</th><th>区间</th><th>当日</th></tr>{rows}</table>"
            )
        stock_rows = "".join(
            f"<tr><td>{item.base.name}</td><td>{_pct(item.quote.pct if item.quote else None)}</td>"
            f"<td>{(item.alert.level.value if item.alert else '—')}</td></tr>"
            for item in briefing.stocks[:20]
        )
        return (
            "<!doctype html><meta charset='utf-8'>"
            f"<title>{briefing.day} 看板</title>"
            f"<h1>{briefing.day} · rev {briefing.revision}</h1>"
            f"<ul>{index_rows}</ul>{pool_rows}"
            f"<table><tr><th>个股</th><th>涨跌</th><th>异动</th></tr>{stock_rows}</table>"
        )


def _num(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "—"


def _pct(value: float | None) -> str:
    return f"{value:+.2f}%" if value is not None else "—"
