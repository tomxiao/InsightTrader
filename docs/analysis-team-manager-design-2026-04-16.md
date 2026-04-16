# Analysis Team Manager 设计草案（2026-04-16）

## 1. 背景

当前系统里，`TradingAgents` 分析编排、阶段报告产出、reply agent 的读取逻辑，实际上是通过“默认约定”耦合在一起的。

现状下这套约定大致是：

- 使用一条默认的完整分析编排
- 输出固定的阶段章节报告
- reply agent 默认按这套章节结构读取内容并回答追问

这套方式在只有一条主编排时可以工作，但一旦我们要引入新的轻量编排，就会出现明显问题：

- 新编排输出的章节结构可能与老编排不同
- 当前 reply agent 仍然依赖老编排产出的阶段报告
- 前端任务状态和阶段展示也默认绑定老阶段定义
- 如果不做抽象，后续会在多个模块里散落大量 `if full / if lite` 逻辑

因此，建议引入一个统一的 `Analysis Team Manager`，作为“分析团队规格管理层”，把以下内容成组绑定：

- 分析 agents 与其编排方式
- 阶段定义
- 报告契约
- reply agent

---

## 2. 设计目标

### 2.1 目标

- 支持多套分析团队并存，例如 `full team` 和 `lite team`
- 明确“这次分析任务属于哪一套 team”
- 明确每套 team 的：
  - analysis orchestrator
  - analysis agent set
  - report contract
  - reply agent
  - stage contract
- 降低新增编排时对现有 reply agent 和前端状态体系的破坏

### 2.2 非目标

- 这次设计不要求立刻重构所有现有 agent prompt
- 不要求将 graph 持久化或可视化管理
- 不要求一次性支持无限多 team 类型

---

## 3. 核心思路

把“分析任务”提升为一个显式的 `team` 概念。

也就是说，未来每次分析任务不只是：

- ticker
- trade_date
- selected_analysts

而是还要明确：

- `team_id`

例如：

- `team_id = "full"`
- `team_id = "lite"`

系统拿到 `team_id` 后，就能统一决定：

- 由哪些分析 agents 参与报告生成
- 用哪条 analysis graph
- 输出哪些报告章节
- 阶段状态怎么映射
- 追问时由哪个 reply agent 消费报告

---

## 4. 建议的数据模型

建议引入一个统一的 Team Spec 结构。

示意：

```python
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class AnalysisTeamSpec:
    team_id: str
    display_name: str
    analysis_orchestrator_factory: Callable
    analysis_agent_ids: tuple[str, ...]
    report_contract: "ReportContract"
    reply_agent_spec: "ReplyAgentSpec"
    stage_contract: "StageContract"
```

### 4.1 `team_id`

唯一标识一套分析团队，例如：

- `full`
- `lite`

### 4.2 `analysis_orchestrator_factory`

负责创建本 team 对应的分析编排。

例如：

- `full` team -> 当前完整 `TradingAgentsGraph`
- `lite` team -> 新的轻量 `LiteTradingGraph`

### 4.3 `analysis_agent_ids`

定义本 team 里参与生成分析报告的 agent 集合。

例如：

- `full` team -> `Market Analyst / Social Analyst / News Analyst / Fundamentals Analyst / Bull Researcher / Bear Researcher / Research Manager / Trader / Aggressive Analyst / Conservative Analyst / Neutral Analyst / Portfolio Manager`
- `lite` team -> `Market Analyst / News Analyst / Fundamentals Analyst / Decision Manager`

### 4.4 `report_contract`

定义本 team 的报告输出结构，包括：

- section key
- 落盘路径
- 哪些 section 是必需的
- 哪些 section 用于 reply agent 读取

### 4.5 `reply_agent_spec`

定义本 team 的 reply agent 规格，包括：

- 使用哪个 report loader
- 使用哪个 reply agent
- 使用哪套 prompt 组织方式
- 缺失 section 时如何降级

### 4.6 `stage_contract`

定义本 team 的阶段体系，包括：

- 支持哪些 `stage_id`
- 对应文案
- 对前端暴露的阶段映射

---

## 5. Team Registry

建议用注册表统一管理所有 team。

示意：

```python
TEAM_REGISTRY = {
    "full": FULL_TEAM_SPEC,
    "lite": LITE_TEAM_SPEC,
}
```

并提供一个统一入口：

```python
def get_team_spec(team_id: str) -> AnalysisTeamSpec:
    try:
        return TEAM_REGISTRY[team_id]
    except KeyError:
        raise ValueError(f"Unknown analysis team: {team_id}")
```

这样系统其余模块不需要知道“full/lite 的具体差异”，只需要依赖 team spec。

---

## 6. 建议先定义的两套 Team

### 6.1 Full Team

用于兼容现有完整编排。

#### 编排

- 使用当前 `TradingAgentsGraph`

#### 基础 analyst

- `market`
- `social`
- `news`
- `fundamentals`

#### 后续角色

- `Bull Researcher`
- `Bear Researcher`
- `Research Manager`
- `Trader`
- `Aggressive Analyst`
- `Conservative Analyst`
- `Neutral Analyst`
- `Portfolio Manager`

#### 报告 contract

建议维持当前结构：

- `1_analysts/market.md`
- `1_analysts/sentiment.md`
- `1_analysts/news.md`
- `1_analysts/fundamentals.md`
- `2_research/bull.md`
- `2_research/bear.md`
- `2_research/manager.md`
- `3_trading/trader.md`
- `4_risk/aggressive.md`
- `4_risk/conservative.md`
- `4_risk/neutral.md`
- `5_portfolio/decision.md`

#### reply agent

- 继续兼容当前 reply agent 读取模式

#### stage contract

- 继续使用当前：
  - `analysts.market`
  - `analysts.social`
  - `analysts.news`
  - `analysts.fundamentals`
  - `research.debate`
  - `trader.plan`
  - `risk.debate`
  - `portfolio.decision`

### 6.2 Lite Team

用于支持低时延分析。

#### 编排

建议新增一条轻量 graph，例如：

- `Market Analyst`
- `News Analyst`
- `Fundamentals Analyst`
- `Decision Manager`

说明：

- 默认不跑 `Social Analyst`
- 默认不跑 `Bull/Bear/Research/Trader/Risk` 链路
- 最终节点建议不要直接复用当前 `Portfolio Manager`，而是定义一个更适合 lite 输入的 `Decision Manager`

#### 报告 contract

建议单独定义，不强行复用 full team 的章节结构。

例如：

- `1_analysts/market.md`
- `1_analysts/news.md`
- `1_analysts/fundamentals.md`
- `2_decision/summary.md`

可选扩展：

- `2_decision/key_risks.md`
- `2_decision/key_catalysts.md`

#### reply agent

不建议直接假设所有 full team 章节存在。

建议：

- 使用兼容 lite contract 的 report loader
- 优先基于：
  - analyst 三份报告
  - decision summary
- 若用户追问深度超出 lite 能力边界，可提示补跑 full 分析

#### stage contract

建议独立定义，例如：

- `analysts.market`
- `analysts.news`
- `analysts.fundamentals`
- `decision.finalize`

---

## 7. Report Contract 设计建议

建议把 report contract 独立成显式结构，而不是让 reply agent 直接硬编码路径。

示意：

```python
@dataclass(frozen=True)
class ReportSectionSpec:
    key: str
    path: str
    required: bool = False
    reply_visible: bool = True


@dataclass(frozen=True)
class ReportContract:
    sections: tuple[ReportSectionSpec, ...]
    primary_summary_key: str
```

### 7.1 Full Team 的 Report Contract

包含所有当前阶段章节。

### 7.2 Lite Team 的 Report Contract

只包含轻量编排实际会产出的章节。

### 7.3 设计原则

- reply agent 不应直接假设某路径一定存在
- 统一通过 `report_contract` 获取“本 team 有哪些 section”
- section 缺失时按 contract 决定是否允许降级

---

## 8. Reply Agent 设计建议

关键结论：

- 当前 reply agent 依赖老编排输出的阶段报告
- 因此不能继续让它“默认按 full report contract 读取”
- 如果未来长期并存 `full / lite` 两套报告结构，reply 层也应该拆成两套独立实现

因此，建议在引入 `reply agent spec` 抽象的同时，明确拆分成两个 reply agent。

示意：

```python
@dataclass(frozen=True)
class ReplyAgentSpec:
    agent_id: str
    report_loader_factory: Callable
    prompt_builder: Callable
    reply_agent_factory: Callable
```

### 8.1 第一阶段建议

- 保留统一的 reply 入口，但内部按 `team_id` 分发到不同 reply agent
- `full` team 使用 `full reply agent`
- `lite` team 使用 `lite reply agent`
- 每个 reply agent 各自绑定：
  - report loader
  - section 集合
  - prompt 组织方式

### 8.2 后续再决定是否拆成两个 reply agent

这一点不再建议暂缓。

后续真正需要再评估的是：

- 两个 reply agent 是否共用同一套基础 loader 抽象
- 两个 reply agent 是否需要不同的产品表现层和文案风格

---

## 9. Stage Contract 设计建议

当前阶段体系默认服务 full graph。

如果未来引入 lite graph，建议不要继续强行复用 full graph 的所有 stage。

建议定义：

```python
@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    label: str
    stage_group: str


@dataclass(frozen=True)
class StageContract:
    stages: tuple[StageSpec, ...]
```

### 9.1 Full Team

沿用现有 stage。

### 9.2 Lite Team

定义精简 stage，避免前端显示不存在的阶段。

---

## 10. 与 ta_service 的接入方式

建议 `ta_service` 按以下方式接入。

### 10.1 Analysis Task 新增 `teamId`

当前任务模型里建议新增字段：

- `teamId`

默认值建议：

- `full`

### 10.2 Analysis Service 在建任务时确定 team

例如：

- 默认创建 `full`
- 未来根据入口、用户选择、产品策略创建 `lite`

### 10.3 Worker 运行时通过 Team Manager 取 spec

当前 `TradingAgentsRunner` 直接创建 `TradingAgentsGraph`。

建议改为：

1. 读取 `teamId`
2. `get_team_spec(teamId)`
3. 调用对应 `analysis_orchestrator_factory`
4. 用对应 `stage_contract` 和 `report_contract` 驱动后续逻辑

### 10.4 报告落盘和读取统一依赖 contract

不要让保存和读取逻辑分散硬编码。

建议：

- 保存报告时，按当前 team 的 `report_contract` 写 section
- 读取报告时，也按当前 team 的 `report_contract` 读 section

---

## 11. 建议的运行流程

未来一次分析任务建议变成：

1. 接收分析请求
2. 决定 `team_id`
3. 读取 `team_spec`
4. 创建对应 graph
5. 执行分析
6. 按 `report_contract` 落盘
7. 把 `team_id` 和 report metadata 持久化到 task / conversation 上
8. 用户追问时，reply agent 先读取 `team_id`
9. 按 `reply_agent_spec` 加载对应报告并回答

---

## 12. 建议的最小落地顺序

建议分四步落地。

### 第一步：先抽象 Team Registry

- 新增 `AnalysisTeamSpec`
- 新增 `TEAM_REGISTRY`
- 先只注册 `full`

目标：

- 不改行为，只建立扩展点

### 第二步：把当前 full 流程接到 Team Manager

- task 增加 `teamId`
- runner 改为通过 team spec 创建 graph
- reply 侧按 `teamId` 读取 report contract

目标：

- 在不改变现有用户体验的前提下，把老流程纳入统一框架

### 第三步：新增 Lite Team

- 新增 `lite graph`
- 新增 `lite report contract`
- 新增 `lite stage contract`
- 新增 `lite reply agent`

目标：

- 在架构上安全引入第二套编排

### 第四步：做产品化选择

- 由产品决定哪些入口默认走 `lite`
- 哪些入口允许用户切换 `full / lite`

---

## 13. 关键决策建议

### 建议接受

- 引入 Team Manager
- 引入 `team_id`
- 引入 `report_contract`
- 引入 `stage_contract`
- 拆分成两个独立的 reply agent
- reply 侧按 `team_id` 选择对应 reply agent 和报告读取协议

### 建议暂缓

- 立刻重写所有 full graph 逻辑
- 立刻把 graph 做持久化存储

---

## 14. 我当前的建议结论

一句话总结：

> 建议新增一个 `Analysis Team Manager`，把“分析报告参与 agents、报告契约、reply agent、阶段体系”按 team 统一管理；保留现有 full 流程，同时新增 lite 流程，并让 reply 侧按 team 独立演进。

推荐先落地的方向是：

- 保留现有 `full team`
- 新建 `lite team`
- 新建 `full reply agent` 和 `lite reply agent`
- 统一由 Team Manager 或 reply router 按 `team_id` 选择对应 reply agent

这样改造的好处是：

- 架构清晰
- 风险可控
- 易于灰度
- 便于后续继续做低时延优化
