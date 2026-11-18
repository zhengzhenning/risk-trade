"""看板页路由：静态模板 + 当日快照数据，60 秒自检版本号。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.sections import load as load_section
from .board_data import latest_archive, render
from .board_index import build_index_bars
from .board_vp import build_vp
from .composition import kline_port

_FLASH = """
<style>
  @keyframes bf-up { 0% { background: rgba(214,52,80,.30); } 100% { background: transparent; } }
  @keyframes bf-down { 0% { background: rgba(14,150,104,.30); } 100% { background: transparent; } }
  .bf-up { animation: bf-up .9s ease-out; }
  .bf-down { animation: bf-down .9s ease-out; }
  @media (prefers-reduced-motion: reduce) { .bf-up, .bf-down { animation: none; } }
</style>
<script>
(function () {
  var KEY = "brief:flash:v1";
  var prev = {};
  try { prev = JSON.parse(sessionStorage.getItem(KEY) || "{}"); } catch (e) { prev = {}; }
  var now = {};
  function track(el, key) {
    if (!el) return;
    var text = (el.textContent || "").trim();
    if (!/%$/.test(text)) return;
    now[key] = text;
    var old = prev[key];
    if (!old || old === text) return;
    var up = parseFloat(text) >= parseFloat(old);
    el.classList.add(up ? "bf-up" : "bf-down");
  }
  document.querySelectorAll("[data-live-pct]").forEach(function (el) {
    track(el, "pct:" + el.getAttribute("data-live-pct"));
  });
  document.querySelectorAll("[data-live-big]").forEach(function (el) {
    track(el, "big:" + el.getAttribute("data-live-big"));
  });
  document.querySelectorAll(".mx-today .mx-cell[data-code] .mx-pct").forEach(function (el) {
    track(el, "mx:" + el.closest(".mx-cell").getAttribute("data-code"));
  });
  try { sessionStorage.setItem(KEY, JSON.stringify(now)); } catch (e) { /* 隐私模式忽略 */ }
})();
</script>
"""

_POLL = """
<script>
(function () {
  window.__BRIEF_REV = %d;
  var lastTouch = Date.now();
  ["click", "keydown", "wheel", "touchstart"].forEach(function (name) {
    document.addEventListener(name, function () { lastTouch = Date.now(); }, true);
  });
  setInterval(async function () {
    // 用户刚操作过（如切换个股）时不打断，等下一次静默再判断
    if (Date.now() - lastTouch < 90000) return;
    try {
      var res = await fetch("/api/briefing", { headers: { "Accept": "application/json" } });
      if (!res.ok) return;
      var data = await res.json();
      if (data.revision !== window.__BRIEF_REV) location.reload();
    } catch (error) { /* 网络抖动保持当前页 */ }
  }, 15000);
})();
</script>
"""


def _overlay(store: Path) -> tuple[dict[str, float], dict[str, tuple[float, float]]]:
    """读取分片里的最新行情与指数。

    Args:
        store: 快照目录，分片位于同级 sections 目录。

    Returns:
        (代码→涨跌幅, 指数名→(收盘, 涨跌幅))。
    """
    root = store.parent / "sections"
    quotes: dict[str, float] = {}
    indexes: dict[str, tuple[float, float]] = {}
    if (section := load_section(root, "quotes")) is not None:
        quotes = {row["code"]: row["pct"] for row in section.get("rows") or []
                  if row.get("pct") is not None}
    if (section := load_section(root, "index")) is not None:
        indexes = {row["name"]: (row["close"], row["pct"]) for row in section.get("rows") or []
                   if row.get("close") is not None and row.get("pct") is not None}
    return quotes, indexes


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
        klines = kline_port()
        vp = build_vp(snapshot, day, klines)
        index_bars = build_index_bars(day, snapshot.revision, klines)
        quotes, indexes = _overlay(store)
        html = render(base.read_text(encoding="utf-8"), snapshot, day, vp, index_bars,
                      quotes, indexes)
        return html.replace("</body>", _FLASH + (_POLL % snapshot.revision) + "</body>", 1)
