#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""个股 K 线 + 板块梯队采集（量价阶段复盘数据源）

用法:
  python3 fetch_stock_vp.py --codes 601599,002578 --out <DIR> [--bars 60]
                            [--concepts <prefetched concepts.json>] [--map "601599=影视院线,..."]

产出:
  klines.json  {code: [[date, open, close, low, high, vol万手, pct, turnover]...]}   # 前复权日K
  peers.json   {code: {board, rows:[{code,name,pct,price,turn,mktcap,mkt}]}}          # 板块内按今日涨幅

数据源:
  push2his 日K（klt=101, fqt=1，轻量白名单，单只 1 次）
  push2 clist 行业板块列表 + 板块成分（单页 ≤15，不做全市场分页）
限频：每次请求间隔 1.2s。
"""
import argparse, json, os, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
HINT = {"其他纺织": "影视院线", "影视": "影视院线", "广告营销": "广告营销", "营销代理": "广告营销",
        "铝": "铝", "光伏辅材": "光伏辅材", "耐火材料": "耐火材料",
        "水产养殖": "水产养殖", "海水养殖": "水产养殖", "其他电子": "元件", "电子": "元件"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def board_list():
    boards = []
    for pn in range(1, 6):
        url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=%d&pz=100&po=1&np=1&fltt=2&invt=2"
               "&fid=f3&fs=m:90+t:2&fields=f12,f14,f3" % pn)
        d = get(url)
        diff = (d.get("data") or {}).get("diff") or []
        if not diff:
            break
        boards += [(x["f14"], x["f12"]) for x in diff]
        time.sleep(1.2)
    return boards


def pick_board(industries, boards):
    tokens = list(reversed(industries))
    for token in tokens:                      # F10 语义优先：如 其他纺织→影视院线
        hint = HINT.get(token)
        if not hint:
            for k, v in HINT.items():
                if k in token:
                    hint = v
                    break
        if hint:
            for name, code in boards:
                if name == hint:
                    return name, code
    for token in tokens:
        for name, code in boards:
            if name == token:
                return name, code
    for token in tokens:
        for name, code in boards:
            if token and (token in name or name in token):
                return name, code
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bars", type=int, default=60)
    ap.add_argument("--concepts", help="fetch_concepts.py 产出的 concepts.json，用于匹配行业板块")
    ap.add_argument("--map", default="", help='手工板块映射，如 "601599=影视院线,002578=铝"')
    args = ap.parse_args()
    codes = [c for c in args.codes.split(",") if c]
    os.makedirs(args.out, exist_ok=True)

    concepts = {}
    if args.concepts and os.path.exists(args.concepts):
        concepts = json.load(open(args.concepts, encoding="utf-8"))
    overrides = dict(x.split("=", 1) for x in args.map.split(",") if "=" in x)
    boards = board_list()

    peers, klines = {}, {}
    for code in codes:
        inds = []
        c = concepts.get(code) or {}
        if isinstance(c.get("industry"), list):
            inds = c["industry"]
        elif isinstance(c.get("industry"), str):
            inds = [c["industry"]]
        for it in (c.get("hxtc") or []):          # 主营关键词（最具体）追加在后，匹配时倒序优先
            if it.get("cls") == "主营业务" and it.get("kw"):
                inds.append(it["kw"])
        if code in overrides:
            bname, bcode = overrides[code], None
            for name, bk in boards:
                if name == bname:
                    bcode = bk
            if bcode is None:
                raise SystemExit("board not found: " + bname)
        else:
            bname, bcode = pick_board(inds, boards)
        if bcode:
            url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fltt=2&invt=2"
                   "&fid=f3&fs=b:%s&fields=f12,f14,f3,f2,f8,f20,f13" % bcode)
            d = get(url)
            rows = (d.get("data") or {}).get("diff") or []
            peers[code] = {"board": bname, "rows": [
                {"code": x["f12"], "name": x["f14"], "pct": x["f3"], "price": x.get("f2"),
                 "turn": x.get("f8"), "mktcap": x.get("f20"), "mkt": x.get("f13")} for x in rows]}
            time.sleep(1.2)
        else:
            peers[code] = {"board": "", "rows": []}

        secid = ("1." if code.startswith("6") else "0.") + code
        url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=%s&klt=101&fqt=1&lmt=%d"
               "&end=20500101&fields1=f1,f2,f3,f4,f5,f6"
               "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61" % (secid, max(args.bars + 20, 100)))
        d = get(url)
        ks = ((d.get("data") or {}).get("klines") or [])[-args.bars:]
        klines[code] = []
        for row in ks:
            p = row.split(",")
            klines[code].append([p[0], float(p[1]), float(p[2]), float(p[4]), float(p[3]),
                                 round(float(p[5]) / 1e4, 1), float(p[8]), float(p[10])])
        print("[OK] %s %s bars=%d board=%s peers=%d" % (code, ks[-1][:10] if ks else "-", len(ks), bname,
                                                        len(peers[code]["rows"])))
        time.sleep(1.2)

    json.dump(klines, open(os.path.join(args.out, "klines.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(peers, open(os.path.join(args.out, "peers.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("saved ->", args.out)


if __name__ == "__main__":
    main()
