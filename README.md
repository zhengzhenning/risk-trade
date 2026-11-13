# A 股每日看板

采集行情与要闻 → 固化快照 → 按日动态渲染看板。架构见 [docs/00_架构说明.md](docs/00_架构说明.md)，仓库约束见 [AGENTS.md](AGENTS.md)。

```bash
make install   # 安装依赖（含 dev）
make test      # 内核测试 + 依赖方向守卫
make demo      # 生成并渲染一份快照
```

现有可运行入口：`src/a_share_brief/drivers/cli.py`；HTTP/调度驱动按 P2 接入。

文档：[00 架构说明](docs/00_架构说明.md) · [10 详细设计](docs/10_详细设计.md) · [11 代码链路树](docs/11_代码链路树.md) · [20 整体领域设计](docs/20_整体领域设计.md) · [12 前端架构](docs/12_前端架构.md) · [15 项目进度](docs/15_项目进度.md) · [30 业务蓝图](docs/30_业务蓝图.md)
