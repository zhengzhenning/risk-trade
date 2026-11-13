"""渲染适配器：把 Briefing 渲染成 HTML（占位实现，后续接 dashboard-template）。"""
from __future__ import annotations

from ..domain.aggregates import Briefing


class HtmlRendererAdapter:
    def render(self, briefing: Briefing) -> str:
        rows = "".join(
            f"<tr><td>{s.rank or '-'}</td><td>{s.name}</td><td>{s.pct:+.2f}%</td></tr>"
            for s in briefing.stocks
        )
        return (
            f"<!doctype html><meta charset='utf-8'><title>{briefing.day}</title>"
            f"<h1>{briefing.day} · rev {briefing.revision}</h1>"
            f"<table><tr><th>#</th><th>名称</th><th>涨跌</th></tr>{rows}</table>"
        )
