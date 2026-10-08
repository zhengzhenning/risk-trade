#!/usr/bin/env python3
"""三渠道要闻采集：东方财富要闻频道 + 新浪财经要闻 + 财联社电报(m站SSR)

用法：python3 fetch_news.py [--date YYYY-MM-DD] [--pages 8] [--out DIR]
产出：DIR/news.json，每条含 {time, title, url, source}；日期过滤基于各源时间字段。
代理：同级 proxy_config.json 存在且配置了代理时自动启用 proxy_pool。
"""
import argparse, datetime, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from proxy_pool import ProxyPool, fetch_with_pool  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"

# ---------- 工具 ----------

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

def fmt_ts(ts, date):
    """epoch → 'MM-DD HH:MM'；无法解析返回空。调用方按目标日期前缀过滤。"""
    try:
        return datetime.datetime.fromtimestamp(int(float(ts))).strftime("%m-%d %H:%M")
    except Exception:
        return ""

def in_date(t, date):
    return t.startswith(date[5:7] + "-" + date[8:10])

# ---------- 渠道 1：东方财富要闻频道页（文章 URL 内含日期） ----------

def fetch_eastmoney(pool, date):
    html = fetch_with_pool("https://finance.eastmoney.com/a/czqyw.html", pool,
                           headers={"Referer": "https://finance.eastmoney.com/"})
    blocks = re.findall(
        r'href="(https?://finance\.eastmoney\.com/a/(\d{18})\.html)"[^>]*>(.{0,200}?)</a>',
        html, re.S)
    seen, items = set(), []
    for url, art_id, inner in blocks:
        title = strip_html(re.sub(r"<[^>]+>", " ", inner))
        if len(title) < 8 or url in seen:
            continue
        seen.add(url)
        d = f"{art_id[0:4]}-{art_id[4:6]}-{art_id[6:8]}"
        if d != date:
            continue
        items.append({"time": d, "title": title, "url": url, "source": "东方财富"})
    return items

# ---------- 渠道 2：新浪财经要闻（roll 接口，分页回溯覆盖全日） ----------

def fetch_sina(pool, date, pages):
    seen, items = {}, []
    for page in range(1, pages + 1):
        url = (f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=50&page={page}")
        d = json.loads(fetch_with_pool(url, pool, headers={"Referer": "https://finance.sina.com.cn/"}))
        lst = (d.get("result") or {}).get("data") or []
        if not lst:
            break
        oldest = ""
        for it in lst:
            t = fmt_ts(it.get("ctime"), date)
            oldest = min(oldest or t, t)
            key = it.get("url") or it.get("title")
            if key and key not in seen and in_date(t, date):
                seen[key] = True
                items.append({"time": t, "title": strip_html(it.get("title", "")),
                              "url": it.get("url", ""), "source": "新浪财经"})
        # 已回溯到目标日期 00:00 之前则停
        if oldest and oldest < date[5:7] + "-" + date[8:10] + " 00:00":
            break
        time.sleep(0.5)
    items.sort(key=lambda x: x["time"], reverse=True)
    return items

# ---------- 渠道 3：财联社电报（m 站 SSR 内嵌 roll_data；深度头条走浏览器，见 channel-guide.md） ----------

def extract_json_array(html, key):
    i = html.find('"%s":' % key)
    j = html.index("[", i)
    depth, in_str, esc = 0, False, False
    for k in range(j, len(html)):
        c = html[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return json.loads(html[j:k + 1])
    raise RuntimeError("unbalanced json array")

def fetch_cls(pool, date):
    html = fetch_with_pool("https://m.cls.cn/telegraph", pool,
                           headers={"Referer": "https://m.cls.cn/telegraph"})
    items = []
    for it in extract_json_array(html, "roll_data"):
        if not isinstance(it, dict):
            continue
        title = strip_html(it.get("title") or "") or strip_html(it.get("content"))[:60]
        if not title:
            continue
        t = fmt_ts(it.get("ctime") or it.get("modified_time"), date)
        if not in_date(t, date):
            continue
        items.append({"time": t, "title": title[:120],
                      "url": "https://www.cls.cn/detail/%s" % it.get("id"), "source": "财联社"})
    return items

# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y-%m-%d"))
    ap.add_argument("--pages", type=int, default=8, help="新浪回溯页数，每页50条")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()

    pool = ProxyPool.load(os.path.join(HERE, "proxy_config.json"))
    result = {"date": args.date, "run_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "proxy_enabled": pool.is_enabled(), "channels": {}}
    for name, fn in [("eastmoney", lambda: fetch_eastmoney(pool, args.date)),
                     ("sina", lambda: fetch_sina(pool, args.date, args.pages)),
                     ("cls_telegraph", lambda: fetch_cls(pool, args.date))]:
        try:
            items = fn()
            result["channels"][name] = {"ok": True, "count": len(items), "items": items}
            print("[OK]   %-14s %3d 条" % (name, len(items)), flush=True)
        except Exception as e:
            result["channels"][name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, e), "items": []}
            print("[FAIL] %-14s %s: %s" % (name, type(e).__name__, str(e)[:120]), flush=True)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "news.json")
    json.dump(result, open(path, "w"), ensure_ascii=False, indent=1)
    print("saved ->", path)

if __name__ == "__main__":
    main()
