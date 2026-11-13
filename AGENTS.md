# AGENTS.md

A 股每日看板：采集 → 固化快照 → 按日动态渲染。本文件是仓库级约束，与全局 `~/.dsh/AGENTS.md` 冲突时以全局危险操作与 Git 条款为准。

## 一、架构

风格：整洁架构 + 端口适配器 + DDD 轻量聚合，形态为模块化单体。详见 `docs/00_架构说明.md`。

```text
interfaces → application → domain ← infrastructure
```

| 层 | 允许依赖 | 禁止 | 职责 |
| --- | --- | --- | --- |
| `domain/` | 标准库 | 其他层、IO、日志 | 聚合不变量与纯规则 |
| `application/` | `domain` | `infrastructure`、`interfaces` | 用例编排、定义端口 |
| `infrastructure/` | `domain`、`application.ports` | `interfaces` | 协议转换与持久化 |
| `interfaces/` | `application`、`infrastructure` | — | 解析参数、组装依赖 |

规则：

1. 端口定义在 `application/ports.py`，实现放 `infrastructure/`。
2. 第三方字段（`f43`、`lbc` 等）只允许出现在 `infrastructure/`。
3. 领域服务是纯函数，不写 IO、不读配置、不打日志。
4. 聚合根自持不变量，校验写在 `__post_init__` 或聚合方法内。
5. 新增依赖前先判断是否可落到已有端口；不可则新增端口，禁止跨层直连。

## 二、代码规范

细则见 [13_后端编码规约](docs/13_后端编码规约.md) 与 [14_前端编码规约](docs/14_前端编码规约.md)；本节为硬性底线。

- 单文件上限：普通 160 行、`domain/services` 120 行；超限即拆包。
- 公共类与方法必须多行 docstring，含 Args/Returns/Raises。
- 命名用业务术语，禁止 `data`、`info`、`result` 这类无含义名称。
- 日志只记关键业务结果与失败原因，字段用 `day/codes/reason` 等可检索键。
- 异常：适配器吞掉单条失败并跳过；用例失败上抛，由入口层记录。
- 不使用 `print`；入口层用 `logging`。
- 时间统一 `datetime.date`，字符串只出现在存储与渲染边界。

## 三、测试与守卫

```bash
make test   # 用例 + 领域 + 分层守卫
make lint   # ruff（python3 -m ruff，无需全局安装）
make demo   # 生成并渲染一份快照
```

必须通过：

1. `tests/test_architecture.py`：依赖方向、文件规模、领域纯净。
2. 用例测试只用 Fake 端口，不触网、不落盘。
3. 新增聚合或规则必须补对应测试。

## 四、前端

- 目录 `web/`，pnpm workspace：`apps/{h5,miniapp,app}` + `packages/{core,api,charts,ui,design}`。
- `packages/core` 零框架依赖；页面只组装，不拼接口字段。
- 多端单位用 `toUnit()`，断点用 `columnsOf()`，触控行高 ≥44px。
- 实时统一走 `createRealtime()`：H5 用 SSE，小程序/APP 用 WebSocket。
- 类型由 `packages/core/src/types.ts` 对齐后端契约，字段为 `snake_case`。

## 五、文档

- 命名 `层级+顺序_中文名.md`：`00_` 顶层、`10_/11_` 设计与分析、`20_` 整体领域、`30_` 业务蓝图。
- 业务模块放 `docs/business/<编号>_<业务名>/`，每模块两份：`领域设计.md`、`详细设计.md`。
- 文档只写事实；未落地内容标「拟定」，缺失依据标「待确认」。
- 改动架构或分层时，同步更新 `00_架构说明.md` 与 `11_代码链路树.md`。

## 六、Git

1. 任何写操作前先 `git branch --show-current`。
2. `main`、`stable/*` 禁止写入；`test/*` 需单独确认。
3. 提交前说明文件清单与提交信息，等待用户明确指令后再 commit。
4. 未经明确指令不得 push、force push、rebase 改写历史。
5. 不提交与本任务无关的文件。
