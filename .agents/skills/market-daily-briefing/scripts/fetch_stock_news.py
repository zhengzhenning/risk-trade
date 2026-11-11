#!/usr/bin/env python3
"""个股资讯抓取：东方财富搜索接口按代码/名称取近期个股新闻（供主升催化·个股逻辑归因用）

用法：
  python3 scripts/fetch_stock_news.py --codes 002578,601599 --size 8 --out <工作目录>

产出 stock_news.json：{ "002578": [ {date, media, title, url, snippet}, ... ] }
只读接口，不写历史库；限频每码 ≥0.8s。
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

API = "https://search-api-web.eastmoney.com/search/jsonp"
HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
       "Referer": "https://so.eastmoney.com/"}


def query(keyword, size=8):
    param = {
        "uid": "", "keyword": keyword, "type": ["cmsArticleWebOld"],
        "client": "web", "clientType": "web", "clientVersion": "curr",
        "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default",
                                       "pageIndex": 1, "pageSize": size,
                                       "preTag": "<em>", "postTag": "</em>"}},
    }
    url = API + "?cb=cb&param=" + urllib.parse.quote(json.dumps(param, ensure_ascii=False))
    req = urllib.request.Request(url, headers=HDR)
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    txt = raw[raw.index("(") + 1:raw.rindex(")")]
    data = json.loads(txt)
    items = (data.get("result") or {}).get("cmsArticleWebOld") or []
    out = []
    for it in items:
        clean = lambda s: (s or "").replace("<em>", "").replace("</em>", "")
        out.append({
            "date": (it.get("date") or "")[:16],
            "media": clean(it.get("mediaName")),
            "title": clean(it.get("title")),
            "url": it.get("url") or "",
            "snippet": clean(it.get("content"))[:160],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True, help="逗号分隔股票代码")
    ap.add_argument("--size", type=int, default=8)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    res = {}
    for i, c in enumerate(codes):
        try:
            res[c] = query(c, args.size)
            print("[OK]", c, len(res[c]), "条", res[c][0]["date"] if res[c] else "—")
        except Exception as e:
            res[c] = []
            print("[WARN]", c, type(e).__name__, str(e)[:80])
        if i < len(codes) - 1:
            time.sleep(0.9)
    os.makedirs(args.out, exist_ok=True)
    p = os.path.join(args.out, "stock_news.json")
    json.dump(res, open(p, "w"), ensure_ascii=False, indent=1)
    print("saved ->", p)


if __name__ == "__main__":
    main()
