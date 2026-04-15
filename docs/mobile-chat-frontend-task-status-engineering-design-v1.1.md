# 移动端对话任务状态技术实现方案 v1.1

## 1. 文档信息

- 文档名称：移动端对话任务状态技术实现方案 v1.1
- 对应需求文档：`docs/mobile-chat-frontend-prd-v1.1.md`
- 适用范围：`mobile_h5`、`ta_service`、`tradingagents`
- 面向对象：前端、后端、测试

## 2. 设计目标

本方案用于支撑移动端会话页中 `task_status` 的技术落地，确保前端展示的任务状态与 `tradingagents` 实际运行过程一致。

本次方案重点解决以下问题：

- 将 `tradingagents` 的 `stage` 事件映射为前端可展示的阶段状态
- 将 `tradingagents` 的 `node` 事件映射为前端“谁正在工作”的动态文案
- 明确前后端实时状态传递格式与合并规则
- 处理 stalled、failed、页面返回、历史回放等边界场景

## 3. 总体设计原则

### 3.1 阶段优先，节点补充

- 前端任务主状态以 `stage_id` 为准
- 节点信息只用于增强当前阶段中的主体和动作文案
- 前端不得跳过 `stage_id` 直接用 `node_id` 自行生成新的业务阶段

### 3.2 产品语言与运行结构分层

- 运行层保留 `stage_id`、`node_id`、`event` 等技术字段
- 展示层统一转换为业务语义，如“新闻分析师正在整理近期关键事件”
- 不向用户暴露 Agent 名、内部服务名、模型名、阶段 ID

### 3.3 一个任务一条主状态流

- 同一分析任务在消息流中只维护一条主状态卡片
- 阶段变化时刷新卡片内容，不在消息流中无限追加碎片状态
- 只有任务完成、失败或明确新任务启动时，才结束当前状态流

### 3.4 真实运行优先于理想流程

- 设计以现有 `TradingAgentsRunner`、`StageEventTracker`、`NodeEventTracker` 的真实输出为依据
- 不要求 `tradingagents` 为前端重做一套状态体系
- 前端基于现有事件做映射和兜底

## 4. 现有运行结构

### 4.1 阶段来源

当前分析阶段由 `ta_service/adapters/tradingagents_runner.py` 中的 `_build_stage_snapshot` 生成。

当前已确认的阶段如下：

- `analysts.market`
- `analysts.social`
- `analysts.news`
- `analysts.fundamentals`
- `research.debate`
- `trader.plan`
- `risk.debate`
- `portfolio.decision`

### 4.2 节点来源

当前节点事件由 `tradingagents/observability.py` 中的 `NodeEventTracker` 输出。

节点会带出：

- `node_id`
- `stage_id`
- `node_kind`
- `status`

其中：

- `node_kind=agent` 表示分析师或管理节点
- `node_kind=tool` 表示工具调用节点
- `node_kind=utility` 表示内部清理节点

### 4.3 实际事件来源

当前运行中已存在以下观测文件：

- `stage_events.jsonl`
- `node_events.jsonl`
- `run_trace.jsonl`

前端展示的任务状态以 `stage_events` 为主，`node_events` 为辅。

## 5. 阶段与节点映射设计

### 5.1 阶段映射

| stage_id | 前端阶段名 | 默认展示主体 | 默认动作文案 |
| --- | --- | --- | --- |
| `analysts.market` | 市场分析 | 市场分析师 | 梳理价格走势与技术信号 |
| `analysts.social` | 情绪分析 | 情绪分析师 | 整理社交舆情与市场情绪 |
| `analysts.news` | 新闻分析 | 新闻分析师 | 整理近期关键事件与新闻影响 |
| `analysts.fundamentals` | 基本面分析 | 基本面分析师 | 梳理财务表现、盈利与估值 |
| `research.debate` | 研究讨论 | 研究团队 | 汇总多方观点并形成研究结论 |
| `trader.plan` | 交易计划 | 交易分析师 | 生成交易方案与执行思路 |
| `risk.debate` | 风险评估 | 风险团队 | 评估下行风险与仓位约束 |
| `portfolio.decision` | 投资决策 | 投资总监 | 输出最终投资决策 |

### 5.2 节点映射

| node_id | node_kind | stage_id | 前端解释 |
| --- | --- | --- | --- |
| `Market Analyst` | `agent` | `analysts.market` | 市场分析师正在工作 |
| `Social Analyst` | `agent` | `analysts.social` | 情绪分析师正在工作 |
| `News Analyst` | `agent` | `analysts.news` | 新闻分析师正在工作 |
| `Fundamentals Analyst` | `agent` | `analysts.fundamentals` | 基本面分析师正在工作 |
| `Bull Researcher` | `agent` | `research.debate` | 研究团队正在形成看多观点 |
| `Bear Researcher` | `agent` | `research.debate` | 研究团队正在形成看空观点 |
| `Research Manager` | `agent` | `research.debate` | 研究团队正在汇总讨论结论 |
| `Trader` | `agent` | `trader.plan` | 交易分析师正在生成交易方案 |
| `Aggressive Analyst` | `agent` | `risk.debate` | 风险团队正在评估积极情景 |
| `Conservative Analyst` | `agent` | `risk.debate` | 风险团队正在评估保守情景 |
| `Neutral Analyst` | `agent` | `risk.debate` | 风险团队正在评估中性情景 |
| `Portfolio Manager` | `agent` | `portfolio.decision` | 投资总监正在输出最终决策 |
| `tools_*` | `tool` | 所属阶段 | 当前阶段正在收集数据或补充信息 |
| `Msg Clear *` | `utility` | 所属阶段 | 内部节点，不对用户单独展示 |

### 5.3 映射规则

- `stage_id` 决定当前任务处于哪个大阶段
- `node_id` 决定当前阶段的细粒度工作主体
- 若 `node_id` 无法识别，回退到对应 `stage_id` 的默认主体和动作
- 若 `stage_id` 无法识别，回退到通用文案“投资团队正在推进分析”

## 6. 状态模型设计

### 6.1 前端状态定义

前端内部任务状态统一定义为：

| 前端状态 | 来源 | 含义 |
| --- | --- | --- |
| `pending` | 初始或等待阶段开始 | 任务已发起，等待进入处理 |
| `active` | `stage.started` | 当前阶段正在处理 |
| `stalled` | `stage.stalled` 或兜底判断 | 当前阶段仍在执行，但长时间无明显推进 |
| `done` | `stage.completed` | 当前阶段已完成 |
| `failed` | `stage.failed` | 当前阶段或任务已失败 |

### 6.2 阶段级状态转换

标准状态流转如下：

`pending -> active -> done`

异常流转如下：

`active -> stalled -> active`

`active -> failed`

`stalled -> failed`

### 6.3 节点级状态使用约束

- `node.started` 仅更新当前阶段文案
- `node.completed` 不单独渲染为新状态
- `node.failed` 不直接替代阶段失败，需等待 `stage.failed` 或后端任务失败事件
- `node.stalled` 仅作为页面文案刷新辅助依据

## 7. 事件契约设计

### 7.1 事件模型

后端向前端传递任务状态时，统一采用事件流模型。

建议事件类型如下：

- `stage.started`
- `stage.completed`
- `stage.failed`
- `stage.stalled`
- `node.started`
- `node.completed`
- `node.failed`
- `node.stalled`
- `task.completed`
- `task.failed`

### 7.2 最小字段契约

所有任务状态事件至少包含以下字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `task_id` | 是 | 当前分析任务唯一标识 |
| `run_id` | 是 | TradingAgents 运行标识 |
| `event` | 是 | 事件类型 |
| `ts` | 是 | 事件时间 |
| `stage_id` | 阶段事件必填 | 当前阶段标识 |
| `status` | 阶段事件必填 | 阶段状态 |
| `node_id` | 节点事件推荐 | 当前节点标识 |
| `node_kind` | 节点事件推荐 | 节点类型 |
| `elapsed_time` | 推荐 | 已用时间，单位由接口统一 |
| `eta` | 可选 | 预计剩余时间 |
| `error_code` | 失败事件推荐 | 错误代码 |
| `error_message` | 失败事件推荐 | 错误说明 |

### 7.3 推荐事件载荷

```json
{
  "task_id": "task_123",
  "run_id": "TSLA-f69016810855",
  "event": "stage.started",
  "ts": "2026-04-13T11:09:05.536876+00:00",
  "stage_id": "analysts.market",
  "status": "in_progress",
  "elapsed_time": 0,
  "eta": null
}
```

```json
{
  "task_id": "task_123",
  "run_id": "TSLA-f69016810855",
  "event": "node.started",
  "ts": "2026-04-13T11:12:08.768075+00:00",
  "stage_id": "analysts.news",
  "node_id": "News Analyst",
  "node_kind": "agent",
  "status": "in_progress"
}
```

## 8. 前端实现方案

### 8.1 状态存储

前端建议按 `task_id` 维度维护任务状态对象：

```ts
type TaskStatusViewModel = {
  taskId: string
  runId?: string
  currentStageId?: string
  currentNodeId?: string
  currentNodeKind?: 'agent' | 'tool' | 'utility'
  displayState: 'pending' | 'active' | 'stalled' | 'done' | 'failed'
  displayTitle: string
  displaySubtitle?: string
  elapsedTimeSec?: number
  etaSec?: number
  updatedAt: string
}
```

### 8.2 事件处理顺序

前端接收事件后按以下顺序处理：

1. 根据 `task_id` 定位当前任务状态对象。
2. 若为 `stage` 事件，更新 `currentStageId` 和 `displayState`。
3. 若为 `node` 事件，且 `stage_id` 与当前阶段一致，则更新节点文案。
4. 重新计算 `displayTitle` 和 `displaySubtitle`。
5. 刷新已用时间与预计剩余时间显示。

### 8.3 文案生成策略

优先级如下：

1. 有明确可识别的 `node_id` 时，按节点映射生成文案。
2. 无节点信息时，按 `stage_id` 默认文案生成。
3. 阶段未知时，回退到“投资团队正在推进分析”。

示例：

- `stage_id=analysts.news` + `node_id=News Analyst`
  - `新闻分析师正在整理近期关键事件`
- `stage_id=analysts.news` + `node_id=tools_news`
  - `新闻分析师正在补充新闻与公开信息`
- `stage_id=risk.debate` + 无 `node_id`
  - `风险团队正在评估下行风险与仓位约束`

### 8.4 消息流合并规则

- 同一 `task_id` 仅保留一条活跃的 `task_status` 消息
- 阶段更新时原地刷新，不追加新消息
- 若新任务启动，创建新的 `task_status`
- 若旧任务已完成，保留为静态完成态

### 8.5 时间刷新策略

- 进入 `active` 或 `stalled` 后，前端每秒或每 5 秒刷新已用时间
- 若后端提供 `eta`，前端同步展示预计剩余时间
- 进入 `done` 或 `failed` 后，停止本地计时刷新

## 9. 后端实现方案

### 9.1 后端职责

后端负责：

- 为每次分析生成稳定的 `task_id`
- 将 `stage_events` 和 `node_events` 转换为前端可消费事件
- 保障同一任务事件顺序尽量稳定
- 在任务完成和失败时发出终态事件

### 9.2 与现有结构对接

建议以 `TradingAgentsRunner` 现有回调为基础扩展：

- `on_stage_change`：继续承担阶段切换通知
- `on_node_change`：继续承担节点切换通知
- 新增事件封装层：将 `stage_events.jsonl`、`node_events.jsonl` 的语义转为 API 输出或流式推送

### 9.3 推送方式建议

优先级建议如下：

1. SSE：适合单任务连续状态流推送，实现成本低
2. WebSocket：适合未来做多任务并行和更复杂实时能力
3. 轮询：仅作为兜底方案

若一期追求稳定交付，优先推荐 SSE。

### 9.4 服务端兜底规则

- 若节点事件缺失，仍必须保证阶段事件完整
- 若阶段卡住，需能输出 `stage.stalled`
- 若分析抛错，需输出 `stage.failed` 或 `task.failed`
- 若任务完成，需输出最终完成事件，避免前端永久停留在 `active`

## 10. 历史回放与恢复方案

### 10.1 历史消息回放

- 历史消息列表返回时，`task_status` 应返回最新快照，而不是全量事件流
- 已完成任务返回 `done`
- 已失败任务返回 `failed`
- 进行中任务返回当前阶段状态与已用时间

### 10.2 页面刷新与重连

- 页面重连后，前端先拉取任务当前快照
- 若随后收到流式事件，再以事件增量更新
- 若快照与事件冲突，以时间较新的状态为准

## 11. 异常场景处理

### 11.1 节点频繁轮转

- 不在 UI 中为每次 `node.started` 单独生成新消息
- 只刷新当前状态卡片文案

### 11.2 阶段长时间无变化

- 收到 `stage.stalled` 后进入 `stalled`
- 仍保留“任务正在推进”的温和语义
- 若后续恢复阶段推进，可从 `stalled` 回到 `active`

### 11.3 工具节点暴露过深

- `tools_*` 不直接显示技术节点名
- 前端转换为“正在收集数据”“正在补充信息”等业务表达

### 11.4 内部清理节点干扰体验

- `Msg Clear *` 一律不单独展示
- 前端可直接忽略 `utility` 节点

### 11.5 任务失败

- 任务失败后当前状态卡片切为 `failed`
- 停止动效和倒计时
- 消息流由 `小I` 追加错误消息承接

## 12. 联调方案

### 12.1 联调清单

- 前端确认 `stage_id` 映射表与节点映射表
- 后端确认事件字段名与时间单位
- 双方确认 `task_id`、`run_id` 的关系
- 双方确认同一任务消息更新为“覆盖”而不是“追加”

### 12.2 联调样例

至少准备以下样例：

- 正常完整跑通一条分析链路
- 某阶段 stalled 后恢复
- 某阶段失败
- 页面刷新后恢复任务状态
- 历史消息回放

## 13. 测试方案

### 13.1 功能测试

- 验证各 `stage_id` 能正确映射到阶段展示
- 验证各关键 `node_id` 能正确映射到主体文案
- 验证 `tools_*`、`utility` 节点的折叠和忽略逻辑

### 13.2 状态流测试

- `pending -> active -> done`
- `active -> stalled -> active`
- `active -> failed`
- 多阶段连续切换

### 13.3 体验测试

- 同一任务不会在消息流中产生过多碎片状态
- 状态文案不暴露技术实现细节
- 页面长时间处理中不会显得“挂住”

## 14. 风险与后续演进

### 14.1 当前风险

- 现有前端若只接收粗粒度状态，需补充事件消费层
- 若后端事件顺序不稳定，前端需增加时间戳保护
- 若未来 `tradingagents` 新增阶段，映射表需同步维护

### 14.2 后续演进方向

- 支持更多阶段的细化业务文案
- 支持面向任务的完整时间线回放
- 支持多任务并发状态管理
- 支持任务状态埋点和性能分析

## 15. 结论

本方案采用“阶段主导、节点补充、前后端分层映射”的实现方式，在不重构 `tradingagents` 核心编排的前提下，为移动端提供稳定、可解释、可联调的任务状态体验。

该方案可直接作为前后端联调和开发依据使用。
