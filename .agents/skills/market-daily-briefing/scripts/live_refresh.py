#!/usr/bin/env python3
"""分钟级实时数据刷新（L1 实时层）：写 live.json 供看板页面轮询

用法：
  python3 scripts/live_refresh.py --out <目录> [--codes 002578,601599,...]        # 单次
  python3 scripts/live_refresh.py --out <目录> --watch 60                          # 守护，每 60s 一次
  python3 scripts/live_refresh.py --out <目录> --codes ... --watch 60 --min-interval 55

口径：
  · 指数实时价/涨幅/成交额 = push2 ulist（上证 1.000001、科创50 1.000688、深证成指 0.399001）
  · 两市成交额 = 上证 f6 + 深证成指 f6（与 fetch_market_overview 的口径一致，单位换算为亿）
  · 个股实时 = 前七标的（6 开头 → 沪 1. 前缀，0/3 开头 → 深 0. 前缀）
  · 涨停池 = push2ex getTopicZTPool（数量 + 名字系「东方」「龙」扫描）
交易时段之外自动跳过；原子写（临时文件 + os.replace）避免页面读到半截 JSON。
"""
import argparse, datetime, json, os, time, urllib.parse, urllib.request

HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
       "Referer": "https://quote.eastmoney.com/"}
ULIST = ("https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2"
         "&fields=f1,f2,f3,f4,f6,f12,f13,f14&secids=")
ZTPOOL = "https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=300&sort=fbt%3Aasc&date="


def get(url, timeout=8):
    req = urllib.request.Request(url, headers=HDR)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def secid(code):
    return ("1." if code[:1] == "6" else "0.") + code


def session_state(now=None):
    """返回 trading / lunch / closed（仅按工作日+时段，不含交易日历）。"""
    n = now or datetime.datetime.now()
    if n.weekday() >= 5:
        return "closed"
    t = n.hour * 60 + n.minute
    if (9 * 60 + 15) <= t <= (11 * 60 + 30):
        return "trading"
    if (11 * 60 + 30) < t < (13 * 60):
        return "lunch"
    if (13 * 60) <= t <= (15 * 60 + 5):
        return "trading"
    return "closed"


def fetch_idx():
    d = json.loads(get(ULIST + "1.000001,1.000688,0.399001"))
    out = {}
    for x in (d.get("data") or {}).get("diff") or []:
        key = {"000001": "sh", "000688": "kc50", "399001": "sz"}.get(x.get("f12"))
        if not key:
            continue
        amt = x.get("f6") or 0
        out[key] = {"name": x.get("f14"), "p": x.get("f2"), "chg": x.get("f4"),
                    "pct": x.get("f3"), "amt": round(amt / 1e8, 1)}
    if "sh" in out and "sz" in out:
        out["total_amt"] = round((out["sh"]["amt"] or 0) + (out["sz"]["amt"] or 0), 1)
    return out


def fetch_stocks(codes):
    if not codes:
        return {}
    d = json.loads(get(ULIST + ",".join(secid(c) for c in codes)))
    out = {}
    for x in (d.get("data") or {}).get("diff") or []:
        out[str(x.get("f12"))] = {"name": x.get("f14"), "p": x.get("f2"),
                                  "pct": x.get("f3"), "chg": x.get("f4"),
                                  "amt": round((x.get("f6") or 0) / 1e8, 1)}
    return out


def fetch_zt(date):
    d = json.loads(get(ZTPOOL + date, timeout=10))
    pool = ((d.get("data") or {}).get("pool")) or []
    fam = {"东方": 0, "龙": 0}
    for p in pool:
        nm = (p.get("n") or "").replace(" ", "")
        for k in fam:
            if k in nm:
                fam[k] += 1
    lb = sorted([p.get("lbc") or 0 for p in pool], reverse=True)[:3]
    return {"count": len(pool), "families": fam, "top_lb": lb}


def write_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def once(outdir, codes):
    now = datetime.datetime.now()
    state = session_state(now)
    data = {"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "epoch": int(now.timestamp()),
            "session": state, "date": now.strftime("%Y-%m-%d")}
    errs = []
    try:
        idx = fetch_idx()
        data["idx"] = idx
        if idx.get("total_amt"):
            data["amt"] = idx["total_amt"]
    except Exception as e:
        errs.append("idx:" + type(e).__name__)
    try:
        data["stocks"] = fetch_stocks(codes)
    except Exception as e:
        errs.append("stocks:" + type(e).__name__)
    try:
        data["zt"] = fetch_zt(now.strftime("%Y%m%d"))
    except Exception as e:
        errs.append("zt:" + type(e).__name__)
    if errs:
        data["err"] = errs
    write_atomic(os.path.join(outdir, "live.json"), data)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="archives", help="输出目录（live.json 落在此目录）")
    ap.add_argument("--codes", default="", help="前七标的代码，逗号分隔")
    ap.add_argument("--watch", type=int, default=0, help="秒；>0 则循环刷新")
    ap.add_argument("--min-interval", type=int, default=55)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if not args.watch:
        d = once(args.out, codes)
        print("[OK]", d["ts"], d["session"], "两市", d.get("amt"), "亿", "涨停", (d.get("zt") or {}).get("count"),
              "err", d.get("err"))
        return
    print("[INFO] watch 启动：每", args.watch, "s 刷新 →", os.path.join(args.out, "live.json"))
    while True:
        st = session_state()
        if st == "closed":
            now = datetime.datetime.now()
            write_atomic(os.path.join(args.out, "live.json"),
                         {"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "epoch": int(now.timestamp()),
                          "session": "closed", "date": now.strftime("%Y-%m-%d")})
            print("[INFO]", now.strftime("%H:%M"), "非交易时段，跳过抓取")
        else:
            try:
                d = once(args.out, codes)
                print("[OK]", d["ts"], d["session"], "两市", d.get("amt"), "亿", "涨停", (d.get("zt") or {}).get("count"),
                      ("err " + str(d["err"])) if d.get("err") else "")
            except Exception as e:
                print("[WARN]", type(e).__name__, str(e)[:80])
        time.sleep(max(args.min_interval, 30) if args.watch <= 60 else args.watch)


if __name__ == "__main__":
    main()
