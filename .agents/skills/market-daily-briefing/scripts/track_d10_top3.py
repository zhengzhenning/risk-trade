#!/usr/bin/env python3
"""十日前三：当月逐日快照回补 + 全景矩阵视图模型（看板《十日前3·当月全景》数据源）

用法（在仓库根目录执行）：
  python3 skills/market-daily-briefing/scripts/track_d10_top3.py \
      --pool <工作目录>/pool_近十日三强.json [--date 2026-11-04] --out <工作目录>

职责：
1. 当日快照：从 --pool（第 3 步"近十日涨幅前三"原生结果）规整入历史库（同日重跑覆盖当日行）。
2. 当月回补：对当月历史库缺失的交易日 D，用区间措辞查询"起日至 D 共 10 个交易日区间涨跌幅前三"
   重建该时点三强。起点=从 D 往前数第 10 个交易日（交易日序列取月度历史库快照日 ∪ 当月周一~周五，
   接口自动收敛节假日，从 INTERVAL_CHG{起|止|N|天} 回读校验）。**回补查询不带竞价子句**
   （集合竞价列对历史区间返回最新交易日值，不能当历史当日值）。
3. 产出 d10_changes.json：matrix={month, today, dates=当月快照日, labels=MMDD+星期,
   rankRows=[{rank:1..3, cells:{日期:{code,name,d10_pct}}}]}（d10_pct=近十日区间涨跌幅）。
   题材（themes）不在脚本产出，由模型回填（与 POOLCHG.themes 共用一份映射）。

历史库：archives/pool-history/d10-top3.jsonl，每行一个交易日快照：
  {date, fetched_at, stocks:[{rank, code, name, d10_pct, today_pct, auction}]}
只存接口原始结果，禁止手工补写。限频：回补查询间隔 ≥1.2s，只查缺失日期，禁止重复刷。
"""
import argparse, datetime, json, os, time

from fetch_pool_api import query as xg_query

TOPN = 3  # 方向二·近十日三强（矩阵行数）
WINDOW = 10  # 近十日=10 个交易日区间（接口原生口径）
COLS = {"rank": "序号", "code": "代码", "name": "名称",
        "d10_pct": "区间涨跌幅", "today_pct": "涨跌幅", "auction": "集合竞价涨跌幅"}
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
    d = datetime.date.fromisoformat(month + "-01")
    end = datetime.date.fromisoformat(until)
    out = []
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def label(d):
    dt = datetime.date.fromisoformat(d)
    return dt.strftime("%m%d") + "周" + WEEK_CN[dt.weekday()]


def interval_bounds(rawList):
    """从 INTERVAL_CHG{起|止|N|天} 原始键读有效起止交易日（接口已自动收敛节假日）。"""
    for row in rawList or []:
        for k in row:
            if k.startswith("INTERVAL_CHG{") and "|" in k:
                parts = k[len("INTERVAL_CHG{"):].rstrip("}").split("|")
                if len(parts) >= 3:
                    return parts[0], parts[1]
    return None, None


def trading_days(month_hist_dates, month, until):
    """交易日序列（升序去重）=月度历史库快照日 ∪ 当月工作日。用于定位 10 日窗口起点。"""
    days = set(month_hist_dates)
    days |= set(weekdays_of_month(month, until))
    return sorted(d for d in days if d <= until)


def window_start(days, end_date):
    """从 end_date 往前数第 WINDOW 个交易日作为区间起点。"""
    seq = [d for d in days if d <= end_date]
    if len(seq) < WINDOW:
        return None
    return seq[-WINDOW]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True, help="fetch_pool_api 产出的 pool_近十日三强.json")
    ap.add_argument("--date", help="快照日期 YYYY-MM-DD，默认取 pool 文件 fetched_at 的日期")
    ap.add_argument("--history", default=os.path.join("archives", "pool-history", "d10-top3.jsonl"))
    ap.add_argument("--month-history", default=os.path.join("archives", "pool-history", "month-top10.jsonl"),
                    help="月度历史库（提供交易日序列）")
    ap.add_argument("--out", default=".")
    ap.add_argument("--no-backfill", action="store_true", help="跳过当月回补（接口故障降级时用）")
    args = ap.parse_args()

    data = json.load(open(args.pool))
    date = args.date or str(data.get("fetched_at", ""))[:10]
    if len(date) != 10 or not date.startswith("2"):
        raise SystemExit("无法确定快照日期，请用 --date 显式指定 YYYY-MM-DD")
    month = date[:7]
    stocks = [norm(r) for r in (data.get("pool") or [])]
    if not stocks:
        raise SystemExit("pool 文件无标的（total=0），不写历史库")

    hist = []
    if os.path.exists(args.history):
        hist = [json.loads(l) for l in open(args.history) if l.strip()]
    month_hist_dates = []
    if os.path.exists(args.month_history):
        month_hist_dates = [json.loads(l)["date"] for l in open(args.month_history) if l.strip()]

    # ---- 1) 当日快照 upsert ----
    hist = [l for l in hist if l.get("date") != date]
    hist.append({"date": date, "fetched_at": data.get("fetched_at"), "stocks": stocks})

    # ---- 2) 当月回补缺失交易日 ----
    days = trading_days(month_hist_dates, month, date)
    backfilled = []
    if not args.no_backfill:
        have = {l["date"] for l in hist}
        for d in weekdays_of_month(month, date):
            if d in have or d == date:
                continue
            start = window_start(days, d)
            if not start:
                continue
            cond = "%s至%s区间涨跌幅前三；%s" % (start.replace("-", "."), d.replace("-", "."), EXCL)
            try:
                r = xg_query(cond, raw=True)
            except Exception as e:
                print("[WARN] 回补 %s 失败（%s: %s），矩阵缺该日列" % (d, type(e).__name__, str(e)[:80]))
                time.sleep(1.2)
                continue
            s0, e0 = interval_bounds(r.get("rawList"))
            if e0 and e0 == d:  # 收敛截止=目标日即可采信（起止写入 window 供核对）
                rows = [norm(row, auction_col=False) for row in r.get("pool") or []]
                hist.append({"date": e0, "fetched_at": None, "src": "backfill",
                             "window": {"start": s0, "end": e0}, "stocks": rows})
                have.add(e0)
                backfilled.append(e0)
            time.sleep(1.2)

    hist.sort(key=lambda l: l.get("date", ""))

    # ---- 3) 矩阵视图模型 ----
    month_dates = [l["date"] for l in hist if l.get("date", "").startswith(month)]
    rank_rows = [{"rank": i, "cells": {}} for i in range(1, TOPN + 1)]
    for l in hist:
        if not l.get("date", "").startswith(month):
            continue
        for s in l["stocks"]:
            if 1 <= s.get("rank", 0) <= TOPN:
                rank_rows[s["rank"] - 1]["cells"][l["date"]] = {
                    "code": s["code"], "name": s["name"], "d10_pct": s["d10_pct"]}

    changes = {
        "date": date,
        "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "matrix": {
            "month": month, "today": date,
            "dates": month_dates,
            "labels": {d: label(d) for d in month_dates},
            "rankRows": rank_rows,
        },
    }

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "d10_changes.json")
    json.dump(changes, open(out_path, "w"), ensure_ascii=False, indent=1)

    os.makedirs(os.path.dirname(args.history) or ".", exist_ok=True)
    with open(args.history, "w") as f:
        for line in hist:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print("[OK] 十日前三矩阵 %d 列（回补 +%d）-> %s" % (len(month_dates), len(backfilled), out_path))


if __name__ == "__main__":
    main()
