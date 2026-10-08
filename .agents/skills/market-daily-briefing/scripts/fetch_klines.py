#!/usr/bin/env python3
"""抓取股池标的日线（新浪K线接口，东财 push2 限流期间的行情兜底源）

用法：
  python3 fetch_klines.py --codes 603928,603906 [--prefixes sh,sh] [--days 26] [--since 09-01] [--out .]
  # 当日盘中合成bar（可选）：--today 603928=10.02,603906=9.98  （code=今日涨幅%）
输出：klines.json {code: [[MM-DD, open, high, low, close], ...]}
说明：代码前缀自动推断（6 开头=sh，其余=sz）；--since 过滤起始日期；--today 用昨收×(1+pct) 合成当日 bar 并在文件头注明。
"""
import argparse, datetime, json, os, re, time, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"

def prefix(code):
    return "sh" if code.startswith("6") else "sz"

def fetch_one(code, days):
    sym = prefix(code) + code
    url = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20k=/CN_MarketDataService.getKLineData"
           f"?symbol={sym}&scale=240&ma=no&datalen={days}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"})
    raw = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore")
    arr = json.loads(re.search(r"\[.*\]", raw, re.S).group(0))
    return [[b["day"][5:], round(float(b["open"]), 2), round(float(b["high"]), 2),
             round(float(b["low"]), 2), round(float(b["close"]), 2)] for b in arr]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True, help="逗号分隔的6位代码")
    ap.add_argument("--days", type=int, default=26)
    ap.add_argument("--since", default="", help="MM-DD，过滤起始日期")
    ap.add_argument("--today", default="", help="code=pct,... 盘中合成当日bar")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    today_pct = {}
    for kv in filter(None, args.today.split(",")):
        c, p = kv.split("=")
        today_pct[c] = float(p)

    out = {}
    for code in filter(None, args.codes.split(",")):
        bars = fetch_one(code, args.days)
        if args.since:
            bars = [b for b in bars if b[0] >= args.since]
        if code in today_pct and bars:
            prev = bars[-1][4]
            c = round(prev * (1 + today_pct[code] / 100), 2)
            bars.append(["10-08", prev, max(prev, c), min(prev, c), c])  # 合成bar：open=昨收
        out[code] = bars
        print("[OK]  %s %d bars (%s → %s)" % (code, len(bars), bars[0][0], bars[-1][0]))
        time.sleep(0.3)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "klines.json")
    json.dump({"_note": "10-08(如存在)为昨收×盘中涨幅合成bar" if today_pct else "全部为实际交易日bar",
               "klines": out}, open(path, "w"), ensure_ascii=False, indent=1)
    print("saved ->", path)

if __name__ == "__main__":
    main()
