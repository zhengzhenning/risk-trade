#!/usr/bin/env python3
"""全市场涨停池抓取（名字系联动扫描数据源）

用法：
  python3 scripts/fetch_limitup.py --date 2026-11-11 --out <工作目录>
  python3 scripts/fetch_limitup.py --date 2026-11-11 --scan 东方,龙,羊|阳|洋

产出 limitup.json：{date, count, pool:[{code,name,lbc,zdp,zbc,first,last,amount}], families:{关键词:[{code,name,lbc}]}}
用途：L1 名字/玄学系炒作判定的「联动股」证据——同日涨停名单中含同一关键词的股票数量与连板高度。
只读接口；盘中可重复调用（同一快照时点）。
"""
import argparse, json, os, re, time, urllib.request

API = "https://push2ex.eastmoney.com/getTopicZTPool"
HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
       "Referer": "https://quote.eastmoney.com/"}
DEFAULT_FAMS = ["东方", "龙", "羊|阳|洋", "龙|凤", "666|888"]


def fetch(date):
    url = (API + "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=300"
           "&sort=fbt%3Aasc&date=" + date)
    req = urllib.request.Request(url, headers=HDR)
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    data = json.loads(raw)
    pool = ((data.get("data") or {}).get("pool")) or []
    out = []
    for p in pool:
        out.append({
            "code": p.get("c"), "name": (p.get("n") or "").replace(" ", ""),
            "lbc": p.get("lbc") or 0,
            "zdp": round(float(p.get("zdp") or 0), 2),
            "zbc": p.get("zbc") or 0,
            "first": str(p.get("fbt") or "").zfill(6),
            "last": str(p.get("lbt") or "").zfill(6),
            "amount": p.get("amount"),
        })
    return out


def scan(pool, fams):
    res = {}
    for f in fams:
        hit = [{"code": p["code"], "name": p["name"], "lbc": p["lbc"]} for p in pool if re.search(f, p["name"])]
        res[f] = hit
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", default=".")
    ap.add_argument("--scan", default=",".join(DEFAULT_FAMS))
    args = ap.parse_args()
    d = args.date.replace("-", "")
    for attempt in range(3):
        try:
            pool = fetch(d)
            break
        except Exception as e:
            print("[WARN] retry", attempt + 1, type(e).__name__, str(e)[:80])
            time.sleep(1.2)
    else:
        raise SystemExit("涨停池抓取失败")
    fams = [f for f in args.scan.split(",") if f]
    res = {"date": args.date, "count": len(pool), "pool": pool, "families": scan(pool, fams)}
    os.makedirs(args.out, exist_ok=True)
    p = os.path.join(args.out, "limitup.json")
    json.dump(res, open(p, "w"), ensure_ascii=False, indent=1)
    print("[OK] 涨停 %d 只 -> %s" % (len(pool), p))
    for f in fams:
        hit = res["families"][f]
        print("  名字系 %-10s %d 只 %s" % (f, len(hit), [h["name"] + "(" + str(h["lbc"]) + "板)" for h in hit[:6]]))


if __name__ == "__main__":
    main()
