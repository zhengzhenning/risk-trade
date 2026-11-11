#!/usr/bin/env python3
"""严重异动预警抓取（东方财富异动追踪中心）

用法：
  python3 scripts/fetch_unusual.py --codes 002086,002578 --out <工作目录>
  python3 scripts/fetch_unusual.py --codes ... --json

数据源：
  1) dycalchis.eastmoney.com/price-anomaly/list     严重异动预测（JSONP）
     字段：c 代码 / n 名称 / x 当前偏离值 / d 统计天数 / t 触发所需当日涨幅 / a 当前涨幅
           e 规则类型 / o 0=当日 2=次日  （同一股票两类都会出现）
  2) datacenter.eastmoney.com … RPT_WATCH_UNUSUAL_FLUCTUATE   异动记录
     IS_HAPPEN=1 → 已触发；TRADE_DATE 为触发日；UNUSUAL_TYPE 为规则全文

产出结构：
  {"ts": "...", "alerts": {
      "002086": {"name": "东方海洋",
                 "today": [{rule,days,dev,need,now,dist,level}],     # 当日预测（o=0）
                 "next":  [{rule,days,dev,need,level}],              # 次日预测（o=2）
                 "triggered": [{date,rule,days,monitorEnd,left}],    # 已触发 + 监管结束日
                 "level": "triggered|near|watch|far"}}}
监管口径（推算）：严重异动触发后进入交易所重点监控，监控期为触发日的 10 个交易日（不含触发当日）。
"""
import argparse, datetime, json, os, re, urllib.request

HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
       "Referer": "https://vipmoney.eastmoney.com/"}
ANOM = ("https://dycalchis.eastmoney.com/price-anomaly/list?team=h5&product=EastMoney&client=WAP"
        "&version=9001&name=WAP&user=12&pageSize=500&pageNo=1&riseOnly=0&showBJS=1&cb=cb")
REC = ("https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_WATCH_UNUSUAL_FLUCTUATE"
       "&columns=SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,MAX_DAYS,DEVUATION_VALUE,"
       "CHANGE_RATE_TARGET,IS_HAPPEN,UNUSUAL_TYPE&quoteColumns=&filter="
       "&pageNumber=1&pageSize=500&sortTypes=-1&sortColumns=&source=SECURITIES&client=APP")
MONITOR_DAYS = 10          # 重点监控期（交易日）
HOLIDAYS = {"2026-09-25", "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
            "2026-10-05", "2026-10-06", "2026-10-07"}


def get(url, timeout=15):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=timeout).read().decode("utf-8", "ignore")


def jsonp(raw):
    return json.loads(raw[raw.index("(") + 1: raw.rindex(")")])


def trading_days_after(start, n):
    """start 之后第 n 个交易日（不含 start 当日）"""
    d = datetime.date.fromisoformat(start[:10])
    cnt = 0
    while cnt < n:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            cnt += 1
    return d.isoformat()


def level_of(now, need, triggered):
    if triggered:
        return "triggered"
    if need is None or now is None:
        return "far"
    dist = round(float(need) - float(now), 2)
    if dist <= 0:
        return "triggered"
    return "near" if dist <= 2 else ("watch" if dist <= 5 else "far")


def build(codes=None):
    pred = jsonp(get(ANOM)).get("data") or []
    recs = json.loads(get(REC))
    rows = ((recs.get("result") or {}).get("data")) or []
    today_map, next_map, trig_map, name_map = {}, {}, {}, {}
    # 规则全文与名称：从记录表按 代码+天数 对齐
    rule_by = {}
    for r in rows:
        code = str(r.get("SECURITY_CODE") or "")
        if codes and code not in codes:
            continue
        name_map.setdefault(code, r.get("SECURITY_NAME_ABBR") or "")
        if r.get("UNUSUAL_TYPE"):
            rule_by[(code, int(r.get("MAX_DAYS") or 0))] = r["UNUSUAL_TYPE"]
    for r in pred:
        code = str(r.get("c") or "")
        if codes and code not in codes:
            continue
        need, now = r.get("t"), r.get("a")
        item = {"rule": rule_by.get((code, int(r.get("d") or 0)), ""), "days": r.get("d"), "dev": r.get("x"), "need": need, "now": now,
                "dist": round(float(need) - float(now), 2) if need is not None and now is not None else None}
        (today_map if int(r.get("o") or 0) == 0 else next_map).setdefault(code, []).append(item)
    for r in rows:
        code = str(r.get("SECURITY_CODE") or "")
        if codes and code not in codes:
            continue
        if str(r.get("IS_HAPPEN")) != "1":
            continue
        date = (r.get("TRADE_DATE") or "")[:10]
        if not date:
            continue
        end = trading_days_after(date, MONITOR_DAYS)
        left = (datetime.date.fromisoformat(end) - datetime.date.today()).days
        trig_map.setdefault(code, []).append({
            "date": date, "rule": r.get("UNUSUAL_TYPE") or "", "days": r.get("MAX_DAYS"),
            "monitorEnd": end, "leftDays": max(0, left),
        })
    out = {}
    for code in (set(list(today_map) + list(next_map) + list(trig_map)) or set()):
        today = today_map.get(code, [])
        nxt = next_map.get(code, [])
        trig = sorted(trig_map.get(code, []), key=lambda x: x["date"], reverse=True)
        # 规则全文：用触发记录/记录表补全（预测接口不带规则文本）
        for arr in (today, nxt):
            for it in arr:
                if not it["rule"]:
                    it["rule"] = "严重异动预测（%s 日累计偏离）" % it["days"]
        lv = "triggered" if trig else "far"
        if not trig and today:
            lv = min((level_of(x["now"], x["need"], False) for x in today),
                     key=lambda v: {"triggered": 0, "near": 1, "watch": 2, "far": 3}[v])
        out[code] = {"name": name_map.get(code, ""), "today": sorted(today, key=lambda x: abs(x["dist"] or 99)),
                     "next": sorted(nxt, key=lambda x: (x["need"] or 99)),
                     "triggered": trig, "level": lv}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", default="")
    ap.add_argument("--out", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    codes = set(c.strip() for c in args.codes.split(",") if c.strip()) or None
    alerts = build(codes)
    payload = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "alerts": alerts}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return
    os.makedirs(args.out, exist_ok=True)
    p = os.path.join(args.out, "unusual.json")
    tmp = p + ".tmp"
    json.dump(payload, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    print("[OK] %d 只标的在异动追踪中心有记录 → %s" % (len(alerts), p))
    for code, a in alerts.items():
        t = a["today"][0] if a["today"] else None
        n = a["next"][0] if a["next"] else None
        g = a["triggered"][0] if a["triggered"] else None
        print("   %s %s | 当日%s | 次日%s | 已触发%s" % (
            code, a["level"],
            "距%.2f%%" % t["dist"] if t and t["dist"] is not None else "—",
            "需+%.2f%%" % n["need"] if n and n["need"] is not None else "—",
            ("%s → 监管至 %s（剩 %s 天）" % (g["date"], g["monitorEnd"], g["leftDays"])) if g else "—"))


if __name__ == "__main__":
    main()
