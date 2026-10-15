#!/usr/bin/env python3
"""选股器条件直连取股池（无需保存方案 ID）

接口：POST https://np-tjxg-b.eastmoney.com/api/smart-tag/stock/v3/pw/search-code
原理：选股器"AI 选股"后端接受自然语言条件（keyWordNew），列结构自描述（columns[].title ↔ dataList key），
      因此任意条件都能取数且列名自适应，无列号错位问题。

用法：
  python3 fetch_pool_api.py --direction all        # 月度前七 + 近十日三强 + 连板天梯（完整流水线）
  python3 fetch_pool_api.py --direction both       # 双窗口股池（month + d10）
  python3 fetch_pool_api.py --direction month      # 仅方向一（月度前七）
  python3 fetch_pool_api.py --cond "任意自然语言条件" --tag 自定义
输出：pool_<tag>.json {tag, condition, total, latestDate, pool:[{中文列名: 值}], fetched_at}

注意：接口无 cookie 依赖、fingerprint/requestId 可伪造；请控制频率（单方向间隔 ≥1s），勿循环刷。
      股池条件里的"竞价涨幅大于-11%"是**非过滤性字段提及**（剔创/科/北/ST 后全为主板，涨跌停±10%，
      任何竞价涨幅都 > -11%），唯一作用是让自适应列带出"集合竞价涨跌幅"。
      禁止改用"竞价金额大于0元"——实测会过滤掉无竞价成交的标的（total 10→9）。
"""
import argparse, datetime, json, os, time, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
URL = "https://np-tjxg-b.eastmoney.com/api/smart-tag/stock/v3/pw/search-code"

# 内置方向（条件文本可按需改；措辞规范见 references/channel-guide.md，均已一次性验证）
DIRECTIONS = {
    "month": ("月度前七",
              "本月涨幅前七；不要ST股；不要退市股；不要北交所；不要科创板；不要创业板；竞价涨幅大于-11%"),
    "d10": ("近十日三强",
            "近十日涨幅前三；不要ST股；不要退市股；不要北交所；不要科创板；不要创业板；竞价涨幅大于-11%"),
    "ladder": ("连板天梯",
               "连板大于等于2；不要ST股；不要退市股；不要北交所；不要科创板；不要创业板"),
}

def query(cond, raw=False):
    body = {
        "needAmbiguousSuggest": True, "pageSize": 50, "pageNo": 1,
        "fingerprint": "84151842d0ff834d33c1b482db9020f7", "matchWord": "",
        "shareToGuba": False, "timestamp": str(int(time.time() * 1000)) + "053",
        "requestId": "zcode" + str(int(time.time() * 1000)),
        "removedConditionIdList": [], "allCode": True, "ownSelectAll": False,
        "needCorrect": True, "client": "WEB", "product": "", "needShowStockNum": False,
        "biz": "web_ai_select_stocks", "xcId": "", "gids": [], "dxInfoNew": [],
        "keyWordNew": cond,
        "customDataNew": json.dumps([{"type": "text", "value": cond, "extra": ""}], ensure_ascii=False),
    }
    req = urllib.request.Request(URL, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          "Origin": "https://xuangu.eastmoney.com",
                                          "Referer": "https://xuangu.eastmoney.com/"})
    d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore"))
    if d.get("code") == "201":
        # 条件空结果（非故障）：典型如月初"本月涨幅>20%"但主板单日涨幅上限10%
        return {"total": 0, "pool": []}
    if d.get("code") != "100":
        raise RuntimeError("接口返回 code=%s msg=%s" % (d.get("code"), d.get("msg")))
    res = (d.get("data") or {}).get("result") or {}
    cols = {c["key"]: c["title"] for c in (res.get("columns") or [])}
    rawList = res.get("dataList") or []
    pool = []
    for row in rawList:
        pool.append({cols.get(k, k): v for k, v in row.items()})
    out = {"total": res.get("total", len(pool)), "pool": pool, "latestDate": res.get("latestDate")}
    if raw:
        out["rawList"] = rawList
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", choices=["month", "d10", "ladder", "both", "all"], default="both")
    ap.add_argument("--cond", help="自定义自然语言条件")
    ap.add_argument("--tag", default="custom")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    tasks = []
    if args.cond:
        tasks.append((args.tag, args.cond))
    else:
        if args.direction == "both":
            keys = ["month", "d10"]
        elif args.direction == "all":
            keys = ["month", "d10", "ladder"]
        else:
            keys = [args.direction]
        tasks = [(DIRECTIONS[k][0], DIRECTIONS[k][1]) for k in keys]

    os.makedirs(args.out, exist_ok=True)
    for tag, cond in tasks:
        try:
            r = query(cond)
            out = {"tag": tag, "condition": cond, "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "total": r["total"], "latestDate": r.get("latestDate"), "pool": r["pool"]}
            path = os.path.join(args.out, "pool_%s.json" % tag)
            json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
            print("[OK]   %-8s %2d 只 -> %s" % (tag, r["total"], path))
        except Exception as e:
            print("[FAIL] %-8s %s: %s" % (tag, type(e).__name__, str(e)[:120]))
        time.sleep(1.2)

if __name__ == "__main__":
    main()
