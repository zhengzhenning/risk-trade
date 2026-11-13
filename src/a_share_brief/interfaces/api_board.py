"""看板页路由：静态模板 + 当日快照数据，60 秒自检版本号。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.tencent_kline import TencentKLineAdapter
from .board_data import latest_archive, render
from .board_vp import build_vp

_POLL = """
<script>
(function () {
  window.__BRIEF_REV = %d;
  setInterval(async function () {
    try {
      var res = await fetch("/api/briefing", { headers: { "Accept": "application/json" } });
      if (!res.ok) return;
      var data = await res.json();
      if (data.revision !== window.__BRIEF_REV) location.reload();
    } catch (error) { /* 网络抖动保持当前页 */ }
  }, 60000);
})();
</script>
"""


def register_board(app: FastAPI, archives: Path, store: Path) -> None:
    """注册看板页。

    Args:
        app: FastAPI 实例。
        archives: 归档目录（模板来源）。
        store: 快照目录。
    """

    @app.get("/board", response_class=HTMLResponse)
    def board() -> str:
        base = latest_archive(archives)
        if base is None:
            raise HTTPException(status_code=404, detail="暂无归档看板")
        repo = FileRepoAdapter(store)
        days = sorted(repo.root.glob("briefing-*.json"))
        if not days:
            raise HTTPException(status_code=404, detail="暂无快照")
        day = days[-1].stem.removeprefix("briefing-")
        snapshot = repo.load(__import__("datetime").date.fromisoformat(day))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="快照读取失败")
        klines = TencentKLineAdapter()
        vp = build_vp(snapshot, day, klines)
        # 指数卡小 K 线暂用归档序列：替换后模板 kline 渲染报错，回退以保稳定
        html = render(base.read_text(encoding="utf-8"), snapshot, day, vp)
        return html.replace("</body>", (_POLL % snapshot.revision) + "</body>", 1)
