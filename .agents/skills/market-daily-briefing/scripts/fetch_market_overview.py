#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大盘总览数据抓取（第 3.5 步）：上证指数/科创50 近3个月日K + 全A两市合计成交额。

产出 market_overview.json（看板 MKT 数据块，原样注入）：
- idx[0] 上证指数、idx[1] 科创50：close/chg/pct/amt（最新收盘与涨跌）、hi/lo（窗口盘中极值）、
  O/H/L/C/V 数组（近3个月日K：开高低收 + 沪市/板块成交额，单位亿元）
- days[{d, pct, kcPct, amt}]：逐日上证/科创50 涨跌幅 + 全A成交额（亿元）
- 全A口径 = 上证指数（沪市）+ 深证综指（深市）日成交额合计；ma5/stat（今日/5日均/3月均/天量/地量）

接口：东财 push2his 日K（klt=101）——仅 3 次轻量请求、间隔 ≥1.2s，每轮执行仅一次；
不触碰 push2.eastmoney.com 全量分页（红线第 3 条）。失败重试 2 次；三指数任一彻底失败则
输出 {"error": ...} 并以非零码退出，由模型在文末数据质量说明标注"大盘总览待补"，不阻塞简报。

用法：
  python3 skills/market-daily-briefing/scripts/fetch_market_overview.py --out <工作目录>
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.request

SECIDS = {"sh": "1.000001", "sz": "0.399106", "kc": "1.000688"}  # 上证指数/深证综指/科创50
URL = ("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={s}"
       "&klt=101&fqt=1&lmt={lmt}&end=20500101&fields1=f1,f2,f3"
       "&fields2=f51,f52,f53,f54,f55,f57")  # 日期,开,收,高,低,成交额(元)
WINDOW_DAYS = 92   # 近3个月（自然日），约 60 个交易日
RETRIES = 2
SLEEP = 1.2


def fetch(secid, lmt):
    last_err = None
    for k in range(RETRIES + 1):
        try:
            req = urllib.request.Request(
                URL.format(s=secid, lmt=lmt),
                headers={"Referer": "https://quote.eastmoney.com/",
                         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)["data"]
            rows = {}
            for line in data["klines"]:
                d, o, c, h, l, a = line.split(",")
                rows[d] = {"o": float(o), "c": float(c), "h": float(h),
                           "l": float(l), "a": float(a)}
            return data["name"], rows
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(SLEEP * (k + 1))
    raise RuntimeError(f"{secid} 抓取失败：{last_err}")


def main():
    ap = argparse.ArgumentParser(description="大盘总览：指数日K + 全A成交额 → market_overview.json")
    ap.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    ap.add_argument("--lmt", type=int, default=75, help="K线拉取根数（默认 75）")
    args = ap.parse_args()

    raw = {}
    for key, secid in SECIDS.items():
        name, rows = fetch(secid, args.lmt)
        raw[key] = rows
        print(f"[ok] {key} {name} {len(rows)} bars -> {max(rows)}")
        time.sleep(SLEEP)

    dates = sorted(set(raw["sh"]) & set(raw["sz"]) & set(raw["kc"]))
    if len(dates) < 10:
        out = {"error": f"三指数交易日交集过少：{len(dates)}"}
        path = os.path.join(args.out, "market_overview.json")
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[fail] {path} {out['error']}", file=sys.stderr)
        sys.exit(1)

    last = dates[-1]
    cut = (dt.date.fromisoformat(last) - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    win = [d for d in dates if d > cut]

    days = []
    for i, d in enumerate(win):
        j = dates.index(d)
        pd_ = dates[j - 1]
        days.append({
            "d": d,
            "pct": round((raw["sh"][d]["c"] / raw["sh"][pd_]["c"] - 1) * 100, 2),
            "kcPct": round((raw["kc"][d]["c"] / raw["kc"][pd_]["c"] - 1) * 100, 2),
            "amt": round((raw["sh"][d]["a"] + raw["sz"][d]["a"]) / 1e8, 1),
        })

    amts = [x["amt"] for x in days]
    ma5 = [round(sum(amts[max(0, i - 4):i + 1]) / len(amts[max(0, i - 4):i + 1]), 1)
           for i in range(len(amts))]
    mx = max(days, key=lambda x: x["amt"])
    mn = min(days, key=lambda x: x["amt"])

    def card(key, nm, en, color, amt_label):
        a = {"O": [], "H": [], "L": [], "C": [], "V": []}
        for d in win:
            r = raw[key][d]
            a["O"].append(r["o"]); a["H"].append(r["h"]); a["L"].append(r["l"])
            a["C"].append(r["c"]); a["V"].append(round(r["a"] / 1e8, 1))
        j2 = dates.index(last)
        pd_ = dates[j2 - 1]
        cur, prev = raw[key][last], raw[key][pd_]
        return {"nm": nm, "en": en, "color": color,
                "close": cur["c"], "chg": round(cur["c"] - prev["c"], 2),
                "pct": round((cur["c"] / prev["c"] - 1) * 100, 2),
                "amt": round(cur["a"] / 1e8, 1), "amtLabel": amt_label,
                "hi": max(a["H"]), "lo": min(a["L"]),
                "O": a["O"], "H": a["H"], "L": a["L"], "C": a["C"], "V": a["V"]}

    mkt = {
        "asOf": last,
        "window": {"from": win[0], "to": last, "td": len(win)},
        "dates": win,
        "days": days,
        "ma5": ma5,
        "idx": [card("sh", "上证指数", "SSE COMPOSITE", "#3b66d4", "沪市当日成交"),
                card("kc", "科创50", "STAR 50", "#d63450", "板块当日成交")],
        "stat": {"last": amts[-1], "ma5": ma5[-1],
                 "avg": round(sum(amts) / len(amts), 1),
                 "max": {"d": mx["d"], "v": mx["amt"]},
                 "min": {"d": mn["d"], "v": mn["amt"]}},
    }
    path = os.path.join(args.out, "market_overview.json")
    os.makedirs(args.out, exist_ok=True)
    json.dump(mkt, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    s = mkt["stat"]
    print(f"[done] {path}")
    print(f"  窗口 {win[0]} → {last}（{len(win)} 个交易日）")
    print(f"  上证 {mkt['idx'][0]['close']:+.2f}({mkt['idx'][0]['pct']:+.2f}%) "
          f"科创50 {mkt['idx'][1]['close']:+.2f}({mkt['idx'][1]['pct']:+.2f}%)")
    print(f"  全A 今日 {s['last']}亿 · 5日均 {s['ma5']}亿 · 3月均 {s['avg']}亿 "
          f"· 天量 {s['max']['v']}亿({s['max']['d']}) · 地量 {s['min']['v']}亿({s['min']['d']})")


if __name__ == "__main__":
    main()
