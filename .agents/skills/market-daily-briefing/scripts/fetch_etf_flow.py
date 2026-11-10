#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 申赎与资金流抓取（skill 第 3.55 步）
来源：东财 datacenter（etfKit H5 逆向接口，契约见 references/channel-guide.md）
  - RPT_ETF_NETINFLOW      市场六类历史净流入（1宽基/2行业/3策略/4债基/5黄金/6汇金，一次调用）
  - RPT_ETF_NETINFLOWNEW   行业类（TYPE=2）全量榜单（~810 只 2 页：行业代表与行业类重点快照均出自榜单行，
                           非行业类重点走单只快照兜底）
  - push2his 日 K          重点+行业代表 ETF 收盘价序列（按天趋势右轴）
  - push2 clist            股票型 ETF 规模（f20 总市值；单页上限 100，按规模降序自适应翻页至锁定前 N 组）
行业 ETF 观察池（用户固定清单 WATCH）：科技（半导体/机器人/商业航天/人工智能）、医药（创新药）、
           消费（800消费/酒/传媒/畜牧/游戏）、金融（银行/非银/证券）、有色（有色）。
           每个观察行业按关键词包含匹配跟踪指数组（INDEXNAME），取代表基金规模最大的组，
           组内留规模最大 ETF 一只为该行业代表（如 半导体→科创半导体材料设备组→588170、
           人工智能→CS人工智组→159819、商业航天→卫星通信组→159206、有色→有色金属组→512400）；
           看板按 科技→医药→消费→金融→有色 分组五色呈现，类内按规模倒序；名单固定、代表随规模重算。
产出：
  1) <out>/etf_flow.json            全量（aggregate/funds/industries/raw rank）
  2) <out>/etf_flow_slim.json       看板 ETFFLOW 注入源（紧凑数组，builder 原样嵌入，勿手工编辑）
  3) archives/pool-history/etf-flow.jsonl  重点+行业代表每日净流入历史库（逐日追加，同日覆盖；仅本脚本写入）
口径：净流入=估算（份额变动×净值），T-1 更新（当日盘后发布，盘中快照拿到的是上一交易日值）
调用预算：datacenter ≤7 次/日（aggregate 1＋行业榜单 ~2 页＋单只兜底 ≤4）；push2his ≤40（重点 4＋代表 30）；
          push2 clist ≤12 页（自适应提前终止）。均间隔 ≥0.5s、无全量死循环。
用法：python3 fetch_etf_flow.py --codes 563360,588000,512100,515300 --lookback 120 --out <工作目录>
"""
import argparse, datetime, json, os, sys, time, urllib.parse, urllib.request

DC = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://emrnweb.eastmoney.com/"}
TYPE_NAME = {"1": "宽基", "2": "行业", "3": "策略", "4": "债基", "5": "黄金", "6": "汇金"}
# 行业 ETF 观察清单（用户指定）：(分类, 行业名, 跟踪指数包含匹配关键词)；组内留规模最大代表
WATCH = [
    ("科技", "半导体", ["科创半导体", "半导体"]),
    ("科技", "机器人", ["机器人"]),
    ("科技", "商业航天", ["卫星", "航天"]),
    ("科技", "人工智能", ["人工智"]),
    ("医药", "创新药", ["创新药"]),
    ("消费", "800消费", ["800消费"]),
    ("消费", "酒", ["酒"]),
    ("消费", "传媒", ["传媒"]),
    ("消费", "畜牧", ["畜牧"]),
    ("消费", "游戏", ["游戏"]),
    ("金融", "银行", ["银行"]),
    ("金融", "非银", ["非银"]),
    ("金融", "证券", ["证券"]),
    ("有色", "有色", ["有色"]),
]
# 分组五色：科技=蓝 医药=青绿 消费=紫 金融=金 有色=金属灰；展示顺序即列表顺序
CATS = {"科技": "#3b66d4", "医药": "#0e9f9f", "消费": "#8b5cf6", "金融": "#d97706", "有色": "#64748b"}
# 榜单完整列（页面原样，缺列会报"返回字段不存在"，勿增删）
RANK_COLS = ("SECUCODE,SECURITY_CODE,SECURITY_INNER_CODE,SECURITY_NAME_ABBR,PERIODESTIMATENETINFLOW1,"
             "PERIODESTIMATENETINFLOW5,PERIODESTIMATENETINFLOW20,PERIODESTIMATENETINFLOW60,TRADE_DATE,"
             "TVALCNY,CHG,SECURITY_TYPE_NAME,DERIVE_INDEX_CODE,INDEXNAME,DEC_BIANHUARATE1,DEC_BIANHUARATE5,"
             "DEC_BIANHUARATE20,DEC_BIANHUARATE60,PCTCHANGE1,PCTCHANGE5,PCTCHANGE20,PCTCHANGE60,"
             "TYPE,QUOTES_MARKET_CODE")
FUND_COLS = ("SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,PERIODESTIMATENETINFLOW1,"
             "PERIODESTIMATENETINFLOW5,PERIODESTIMATENETINFLOW20,PERIODESTIMATENETINFLOW60,"
             "DEC_BIANHUARATE5,DEC_BIANHUARATE20,TVALCNY,PCTCHANGE5,INDEXNAME,TRADE_DATE")
# push2 clist 股票型 ETF 板块（债/货币类 ETF 不在其中）
CLIST_FS = "b:MK0021,b:MK0022,b:MK0023,b:MK0024"


def secu(code):
    return f"{code}.{'SH' if code.startswith('5') else 'SZ'}"


def get(params, base=DC, headers=UA):
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if not d.get("success"):
        raise RuntimeError(f"datacenter fail: {d.get('message')} ({d.get('code')})")
    return (d.get("result") or {}).get("data") or []


def fetch_aggregate(end, start):
    rows = get({
        "reportName": "RPT_ETF_NETINFLOW",
        "columns": "SECURITY_TYPE,TYPE,TRADE_DATE,PERIODESTIMATENETINFLOW1,PERIODESTIMATENETINFLOW60,CORR_IDX,CM_CLOSE",
        "quoteColumns": "",
        "filter": f"(TRADE_DATE<='{end}')(TRADE_DATE>='{start}')",
        "pageNumber": 1, "pageSize": 2000,
        "sortTypes": "1,1", "sortColumns": "TRADE_DATE,TYPE",
        "source": "SECURITIES", "client": "APP",
    })
    by_type = {}
    for r in rows:
        t = str(r["TYPE"])
        by_type.setdefault(t, []).append({
            "d": r["TRADE_DATE"][:10],
            "netIn": round(r["PERIODESTIMATENETINFLOW1"] / 1e8, 1),
            "cum60": round(r["PERIODESTIMATENETINFLOW60"] / 1e8, 1),
            "idxClose": round(r["CM_CLOSE"], 2),
        })
    return by_type


def fetch_rank(t):
    """单类全量榜单（pageSize 上限 500，翻页到齐；行业类 ~810 只需 2 页）"""
    rows, page = [], 1
    while True:
        batch = get({
            "reportName": "RPT_ETF_NETINFLOWNEW", "columns": RANK_COLS, "quoteColumns": "",
            "filter": f'(TYPE="{t}")', "pageNumber": page, "pageSize": 500,
            "sortTypes": "-1,1", "sortColumns": "PERIODESTIMATENETINFLOW1,SECURITY_CODE",
            "source": "SECURITIES", "client": "APP",
        })
        rows += batch
        if len(batch) < 500 or len(rows) >= 3000:
            return rows
        page += 1
        time.sleep(1.0)


def fund_from_rank(r):
    def g(k, nd=1):
        v = r.get(k)
        return round(v, nd) if isinstance(v, (int, float)) else None
    def e8(k, nd=1):
        v = r.get(k)
        return round(v / 1e8, nd) if isinstance(v, (int, float)) else None
    return {
        "secuCode": r["SECUCODE"], "code": str(r["SECURITY_CODE"]), "name": r["SECURITY_NAME_ABBR"],
        "asOf": r["TRADE_DATE"][:10],
        "netIn1": e8("PERIODESTIMATENETINFLOW1"), "netIn5": e8("PERIODESTIMATENETINFLOW5"),
        "netIn20": e8("PERIODESTIMATENETINFLOW20"), "netIn60": e8("PERIODESTIMATENETINFLOW60"),
        "shareChg5": g("DEC_BIANHUARATE5", 2), "shareChg20": g("DEC_BIANHUARATE20", 2),
        "amt": e8("TVALCNY"), "pct5": g("PCTCHANGE5", 2), "trackIdx": r.get("INDEXNAME"),
    }


def fetch_fund(code):
    rows = get({
        "reportName": "RPT_ETF_NETINFLOWNEW", "columns": FUND_COLS, "quoteColumns": "",
        "filter": f'(SECUCODE="{secu(code)}")',
        "pageNumber": 1, "pageSize": 5,
        "sortTypes": "-1", "sortColumns": "TRADE_DATE",
        "source": "SECURITIES", "client": "APP",
    })
    if not rows:
        raise RuntimeError(f"{code}: empty snapshot")
    return fund_from_rank(rows[0])


def fetch_kline(code, lmt):
    secid = ("1." if code.startswith("5") else "0.") + code
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=" + secid +
           "&klt=101&fqt=1&lmt=" + str(lmt) + "&end=20500101&fields1=f1,f2,f3&fields2=f51,f53")
    req = urllib.request.Request(url, headers={"Referer": "https://quote.eastmoney.com/",
                                               "User-Agent": "Mozilla/5.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read())["data"]
    return [[ln.split(",")[0], round(float(ln.split(",")[1]), 3)] for ln in d["klines"]]


def clist_page(pn):
    """push2 clist 一页股票型 ETF 规模（亿元），fid=f20 降序（实测单页上限 100）"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=%d&pz=100&po=1&np=1&fltt=2&invt=2" % pn
           + "&fid=f20&fs=" + urllib.parse.quote(CLIST_FS) + "&fields=f12,f13,f14,f20")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Referer": "https://quote.eastmoney.com/"})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    diff = ((d.get("data") or {}).get("diff")) or []
    return [(str(x["f12"]), round((x.get("f20") or 0) / 1e8, 1)) for x in diff]


def pick_industry_reps(rank_rows, max_pages=12):
    """观察清单 WATCH：按关键词包含匹配跟踪指数组 → 取代表规模最大的组 → 组内留规模最大 ETF。
    规模来源 clist（f20 降序）：自适应翻页——当全部观察行业的代表规模都 ≥ 当前页最小值时，
    后续页不可能改变任何选择（整榜降序），即终止。"""
    groups = {}
    for r in rank_rows:
        idx = r.get("DERIVE_INDEX_CODE") or r.get("INDEXNAME") or r["SECURITY_CODE"]
        groups.setdefault(idx, []).append(r)
    gname = {idx: (lst[0].get("INDEXNAME") or idx) for idx, lst in groups.items()}
    scale = {}

    def pick_watch():
        """每个观察行业 -> (代表规模, 组idx)；无匹配组返回 None"""
        out = []
        for cat, wname, keys in WATCH:
            cands = [i for i in groups if any(k in gname[i] for k in keys)]
            if not cands:
                out.append((cat, wname, None, None))
                continue
            best_idx, best_sc = None, -1
            for i in cands:
                top = max(groups[i], key=lambda r: scale.get(str(r["SECURITY_CODE"]), 0))
                sc = scale.get(str(top["SECURITY_CODE"]), 0)
                if sc > best_sc:
                    best_idx, best_sc = i, sc
            top = max(groups[best_idx], key=lambda r: scale.get(str(r["SECURITY_CODE"]), 0))
            out.append((cat, wname, best_sc, (best_idx, top)))
        return out

    pages = 0
    for pn in range(1, max_pages + 1):
        page = clist_page(pn)
        pages = pn
        if not page:
            break
        for c, s in page:
            scale[c] = s
        if len(page) < 100:
            break
        picks = pick_watch()
        min_rep = min((sc for _, _, sc, _ in picks if sc is not None), default=0)
        if all(sc is not None for _, _, sc, _ in picks) and min_rep >= page[-1][1]:
            print(f"[OK] clist 第 {pn} 页后锁定观察清单（最小代表规模 {min_rep} 亿 ≥ 本页最小 {page[-1][1]} 亿，共 {len(groups)} 组）")
            break
        time.sleep(0.6)
    order = {c: i for i, c in enumerate(CATS)}
    picks = sorted(pick_watch(), key=lambda x: (order[x[0]], -(x[2] or 0)))
    inds = []
    for cat, wname, sc, sel in picks:
        if sel is None:
            print(f"[WARN] {cat}｜{wname}：无匹配跟踪指数组，跳过")
            continue
        idx, top = sel
        lst = sorted(groups[idx], key=lambda x: -scale.get(str(x["SECURITY_CODE"]), 0))
        top3 = [{"code": str(x["SECURITY_CODE"]), "name": x["SECURITY_NAME_ABBR"],
                 "scale": scale.get(str(x["SECURITY_CODE"]), 0)} for x in lst[:3]]
        inds.append({"cat": cat, "idx": wname, "gidx": gname[idx],
                     "fund": dict(fund_from_rank(top), scale=sc), "top": top3})
        print(f"[IND] {cat}｜{wname}（{gname[idx]}）-> {top['SECURITY_CODE']} {top['SECURITY_NAME_ABBR']} "
              f"规模 {sc} 亿（组内 {len(lst)} 只）")
    cnt = {c: sum(1 for i in inds if i["cat"] == c) for c in CATS if any(i["cat"] == c for i in inds)}
    print(f"[KING] 观察清单行业代表 {len(inds)} 只（{' · '.join(f'{c}{n}' for c, n in cnt.items())}；"
          f"{pages} 页 clist，覆盖规模 {len(scale)} 只）")
    return inds, scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", default="563360,588000,512100,515300")
    ap.add_argument("--lookback", type=int, default=120)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
    args = ap.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    os.makedirs(args.out, exist_ok=True)

    today = datetime.date.today()
    start = (today - datetime.timedelta(days=int(args.lookback * 1.55) + 15)).isoformat()
    end = today.isoformat()

    by_type = fetch_aggregate(end, start)
    total = sum(len(v) for v in by_type.values())
    assert total < 1900, f"aggregate rows {total} 接近 pageSize 上限，存在截断风险"
    print(f"[OK] aggregate 六类 -> {sorted(by_type)} 日数:" +
          ",".join(f"{TYPE_NAME.get(t, t)}:{len(by_type[t])}" for t in sorted(by_type)))
    as_of = max((v[-1]["d"] for v in by_type.values() if v), default=None)

    # 行业榜单 → 行业代表（每跟踪指数一只规模最大）
    rank2 = fetch_rank("2")
    flat = {str(r["SECURITY_CODE"]): r for r in rank2}
    print(f"[OK] 榜单 行业 {len(rank2)} 只")
    inds, scale = pick_industry_reps(rank2)

    # 重点 funds：优先行业榜单行，非行业类走单只兜底；代表+重点 K 线
    funds = []
    for i, c in enumerate(codes):
        f = fund_from_rank(flat[c]) if c in flat else None
        if f is None:
            if i:
                time.sleep(1.0)
            f = fetch_fund(c)
            print(f"[FALLBACK] {c} 非行业榜单，单只快照兜底")
        funds.append(f)
    kcodes = list(dict.fromkeys([f["code"] for f in funds] + [d["fund"]["code"] for d in inds]))
    kmap = {}
    for i, c in enumerate(kcodes):
        if i:
            time.sleep(0.5)
        kmap[c] = fetch_kline(c, args.lookback + 20)
    for f in funds:
        f["k"] = kmap[f["code"]]
        print(f"[OK] {f['code']} {f['name']} @{f['asOf']} d1={f['netIn1']}亿 成交额={f['amt']}亿 K线{len(f['k'])}日")
    for d in inds:
        d["fund"]["k"] = kmap[d["fund"]["code"]]

    # 本地历史库：重点+行业代表 的每日净流入（T-1）
    hist_path = os.path.join(args.repo_root, "archives", "pool-history", "etf-flow.jsonl")
    os.makedirs(os.path.dirname(hist_path), exist_ok=True)
    lines = {}
    if os.path.exists(hist_path):
        for ln in open(hist_path, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                obj = json.loads(ln)
                lines[obj["date"]] = obj
    tracked = list(dict.fromkeys([f["code"] for f in funds] + [d["fund"]["code"] for d in inds]))
    row = {"date": as_of, "funds": {}}
    fmap = {f["code"]: f["netIn1"] for f in funds}
    for d in inds:
        fmap.setdefault(d["fund"]["code"], d["fund"]["netIn1"])
    prev = lines.get(as_of, {}).get("funds", {})
    row["funds"] = {c: fmap.get(c, prev.get(c)) for c in set(tracked) | set(prev)}
    lines[as_of] = row
    with open(hist_path, "w", encoding="utf-8") as fp:
        for d in sorted(lines):
            fp.write(json.dumps(lines[d], ensure_ascii=False) + "\n")
    print(f"[OK] 历史库 {hist_path}（累计 {len(lines)} 日，跟踪 {len(tracked)} 只）")

    out = {
        "fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asOf": as_of, "types": TYPE_NAME,
        "aggregate": {t: by_type[t] for t in sorted(by_type)},
        "funds": funds, "industries": inds, "rank": rank2,
        "history": {c: [{"d": d, "netIn": v.get("funds", {}).get(c)}
                        for d, v in sorted(lines.items())] for c in tracked},
    }
    p = os.path.join(args.out, "etf_flow.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[done] -> {p}")

    slim = {
        "asOf": as_of, "types": TYPE_NAME,
        "series": {t: [[r["d"], r["netIn"], r["cum60"], r["idxClose"]] for r in by_type[t]]
                   for t in sorted(by_type)},
        "funds": funds,
        "industries": [{"cat": d["cat"], "idx": d["idx"], "gidx": d["gidx"], "fund": d["fund"], "top": d["top"]} for d in inds],
        "history": {c: [[x["d"], x["netIn"]] for x in out["history"][c][-120:]] for c in out["history"]},
    }
    ps = os.path.join(args.out, "etf_flow_slim.json")
    json.dump(slim, open(ps, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[done] -> {ps}（六类 %d 日次，行业代表 %d 只）" % (sum(len(v) for v in slim["series"].values()), len(inds)))


if __name__ == "__main__":
    main()
