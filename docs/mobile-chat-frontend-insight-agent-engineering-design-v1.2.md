# 移动端追问解读 Agent 技术实现方案 v1.2

## 1. 文档信息

- 文档名称：移动端追问解读 Agent 技术实现方案 v1.2
- 对应需求文档：`docs/mobile-chat-frontend-prd-v1.2.md`
- 适用范围：`ta_service`、`mobile_h5`
- 面向对象：后端、前端、测试

## 2. 设计目标

本方案用于支撑移动端当前会话页中 `insight_reply` 的 v1.2 技术落地，确保追问阶段的回答从“报告式二次解读”升级为“回答优先、按需检索、逐步展开”的高对话效率体验。

本次方案重点解决以下问题：

- 将追问解读能力明确收敛到一条稳定的 LLM Agent 实现链路
- 让 Agent 基于当前问题自主判断是否需要读取 report，而不是默认加载整份报告
- 保留分析后多份 report 的边界信息，支持按需读取和跨 report 联动
- 将章节探索阶段与最终回答阶段分离，避免无边界展开
- 保证前端对 `insight_reply` 的承接仍保持聊天节奏，而不退化为新报告阅读模式

## 3. 总体设计原则

### 3.1 Agent 负责判断，Service 负责承接

- `ReportInsightAgent` 负责：
  - 理解当前问题
  - 判断现有上下文是否足够
  - 决定是否读取 report 章节
  - 基于已知材料生成最终答复
- `ConversationService` 负责：
  - 组装 Agent 输入上下文
  - 调用 Agent
  - 写入 `insight_reply`
  - 推进会话状态
  - 处理降级与错误承接

### 3.2 多 report 保持边界，不做静态路由

- 分析后的 report 天然按多个维度分开存储
- 系统应保留这种边界，供 Agent 自主判断取材范围
- 产品层不维护“问题类型 -> report 集合”的硬编码命中表
- 仅在工具层提供“有哪些章节可读、如何读取”的能力

### 3.3 轻量上下文优先，重材料按需加载

- 默认不将所有 report 文本一次性拼入 prompt
- 优先提供：
  - 当前问题
  - 最近多轮对话
  - 标的与分析日期
  - report 章节目录
- 只有在必要时才读取具体章节正文

### 3.4 探索与回答分阶段收敛

- 章节探索阶段允许 Agent 调用读取工具
- 最终回答阶段禁止继续调用工具
- 这样可以避免 Agent 长时间停留在“继续搜材料”的状态
- 也有利于稳定回答风格与输出长度

### 3.5 前端不重建 Agent 决策

- 前端只承接 `insight_reply` 结果
- 前端不判断问题属于哪类 report
- 前端不自行拼接 report 或生成摘要
- 前端不暴露技术性工具调用或 report 选择过程

## 4. 现有实现结构

### 4.1 当前调用链

当前追问链路已经具备基础实现：

1. 前端调用 `POST /conversations/{id}/messages`
2. `ConversationService.post_message()` 校验当前状态为 `report_ready` 或 `report_explaining`
3. `ConversationService._build_insight_context()` 组装 `ReportInsightContext`
4. `ReportInsightAgent.answer()` 生成回答
5. 服务端写入 `MessageType.INSIGHT_REPLY`
6. 会话状态推进到 `report_explaining`

### 4.2 当前上下文来源

当前 `ReportInsightContext` 已包含：

- `conversation_id`
- `question`
- `ticker`
- `trade_date`
- `trace_dir`
- `available_sections`
- `report_sections`
- `conversation_history`

这已经满足 v1.2 所需的基础上下文结构。

### 4.3 当前 report 存储结构

当前分析结果并非只有单一报告，而是拆分为多份 report 文件，例如：

- `decision`
- `trading_plan`
- `fundamentals`
- `market`
- `news`
- `sentiment`
- `bull_research`
- `bear_research`
- `research_mgr`
- `risk_aggr`
- `risk_cons`
- `risk_neutral`

这些章节由 `ReportContextLoader` 负责列出与读取。

### 4.4 当前 Agent 能力

当前 `ReportInsightAgent` 已具备：

- 工具调用式章节读取
- 工具调用轮次和单轮调用数限制
- 独立的最终回答阶段
- `summary_card` 降级路径
- `is_answerable` 与 `source_sections` 输出

因此 v1.2 重点不是从零实现，而是围绕现有链路进行策略收敛与体验增强。

## 5. 目标方案总览

### 5.1 总体方案

v1.2 统一采用“轻量上下文 + 按需读取 + 最终回答收敛”的实现路径：

1. Service 组装轻量上下文
2. Agent 基于问题和章节目录先做判断
3. 必要时按需调用 `read_report_section`
4. 探索结束后进入最终回答阶段
5. 输出短而直接、适合移动端阅读的 `insight_reply`

### 5.2 时序概览

1. 用户在 `report_ready` 或 `report_explaining` 状态下继续追问
2. 前端发送普通追问消息
3. 后端写入用户消息
4. `ConversationService` 构建 `ReportInsightContext`
5. `ReportInsightAgent` 执行：
   - 判断是否可直接回答
   - 必要时按需读章节
   - 生成最终答复
6. 后端写入 `insight_reply`
7. 前端将该回答按普通聊天消息承接

## 6. 后端实现方案

### 6.1 ConversationService 方案

#### 做什么

承接当前追问消息，构建 Agent 输入，落库结果并推进状态。

#### 怎么做

保留现有 `post_message()` 主链路，只做以下增强：

- 明确将 `ReportInsightAgent` 视为追问阶段唯一回答器
- 继续使用 `_build_insight_context()` 统一组装上下文
- 保持 `trace_dir + available_sections` 为正常路径
- 保持 `summary_card` 为无 report 时的降级路径
- 将 Agent 返回结果继续写入 `MessageType.INSIGHT_REPLY`

#### 边界与约束

- `ConversationService` 不做问题类型判断
- `ConversationService` 不决定具体读取哪些 report
- `ConversationService` 只负责输入装配和结果承接

### 6.2 ReportContextLoader 方案

#### 做什么

为 Agent 提供 report 章节目录和按需读取能力。

#### 怎么做

继续以 `trace_dir -> reports_root/<trace_dir.name>` 的方式定位报告目录，并保留以下接口：

- `list_available_sections()`
- `load_single_section()`
- `load()`

其中 v1.2 的主路径以：

- `list_available_sections()` 作为目录暴露
- `load_single_section()` 作为工具读取能力

为主；`load()` 主要保留给降级或兼容场景使用。

#### 边界与约束

- Loader 只负责 report 材料装载
- Loader 不负责问题理解
- Loader 不负责回答组织

### 6.3 ReportInsightAgent 方案

#### 做什么

把追问阶段实现为带最小工具能力的 LLM Agent。

#### 怎么做

保留现有 `answer()` 入口，并将执行路径固定为两类：

1. 正常路径：
   - `trace_dir` 存在
   - `available_sections` 非空
   - 走工具调用式 Agent
2. 降级路径：
   - 无磁盘 report
   - 使用 `report_sections` 中的摘要文本
   - 直接回答

#### 核心工作流

正常路径下的 Agent 工作流如下：

1. 注入系统提示词和当前问题
2. 向模型暴露章节目录与读取工具
3. 模型决定是否调用 `read_report_section`
4. 服务端执行工具并把读取结果回填到历史消息
5. 达到停止条件后，进入最终回答阶段
6. 最终回答阶段禁止再次调用工具

#### 边界与约束

- Agent 可以判断“读不读、读哪个、读几个”
- Agent 不允许无限制读所有章节
- Agent 不允许在最终回答阶段继续探索

### 6.4 工具设计

#### 工具定义

本期仅保留一个工具：

- `read_report_section(section)`

#### 工具职责

- 根据章节名读取对应 report 内容
- 返回结构化结果：
  - `section`
  - `content`
  - 或错误说明

#### 工具使用规则

- Agent 只能读取当前 `available_sections` 中已存在的章节
- 每次只读一个章节
- 工具调用结果不直接输出给用户，而是作为回答依据

### 6.5 预算控制设计

当前代码已使用：

- `_MAX_TOOL_ROUNDS = 3`
- `_MAX_TOOL_CALLS_PER_ROUND = 4`

v1.2 沿用这一控制方式，作为追问阶段的默认探索预算。

#### 预算策略

- 未调用工具时，可直接输出回答
- 每轮工具调用数受限
- 总轮次受限
- 若模型在预算耗尽后仍想继续读章节，则强制进入最终回答阶段

#### 设计意图

- 限制无边界章节探索
- 让简单问题尽量快速回答
- 对复杂问题仍保留有限的补充空间

### 6.6 最终回答阶段设计

#### 做什么

在探索结束后输出面向用户的最终答复。

#### 怎么做

保留现有 `_finalize_tool_answer()`：

- 使用独立的最终阶段系统提示词
- 注入：
  - 当前问题
  - 已读取章节
  - 工具轮次
  - 是否预算耗尽
- 明确禁止继续调用工具

#### 输出要求

- 优先直接回答问题
- 如有必要补充 2-4 条关键点
- 若材料不足，明确说明无法回答
- 适合移动端阅读

### 6.7 降级与兜底设计

#### 降级路径

当 `trace_dir` 不存在且 `available_sections` 为空时：

- 若存在 `summary_card` 摘要，则构造 `report_sections = {"executive_summary": ...}`
- 走 `_answer_with_preloaded_sections()`

#### 兜底路径

以下情况统一返回稳定兜底：

- 无任何可用报告材料
- LLM 初始化失败
- LLM 调用失败
- 最终回答为空

#### 设计目标

- 不让用户看到空白回答
- 不因部分能力不可用而打断整个追问链路

### 6.8 可观测性设计

当前代码已具备基本日志能力，v1.2 继续围绕以下指标观察：

- 是否可回答
- 工具轮次使用数
- 是否触发预算耗尽
- 已读取章节列表
- 是否走降级路径

建议后续在日志聚合中补充：

- 简单问题零工具回答比例
- 平均读取章节数
- 平均追问响应耗时
- 无法回答比例

## 7. 前端实现方案

### 7.1 前端职责

前端只负责：

- 发送追问消息
- 承接服务端返回的 `insight_reply`
- 将其作为普通聊天消息插入消息流
- 保持当前会话页的对话节奏

前端不负责：

- 判断问题对应哪些 report
- 重建 Agent 工具逻辑
- 拼接多个 report 自行总结

### 7.2 消息承接方案

当前 `PostConversationMessageResponse` 仍返回：

```ts
{
  messages: ConversationMessage[]
}
```

v1.2 不要求修改这条接口主形态。

前端继续按 `messageType === 'insight_reply'` 承接消息，默认渲染为普通聊天回答。

### 7.3 展示策略

#### 默认策略

- `insight_reply` 保持为聊天消息
- 不切换到结果卡片或报告页
- 不因内容稍长就改造成长文阅读容器

#### 与 `summary_card` 的分工

- `summary_card`：分析完成后的主结果承载
- `insight_reply`：追问阶段的对话式解读承载

#### 后续扩展兼容

若后端未来补充结构化字段，例如：

- `sourceSections`
- `answerMode`
- `keyPoints`

前端可在消息组件内渐进增强，但不重构消息流骨架。

### 7.4 交互节奏

- 用户在 `report_ready`、`report_explaining` 状态下可继续追问
- 追问发送后，前端维持当前消息流交互，不额外插入技术性中间态
- 新回答到达后自然追加到当前消息流
- 若回答走服务降级路径，前端也按自然语言回答承接，不暴露内部原因

## 8. 数据与接口设计

### 8.1 当前后端返回结构

当前 `ReportInsightResult` 包含：

- `answer`
- `is_answerable`
- `source_sections`

但当前对前端直接暴露的仍然只有 `answer`，并通过 `insight_reply` 写入消息流。

### 8.2 v1.2 接口策略

一期不新增前端必需字段，保持现有接口稳定：

- `POST /conversations/{id}/messages`
- 返回新增消息数组

后续如需增强，可考虑把 `source_sections` 作为调试或管理字段附带在消息内容元数据中，但不作为 v1.2 必要改动。

### 8.3 消息类型契约

前端与后端继续保持 `MessageType.INSIGHT_REPLY` 一致，不新增新的追问消息类型。

这能保证：

- 历史回放兼容
- store 结构无需重做
- 前端承接逻辑最小改动

## 9. 落地步骤

### 9.1 后端

1. 固化 `ReportInsightAgent` 的系统提示词，使其更明确遵守“直接回答优先”
2. 校准工具调用预算与最终回答阶段提示词
3. 校准降级路径文案与日志字段
4. 评估是否需要把 `source_sections` 进一步透出给调试接口

### 9.2 前端

1. 保持 `insight_reply` 为普通聊天消息承接
2. 检查长回答排版，避免回退成报告阅读感
3. 为未来结构化字段预留组件扩展点，但不引入新页面形态

### 9.3 联调

重点验证以下场景：

- 简单问题无需读章节即可回答
- 复杂问题按需读少量章节后回答
- 跨 report 问题能引用多份依据
- 无 report 时走摘要降级
- 无法回答时返回明确提示

## 10. 测试方案

### 10.1 后端测试

- `ConversationService._build_insight_context()` 上下文构造正确
- `ReportContextLoader` 能正确列出和读取章节
- `ReportInsightAgent` 正常路径与降级路径均可运行
- 工具预算耗尽后能进入最终回答阶段
- LLM 不可用和无 report 时能返回稳定兜底

### 10.2 前端测试

- `insight_reply` 继续按普通聊天消息显示
- 连续多轮追问下消息流节奏稳定
- 较长回答不会被错误渲染成新报告
- 降级提示与无法回答提示能自然承接

### 10.3 联调测试

- `report_ready` -> 继续追问 -> `report_explaining` 流程正确
- 正常路径和降级路径都能返回可展示消息
- store 中新增消息顺序正确
- 历史回放对旧 `insight_reply` 不产生兼容性问题

## 11. 风险与后续演进

### 11.1 当前风险

- 若系统提示词不够强，模型仍可能输出偏长解释
- 若工具预算过大，简单问题仍可能被拖入过度探索
- 若工具预算过小，复杂问题可能过早结束并降低解释质量
- 当前前端只承接文本，无法向用户显式呈现回答依据来源

### 11.2 后续演进方向

- 在不破坏聊天节奏的前提下，渐进增强 `source_sections` 展示
- 引入更细的回答模式标记，例如直接回答 / 深度展开 / 无法回答
- 基于日志优化“零工具回答率”和“平均读取章节数”
- 视效果决定是否为部分复杂场景引入更强的结构化回答协议

## 12. 结论

本方案采用“Service 组装轻量上下文、Agent 按需读 report、最终阶段收敛回答、前端继续按聊天消息承接”的实现方式，在不重做当前会话页结构的前提下，把 `insight_reply` 升级为一条稳定、可迭代、符合多 report 现实结构的追问解读链路。

该方案可直接作为 v1.2 前后端开发、联调与测试依据使用。
