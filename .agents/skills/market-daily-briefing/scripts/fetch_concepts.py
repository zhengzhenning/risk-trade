#!/usr/bin/env python3
"""标的概念提取：东方财富 F10「核心题材」页数据接口

接口：GET https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code=SZ002242
  - ssbk：所属板块（前3条=行业层级，其后=地域+概念板块，如"题材股/趋势股/钠离子电池"等）
  - hxtc：核心题材要点（KEY_CLASSIF=主营业务/核心竞争力/行业背景/对内扩张… + KEYWORD）

用法：python3 fetch_concepts.py --codes 002242,603928 [--out .]
输出：concepts.json {code: {"industry": [...行业层级], "concepts": [...概念板块], "hxtc": [{kw, cls}]}}
说明：题材归组/概念展示以此接口为准（选股器结果表在部分条件下不返回概念列）。
"""
import argparse, json, os, time, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
URL = "https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code={}"

def mkt(code):
    return ("SH" if code.startswith("6") else "SZ") + code

REGION_WORDS = ("板块",)

def fetch_one(code, retries=1):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(URL.format(mkt(code)),
                                         headers={"User-Agent": UA, "Referer": "https://emweb.securities.eastmoney.com/"})
            d = json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore"))
            ssbk = d.get("ssbk") or []
            names = [b.get("BOARD_NAME", "").strip() for b in ssbk]
            industry = [n for n in names[:3] if n]                       # 前3条=行业层级
            concepts = [n for n in names[3:] if n and not n.endswith("板块")]  # 其后=概念（剔除地域）
            hxtc = [{"kw": it.get("KEYWORD", ""), "cls": it.get("KEY_CLASSIF", "")} for it in (d.get("hxtc") or [])]
            return {"name": (ssbk[0].get("SECURITY_NAME_ABBR") if ssbk else ""), "industry": industry,
                    "concepts": concepts, "hxtc": hxtc}
        except Exception:
            if attempt >= retries:
                raise
            time.sleep(1.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", required=True)
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    path = os.path.join(args.out, "concepts.json")
    out = {}
    if os.path.exists(path):
        # 合并写入：保留已有代码，本次抓取的覆盖同名条目（分批补抓不丢数据）
        out = json.load(open(path))
    for code in filter(None, args.codes.split(",")):
        try:
            out[code] = fetch_one(code)
            c = out[code]
            print("[OK]  %s %s 行业=%s 概念=%s" % (code, c["name"], "/".join(c["industry"]),
                  "、".join(c["concepts"][:6]) or "-"))
        except Exception as e:
            print("[FAIL] %s %s: %s" % (code, type(e).__name__, str(e)[:80]))
        time.sleep(0.4)
    os.makedirs(args.out, exist_ok=True)
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    print("saved ->", path)

if __name__ == "__main__":
    main()
