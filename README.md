# A 股每日看板

采集行情与要闻 → 固化快照 → 按日动态渲染看板。架构见 [docs/00_架构说明.md](docs/00_架构说明.md)，仓库约束见 [AGENTS.md](AGENTS.md)。

```bash
./restart.sh          # 一键重启：API(8000) + 快照循环，并做健康检查
./restart.sh status   # 只看状态
./restart.sh stop     # 停止服务
```

```bash
make install   # 安装依赖（含 dev）
make test      # 内核测试 + 依赖方向守卫
make demo      # 生成并渲染一份快照
```

现有可运行入口：`src/a_share_brief/drivers/cli.py`；HTTP/调度驱动按 P2 接入。

文档：[00 架构说明](docs/00_架构说明.md) · [10 详细设计](docs/10_详细设计.md) · [11 代码链路树](docs/11_代码链路树.md) · [20 整体领域设计](docs/20_整体领域设计.md) · [12 前端架构](docs/12_前端架构.md) · [15 项目进度](docs/15_项目进度.md) · [30 业务蓝图](docs/30_业务蓝图.md)

## 目录结构

```text
risk-trade/
├── src/a_share_brief/
│   ├── domain/                  领域层：无 IO 的聚合与纯规则
│   │   ├── aggregates/          Briefing / Stock / Index / PoolRanking / Theme
│   │   └── services/            pool、theme_cluster、wyckoff、trading_calendar 等
│   ├── application/             应用层：用例与端口
│   │   ├── ports.py             端口定义（行情/股池/指数/预警/题材/K线）
│   │   ├── usecases/            build_snapshot、build_view
│   │   └── tasks/               定时任务用例：quotes、indexes、pool、alert、theme
│   ├── infrastructure/          基础设施层：协议转换与存储
│   │   ├── eastmoney*.py        东财行情、股池、指数、预警、题材、板块、K线
│   │   ├── tencent*.py          腾讯行情与 K 线（直连兜底）
│   │   ├── qingguo_proxy.py     青果代理池：120 秒租约复用
│   │   ├── proxy_client.py      代理请求：退避、换 IP、网页降级
│   │   ├── sections.py          分片存储（带 captured_at）
│   │   └── file_repo.py         快照读写
│   └── interfaces/              接口层：入口与装配
│       ├── api.py               FastAPI 应用工厂
│       ├── api_*.py             board、行情、个股、辅助接口
│       ├── tasks.py             定时任务调度（各业务独立频率）
│       ├── scheduler.py         通用作业执行器（Job/Scheduler）
│       ├── composition.py       组合根：唯一装配依赖处
│       └── board_*.py           看板渲染：数据块、矩阵、指数、威科夫
├── config/
│   ├── settings.example.json    配置模板（代理 switch 与密钥占位）
│   └── settings.json            本地配置（含密钥，不入库）
├── work/
│   ├── store/                   按日快照 briefing-YYYY-MM-DD.json
│   ├── sections/                任务分片 quotes/index/pool/alert/theme.json
│   └── cache/                   威科夫按日缓存
├── archives/                    历史看板 HTML
├── docs/                        架构、设计、编码规约、任务拆分
├── tests/                       用例测试与分层守卫
├── restart.sh                   一键重启脚本
└── Makefile                     serve / live / test / lint / proxy-stats
```
