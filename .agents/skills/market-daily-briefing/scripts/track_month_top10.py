#!/usr/bin/env python3
"""月度前七：当月逐日快照回补 + 每日进出对比 + 全景矩阵视图模型

用法（在仓库根目录执行）：
  python3 skills/market-daily-briefing/scripts/track_month_top10.py \
      --pool <工作目录>/pool_月度前七.json [--date 2026-10-15] --out <工作目录>

职责：
1. 当日快照：从 --pool（第 3 步"本月涨幅前七"结果）规整入历史库（同日重跑覆盖当日行）。
2. 当月回补：对当月历史库缺失的交易日，用区间措辞逐日查询补齐
   （"YYYY.MM.01至YYYY.MM.DD区间涨跌幅前七；剔除…"）。接口会把区间自动收敛到实际交易日，
    从 INTERVAL_CHG{起|止|N|天} 原始键读有效截止日；法定节假日查询会收敛到前一交易日，
    已有快照则跳过。**回补查询不带竞价子句**——集合竞价列对历史区间返回的是最新交易日
    竞价值（实测 JHJJZDF{今日}），不能当历史当日值，回补快照 auction=null。
3. 产出 top10_changes.json：
   added/removed/retained（vs 最近一个不同交易日的前七子集，removed 带 prev_* 昨日字段）
   + matrix（全景矩阵）：dates=当月快照日升序、labels=MMDD+星期、
     rankRows=[{rank:1..7, cells:{日期:{code,name,month_pct}}}]、
     removed=[{code,name,prev_rank,cells:{日期:{rank,month_pct}},note}]。
   题材（themes）不在脚本产出，由模型在第 4 步按 F10 回填到看板 POOLCHG。

历史库：archives/pool-history/month-top10.jsonl（文件名沿用，不改），每行一个交易日快照：
  {date, latestDate, fetched_at, stocks:[{rank, code, name, month_pct, today_pct, auction}]}
  只存接口原始结果，禁止手工补写。限频：回补查询间隔 ≥1.2s，只查缺失日期，禁止重复刷。
  口径兼容：2026-10-08～10-14 快照为"前十"口径（stocks 含 10 行），10-15 起为"前七"口径（7 行）；
  矩阵与对比统一只取每行 rank ≤ TOPN=7 的子集，历史快照无需迁移。
"""
import argparse, datetime, json, os, time

from fetch_pool_api import query as xg_query

TOPN = 7  # 方向一·月度前七（矩阵行数与对比基线口径）
COLS = {"rank": "序号", "code": "代码", "name": "名称",
        "month_pct": "区间涨跌幅", "today_pct": "涨跌幅", "auction": "集合竞价涨跌幅"}
WEEK_CN = "一二三四五六日"
EXCL = "不要ST股；不要退市股；不要北交所；不要科创板；不要创业板"

def norm(row, auction_col=True):
    out = {}
    for k, cn in COLS.items():
        v = row.get(cn)
        if k == "rank" and str(v).isdigit():
            v = int(v)
        if k == "auction" and not auction_col:
            v = None
        out[k] = v
    return out

def weekdays_of_month(month, until):
    """month='2026-10'，until='2026-10-14'：枚举当月起始日至 until 的周一~周五（自然日，不含节假日修正——由接口收敛）。"""
    d = datetime.date.fromisoformat(month + "-01")
    end = datetime.date.fromisoformat(until)
    out = []
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out

def label(d):
    """MMDD+星期，如 1014周三"""
    dt = datetime.date.fromisoformat(d)
    return dt.strftime("%m%d") + "周" + WEEK_CN[dt.weekday()]

def interval_end(rawList):
    """从 INTERVAL_CHG 原始键读有效截止交易日（接口已自动收敛节假日）。
    多日窗口键为 INTERVAL_CHG{起|止|N|天}，单日窗口为 INTERVAL_CHG{日期}。"""
    for row in rawList or []:
        for k in row:
            if k.startswith("INTERVAL_CHG{"):
                parts = k[len("INTERVAL_CHG{"):].rstrip("}").split("|")
                return parts[1] if len(parts) >= 2 else parts[0]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True, help="fetch_pool_api 产出的 pool_月度前七.json")
    ap.add_argument("--date", help="快照日期 YYYY-MM-DD，默认取 pool 文件 fetched_at 的日期")
    ap.add_argument("--history", default=os.path.join("archives", "pool-history", "month-top10.jsonl"))
    ap.add_argument("--out", default=".")
    ap.add_argument("--no-backfill", action="store_true", help="跳过当月回补（接口故障降级时用，矩阵只呈现已有快照日）")
    args = ap.parse_args()

    data = json.load(open(args.pool))
    date = args.date or str(data.get("fetched_at", ""))[:10]
    if len(date) != 10 or not date.startswith("2"):
        raise SystemExit("无法确定快照日期，请用 --date 显式指定 YYYY-MM-DD")
    month = date[:7]
    stocks = [norm(r) for r in (data.get("pool") or [])]
    if not stocks:
        raise SystemExit("pool 文件无标的（total=0？），月初窗口事实性空时不写历史库，见 SKILL.md 红线 2")

    hist = []
    if os.path.exists(args.history):
        hist = [json.loads(l) for l in open(args.history) if l.strip()]

    # ---- 1) 当日快照 upsert ----
    hist = [l for l in hist if l.get("date") != date]
    hist.append({"date": date, "latestDate": data.get("latestDate"),
                 "fetched_at": data.get("fetched_at"), "stocks": stocks})

    # ---- 2) 当月回补缺失交易日 ----
    backfilled = []
    if not args.no_backfill:
        have = {l["date"] for l in hist}
        for d in weekdays_of_month(month, date):
            if d in have or d == date:
                continue
            dot = d.replace("-", ".")
            cond = "%s.01至%s区间涨跌幅前七；%s" % (month.replace("-", "."), dot, EXCL)
            try:
                r = xg_query(cond, raw=True)
            except Exception as e:
                print("[WARN] 回补 %s 失败（%s: %s），矩阵缺该日列" % (d, type(e).__name__, str(e)[:80]))
                time.sleep(1.2)
                continue
            end = interval_end(r.get("rawList"))
            if end and end[:7] == month and end not in have and end < date:
                rows = [norm(row, auction_col=False) for row in r.get("pool") or []]
                hist.append({"date": end, "latestDate": end, "fetched_at": None,
                             "src": "backfill", "stocks": rows})
                have.add(end)
                backfilled.append(end)
            time.sleep(1.2)

    hist.sort(key=lambda l: l.get("date", ""))

    # ---- 3) 对比（vs 最近一个不同交易日）与矩阵 ----
    prev = None
    for line in hist[::-1]:
        if line.get("date", "") < date:
            prev = line
            break

    month_dates = [l["date"] for l in hist if l.get("date", "").startswith(month)]
    rank_rows = [{"rank": i, "cells": {}} for i in range(1, TOPN + 1)]
    for l in hist:
        if not l.get("date", "").startswith(month):
            continue
        for s in l["stocks"]:
            if 1 <= s.get("rank", 0) <= TOPN:
                rank_rows[s["rank"] - 1]["cells"][l["date"]] = {
                    "code": s["code"], "name": s["name"], "month_pct": s["month_pct"]}

    cur_codes = {s["code"] for s in stocks}
    prev_top = [p for p in (prev["stocks"] if prev else []) if 1 <= p.get("rank", 99) <= TOPN]
    prev_codes = {p["code"] for p in prev_top}
    added = [s for s in stocks if s["code"] not in prev_codes]
    removed = []
    if prev:
        for p in prev_top:
            if p["code"] not in cur_codes:
                q = {"code": p["code"], "name": p["name"], "prev_rank": p["rank"],
                     "prev_month_pct": p["month_pct"], "prev_today_pct": p["today_pct"],
                     "prev_auction": p["auction"], "note": None, "cells": {}}
                for l in hist:
                    if not l.get("date", "").startswith(month) or l["date"] >= date:
                        continue
                    for s in l["stocks"]:
                        if s["code"] == p["code"] and 1 <= s.get("rank", 99) <= TOPN:
                            q["cells"][l["date"]] = {"rank": s["rank"], "month_pct": s["month_pct"]}
                removed.append(q)
    retained = []
    if prev:
        pmap = {p["code"]: p for p in prev_top}
        for s in stocks:
            if s["code"] in pmap:
                retained.append({**s, "prev_rank": pmap[s["code"]]["rank"],
                                 "delta": pmap[s["code"]]["rank"] - s["rank"]})

    baseline = prev is None
    changes = {
        "date": date, "prev_date": prev["date"] if prev else None, "baseline": baseline,
        "note": "首次记录，无对比基线" if baseline else "",
        "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "added": added, "removed": removed, "retained": retained,
        "matrix": {
            "month": month, "today": date,
            "prev_date": prev["date"] if prev else None, "baseline": baseline,
            "dates": month_dates,
            "labels": {d: label(d) for d in month_dates},
            "rankRows": rank_rows, "removed": removed,
        },
    }

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "top10_changes.json")
    json.dump(changes, open(out_path, "w"), ensure_ascii=False, indent=1)

    os.makedirs(os.path.dirname(args.history) or ".", exist_ok=True)
    with open(args.history, "w") as f:
        for line in hist:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print("[OK] %s vs %s：新进 %d · 移除 %d · 留存 %d；矩阵 %d 列（回补 +%d）-> %s" % (
        date, prev["date"] if prev else "（基线首录）", len(added), len(removed), len(retained),
        len(month_dates), len(backfilled), out_path))

if __name__ == "__main__":
    main()
