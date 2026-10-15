# 渠道取数指南（含降级链与浏览器提取片段）

## 渠道总表

| 渠道 | 主路径 | 降级路径 | 官方性 |
|---|---|---|---|
| 东方财富·要闻 | `finance.eastmoney.com/a/czqyw.html` 频道页解析（fetch_news.py） | `np-weblist.eastmoney.com/comm/web/getFastNewsList` 7×24 快讯（无单条 URL） | L2 |
| 财联社·深度头条 | `www.cls.cn/depth?id=1000` **浏览器渲染** | 官方接口签名未破解，勿反复试探；电报走 m 站 SSR（fetch_news.py 内置） | L2 |
| 新浪财经·要闻 | `feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509` roll 接口 | `zhibo.sina.com.cn` 7×24（lid=2509 失效时） | L2 |
| 东财选股器·股池 | `np-tjxg-b.eastmoney.com/api/smart-tag/stock/v3/pw/search-code` **条件直连**（自然语言条件） | 选股器方案页浏览器渲染（见下文兜底片段） | 行情权威源 |

## 已验证的坑（不要再踩）

1. **push2.eastmoney.com 全量分页必封 IP**（本技能 2026-09-29 实测，封禁 >1.5 小时，curl/urllib/WebFetch/真实浏览器全被拒）。行情一律取自选股器结果表，禁止对 push2 分页。
2. 财联社官方接口（`/v1/roll/get_roll_list`、`/nodeapi/updateTelegraphList`）需签名，9 种常见算法变体均失败，签名逆向是遗留待办，**不要在正式流程里反复试探**。
3. 东财 `np-listapi.eastmoney.com` 已空返回，用 `np-weblist` 或频道页。
4. 新浪 `finance.sina.com.cn/topnews/` 页面是空壳，别解析它，直接走 roll 接口。
5. 淘股吧主域已跳 `tgb.cn`，无公开快讯接口，只能拿到活动帖——只作佐证源。

## 财联社深度·头条：浏览器提取片段

用 `browser-use:control-browser` 技能，每次 JS 调用先跑标准 bootstrap，然后：

```js
const browser = await agent.browsers.getForUrl("https://www.cls.cn/depth?id=1000");
const tab = await browser.tabs.new();
await tab.goto("https://www.cls.cn/depth?id=1000");
await tab.playwright.waitForLoadState({ state: "domcontentloaded" });
await tab.playwright.waitForTimeout(3000);
const snap = await tab.playwright.domSnapshot();
```

从 snapshot 中提取：`link "标题"` + `/url: /detail/<id>` + 摘要 + 相对时间（`text: 昨天 22:49` / `28分钟前`）+ `阅N.W`。
**相对时间换算**：`昨天 HH:MM` = 目标日期前一天该时刻；`N分钟前` = 执行时刻减 N 分钟（跨零点注意日期）。头条区置顶条目（房贷贴息群、央行工具等）通常没有时间戳，标注"盘中"。
头条完整链接：`https://www.cls.cn/detail/<id>`。

## 选股器条件直连接口（主路径，已验证可脱离浏览器调用）

**端点**：`POST https://np-tjxg-b.eastmoney.com/api/smart-tag/stock/v3/pw/search-code`（Content-Type: application/json，需 UA + Origin/Referer 指向 xuangu.eastmoney.com；无 cookie 依赖，fingerprint/requestId 可伪造）

**请求体模板**（脚本 `fetch_pool_api.py` 已实现，条件文本是唯一关键变量）：

```json
{
  "needAmbiguousSuggest": true, "pageSize": 50, "pageNo": 1,
  "fingerprint": "<任意32位hex>", "matchWord": "", "shareToGuba": false,
  "timestamp": "<毫秒时间戳>", "requestId": "<任意前缀+时间戳>",
  "removedConditionIdList": [], "allCode": true, "ownSelectAll": false,
  "needCorrect": true, "client": "WEB", "product": "", "needShowStockNum": false,
  "biz": "web_ai_select_stocks", "xcId": "", "gids": [], "dxInfoNew": [],
  "keyWordNew": "<自然语言条件>",
  "customDataNew": "[{\"type\":\"text\",\"value\":\"<同条件>\",\"extra\":\"\"}]"
}
```

**响应结构**：`code=100` 成功；`data.result.columns[]` 为自描述列定义（`title`=中文列名 ↔ `key`=字段名，如 `LIAN_BAN{2026-10-08}`=连板(天)、`JHJJZDF`=集合竞价涨跌幅），`data.result.dataList[]` 每行即 `{key: 值}` 字典——**按 title 映射取值，永远不存在列错位**。`code=201` = 条件空结果（非故障；典型：月初"本月涨幅>20%"但主板单日涨幅上限 10%）。

**条件措辞规范**（已验证）：
- 比例排名："本月涨幅前百分之一"；绝对排名："…前十"（方向一现用"本月涨幅前七"）；历史区间："2026.09.01至2026.09.30区间涨跌幅前十"
- **历史时点重建**（第 3.3 步回补用）："2026.10.01至2026.10.13区间涨跌幅前十"（现回补措辞用"前七"）返回**该时点**的月涨幅排名（002242 当时 41.36% vs 当日 85.43%，已核实）；接口自动把区间收敛到实际交易日（国庆自动跳过），有效起止在原始键 `INTERVAL_CHG{起|止|N|天}`（单日窗口为 `INTERVAL_CHG{日期}`），键经 `fetch_pool_api.query(cond, raw=True)` 的 `rawList` 暴露。**注意：集合竞价列对历史区间查询返回的是最新交易日竞价值（JHJJZDF{今日}），不能当历史当日值——回补条件禁带竞价子句**
- 相对区间："近十日涨幅前三"**原生解析为 10 个交易日区间**（回显字段 `INTERVAL_CHG{2026-09-23|2026-10-14|10|天}`，"近10个交易日"同义；2026-10-14 验证）
- 剔除："不要ST股；不要退市股；不要北交所；不要科创板；不要创业板"（可选"不要新股和次新股"）
- 情绪字段："连板大于等于2"、"换手率大于5%"、"断板"
- **竞价列带出技巧**：条件末尾追加"竞价涨幅大于-11%"可让自适应列带出"集合竞价涨跌幅"（`JHJJZDF{日期}`）——剔创/科/北/ST 后全为主板（涨跌停±10%），该阈值**不构成实际过滤**（实测 total 不变，2026-10-14 验证）
- **禁用**："竞价金额大于0元"会实际过滤掉无竞价成交的标的（实测 total 10→9），不得用于股池条件

**限频**：单方向查询间隔 ≥1s，禁止循环刷条件试探措辞（措辞调试在一次性验证中完成）。

## 选股器方案页：浏览器渲染（兜底路径）

仅当直连接口故障时使用。打开方案页（用户在 UI 保存方案后得到的 URL）：

```js
const browser = await agent.browsers.getForUrl("https://xuangu.eastmoney.com/Result");
const tab = await browser.tabs.new();
await tab.goto("https://xuangu.eastmoney.com/Result?color=w&type=stock&a=edit_way&id=<方案ID>");
await tab.playwright.waitForLoadState({ state: "domcontentloaded" });
await tab.playwright.waitForTimeout(4000);
const data = await tab.playwright.evaluate(`(() => {
  const tables = [...document.querySelectorAll("table")];
  const rowTables = tables.map(tb => [...tb.querySelectorAll("tr")].filter(tr => tr.querySelectorAll("td").length > 1));
  // 从"共 N 只股票"读总数（先 snapshot 确认），下面按 N 对齐两张表
  const N = 29; // ← 替换为实际数量
  const idTable = rowTables.find(rt => rt.length === N && /\\d{6}/.test(rt[0].innerText));
  const metricTable = rowTables.find(rt => rt.length === N && /%/.test(rt[0].innerText) && !/\\d{6}/.test(rt[0].innerText));
  const out = [];
  for (let k = 0; k < N; k++) {
    const id = [...idTable[k].querySelectorAll("td")].map(c => c.innerText.trim());
    const m = [...metricTable[k].querySelectorAll("td")].map(c => c.innerText.replace(/\\s+/g, " ").trim());
    out.push({ seq: id[1], code: id[2], name: id[3],
      px: m[4], day: m[5], month: m[6], board: m[7],
      industry: m[12] || "", concepts: (m[11] || "").slice(0, 40) });
  }
  return out;
})()`);
```

- 页面结构：**两张联动表**——左侧固定表（序号/代码/名称）+ 右侧滚动指标表；按行号 zip。
- 指标表列序（表头已验证）：`[0-3 空] 最新价 今日涨跌幅 本月区间涨跌幅 上市板块 是否ST 退市 新股 概念 东财行业二级 ...`，即 `m[4]=最新价, m[5]=今日涨跌幅, m[6]=本月区间涨跌幅, m[7]=板块, m[11]=概念, m[12]=行业二级`。
- 选股条件会渲染在页面顶部（checkbox 文本），提取时核对一遍与预期口径一致（本月区间、前 1%、剔 ST/退市/次新/北交所/创业板/科创板）。
- 月份切换后方案里的"本月"区间自动滚动，无需改条件。

## 佐证源（不入正文，仅交叉验证）

- 韭研公社：`www.jiuyangongshe.com` 首页 SSR，标题在 `class="book-title..."` 节点，无时间戳/链接。
- 开盘红：`kaipanhong.com/latest-news/1` 静态 HTML，标题带日期后缀。
- 用途示例：某部委政策在东财快讯窗口外发布时，用两者标题互证后标注"待权威源复核"。

## 代理配置

`scripts/proxy_config.json`（可选）：

```json
{ "proxy_static": [], "proxy_api": "", "proxy_ttl": 60 }
```

`proxy_api` 填商业代理的短效提取链接（返回 ip:port 文本）。未配置时直连；当前架构单日请求仅十几次，直连足够，代理是为扩容预留。
