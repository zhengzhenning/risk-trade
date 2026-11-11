#!/usr/bin/env python3
"""生成通用入口：archives/live.html（最新看板副本）+ archives/history.html（历史索引）

用法：
  python3 scripts/build_index.py --dir archives
  # 之后访问 http://127.0.0.1:8777/         → 实时看板（最新交易日）
  #        http://127.0.0.1:8777/history    → 历史看板索引
  #        http://127.0.0.1:8777/d/2026-11-10 → 指定日期看板

每次全量重建/推送后执行一次即可；live.html 为最新 archive 的副本（保留实时层轮询能力）。
"""
import argparse, glob, os, re, shutil

TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>A股题材发酵看板 · 历史索引</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{{--ink:#0F172A;--sub:#64748B;--faint:#68758C;--line:#E2E8F0;--bg:#F8FAFC;--acc:#8f6708}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Inter","PingFang SC",-apple-system,sans-serif}}
  .wrap{{max-width:960px;margin:0 auto;padding:32px 24px 80px}}
  h1{{font-size:28px;margin:0 0 6px}}
  .sub{{color:var(--sub);font-size:13px;margin-bottom:22px}}
  .live{{display:inline-flex;align-items:center;gap:8px;margin-bottom:18px;padding:9px 14px;border-radius:8px;
    background:#fff;border:1px solid var(--line);color:var(--ink);text-decoration:none;font-weight:600}}
  .live:hover{{border-color:var(--acc)}}
  .dot{{width:8px;height:8px;border-radius:50%;background:#4ade80;box-shadow:0 0 0 0 rgba(74,222,128,.6)}}
  table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}}
  th,td{{padding:10px 14px;text-align:left;font-size:13px;border-bottom:1px solid var(--line)}}
  th{{background:#F1F5F9;color:var(--sub);font-weight:600;font-size:12px}}
  tr:last-child td{{border-bottom:none}}
  td.num{{font-variant-numeric:tabular-nums}}
  a{{color:#3b66d4;text-decoration:none}}a:hover{{text-decoration:underline}}
  .tag{{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600;background:#eef2f7;color:var(--sub)}}
  .tag.live{{background:#dcfce7;color:#166534}}
</style></head>
<body><div class="wrap">
<h1>A股题材发酵看板</h1>
<div class="sub">实时与历史统一入口 · 数据源东方财富 · 生成 {stamp}</div>
<a class="live" href="/"><span class="dot"></span>打开实时看板（{latest}）</a>
<table><thead><tr><th>交易日</th><th>快照</th><th>大小</th><th>操作</th></tr></thead><tbody>
{rows}
</tbody></table></div></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="archives")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)
    files = sorted(glob.glob(os.path.join(root, "market-briefing-*.html")), reverse=True)
    if not files:
        raise SystemExit("未找到 market-briefing-*.html")
    live_src = files[0]
    live_date = re.search(r"market-briefing-(\d{4}-\d{2}-\d{2})", os.path.basename(live_src)).group(1)
    live_html = open(live_src, encoding="utf-8").read()
    live_html = re.sub(r"<title>[^<]*</title>",
                       "<title>A股题材发酵看板 · %s（实时）</title>" % live_date, live_html, count=1)
    open(os.path.join(root, "live.html"), "w", encoding="utf-8").write(live_html)
    rows = []
    for i, f in enumerate(files):
        date = re.search(r"market-briefing-(\d{4}-\d{2}-\d{2})", os.path.basename(f)).group(1)
        html = open(f, encoding="utf-8", errors="ignore").read(200000)
        m = re.search(r"快照\s*([0-9:]{4,5})", html)
        snap = m.group(1) if m else "—"
        size = "%.0f KB" % (os.path.getsize(f) / 1024)
        tag = '<span class="tag live">实时</span>' if i == 0 else '<span class="tag">归档</span>'
        rows.append('<tr><td class="num"><b>%s</b> %s</td><td class="num">%s</td><td class="num">%s</td>'
                    '<td><a href="/d/%s">打开</a></td></tr>' % (date, tag, snap, size, date))
    stamp = os.path.basename(live_src).replace("market-briefing-", "").replace(".html", "")
    html = TPL.format(stamp=stamp, latest=stamp, rows="\n".join(rows))
    open(os.path.join(root, "history.html"), "w", encoding="utf-8").write(html)
    print("[OK] live.html ← %s" % os.path.basename(live_src))
    print("[OK] history.html（%d 个交易日）" % len(files))


if __name__ == "__main__":
    main()
