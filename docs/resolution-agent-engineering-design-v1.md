# F3 会话式 Ticker 识别与确认技术方案 v1

## 1. 设计目标

本方案采用一层独立的 `Resolution Agent` 能力，放在正式分析任务创建之前，负责：

- 理解用户分析诉求
- 识别股票线索
- 调用股票候选搜索和详情查询能力
- 完成消歧与确认
- 输出结构化结果
- 与会话状态和正式分析任务创建链路衔接

### 一期目标范围

一期目标统一聚焦在单股票分析前的标的确认闭环，覆盖：

- 分析诉求理解
- 股票候选召回
- 确认与消歧
- 结构化输出
- 正式分析前的状态衔接

## 2. 设计原则

### 2.1 Agent 负责自然语言判断，Service 负责系统承接

- `ResolutionAgent` 负责：
  - 理解自然语言
  - 识别股票线索
  - 组织候选查询
  - 做候选判断与消歧
  - 输出结构化结果
- `ResolutionService` 负责：
  - 接收接口请求
  - 组装上下文
  - 触发 Agent
  - 校验输出
  - 管理轮次
  - 落库状态
  - 处理结构化确认动作
  - 推进到 `ready_to_analyze`

### 2.2 tools 仅保留外部股票数据访问能力

一期 tools 统一保留为：

- `search_stock_candidates`
- `get_stock_profile`

以下能力统一作为内部能力实现：

- 显式 ticker 提取
- 市场线索提取
- 候选判断
- 消歧决策
- 确认文案生成
- 轮次控制
- 产品范围校验

### 2.3 自然语言事件与结构化事件分别处理

- 自然语言事件：
  - 触发一次 `ResolutionAgent`
- 结构化事件：
  - 由 `ResolutionService` 直接消费并收尾

自然语言事件包括：

- 首次分析诉求
- 补充说明
- 改口说明

结构化事件包括：

- 点击确认按钮
- 点击候选项
- 点击“重新输入”

### 2.4 输出统一采用强结构化协议

Agent 输出统一包含：

- 当前状态
- 展示文案
- 候选列表
- 股票对象
- 用户关注点
- 是否可进入正式分析
- 当前回合是否结束

### 2.5 MVP 优先复用现有能力

MVP 采用：

- `ta_service` 作为业务承载层
- `StockLookupGateway` 作为股票查询适配层
- `tradingagents` 作为同仓库内嵌 data vendor 能力库

股票查询能力统一通过 `StockLookupGateway` 提供。

## 3. 具体方案

### 3.1 总体方案

#### 做什么

定义 F3 功能在系统中的整体实现形态，以及各核心组件在正式分析前阶段的职责分工。

#### 怎么做

本方案采用以下组件：

- `ResolutionService`
- `ResolutionAgent`
- `StockLookupGateway`

职责如下：

#### `ResolutionService`

- 负责组装 Agent 输入上下文
- 触发 Agent
- 校验输出 schema
- 维护轮次
- 写入会话快照和消息
- 处理结构化确认动作
- 推进到 `ready_to_analyze`

#### `ResolutionAgent`

- 理解用户分析诉求
- 提取股票线索
- 决定是否调用 tools
- 输出结构化结果

#### `StockLookupGateway`

- 向上提供：
  - `search_stock_candidates`
  - `get_stock_profile`
- 向下复用 `tradingagents` 的：
  - market 识别能力
  - symbol 归一化能力
  - vendor 查询能力

#### 边界与约束

- F3 聚焦正式分析前的标的识别与确认，不替代现有 `AnalysisService`
- `ResolutionAgent` 负责语义理解与决策输出，不直接承接数据库写入和任务创建
- `ResolutionService` 负责系统门禁、状态承接和结构化确认收尾
- `StockLookupGateway` 负责股票查询能力适配，不直接暴露给前端

### 3.2 内部依赖关系

#### 做什么

定义 F3 与现有前后端、服务层和数据能力之间的依赖方向。

#### 怎么做

统一依赖方向如下：

- 前端 -> `ta_service` API
- API -> `ResolutionService`
- `ResolutionService` -> `ResolutionAgent`
- `ResolutionService` -> `StockLookupGateway`
- `StockLookupGateway` -> `tradingagents`
- `ResolutionService` -> `ConversationRepository / MessageRepository`

`tradingagents` 继续作为同仓库 Python library 服务 `ta_service`。

#### 边界与约束

- `ResolutionService` 通过 `StockLookupGateway` 访问股票数据，不直接耦合 vendor SDK
- `ResolutionService` 通过 repository 承接会话状态和消息写入，不直接暴露内部状态给前端
- `tradingagents` 继续以内嵌能力库形式复用，不在一期演进为独立服务

### 3.3 API 接口

#### 做什么

定义前端与后端在 F3 阶段的接口契约，以及自然语言输入和结构化确认的分工。

#### 怎么做

一期接口统一分为两类：

- `/resolution`
- `/resolution/confirm`

#### 接口 1：发起 resolution

`POST /conversations/{conversation_id}/resolution`

请求体：

```json
{
  "message": "分析苹果，重点看估值"
}
```

响应体：

```json
{
  "resolutionId": "string",
  "status": "need_confirm",
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "candidates": [],
  "promptMessage": "你想分析的是 Apple Inc.（AAPL）吗？",
  "conversationStatus": "collecting_inputs",
  "messages": []
}
```

#### 接口 2：确认或选择候选

`POST /conversations/{conversation_id}/resolution/confirm`

请求体：

```json
{
  "action": "confirm",
  "resolutionId": "string"
}
```

或：

```json
{
  "action": "select",
  "resolutionId": "string",
  "ticker": "AAPL"
}
```

响应体：

```json
{
  "resolutionId": "string",
  "accepted": true,
  "status": "resolved",
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "promptMessage": "已为你确认分析标的是 Apple Inc.（AAPL）。",
  "conversationStatus": "ready_to_analyze",
  "messages": []
}
```

#### 边界与约束

- `/resolution` 只承接自然语言输入
- `/resolution/confirm` 只承接结构化确认与候选选择
- 未进入 `ready_to_analyze` 前，前端不调用正式分析任务创建接口
- 接口响应统一返回前端可直接消费的状态、展示文案和消息快照

### 3.4 调用时序

#### 做什么

定义 F3 从自然语言输入到标的确认完成的主链路时序。

#### 怎么做

#### 时序 A：自然语言输入链路

1. 用户在当前会话页输入自然语言分析诉求
2. 前端调用 `/resolution`
3. `ResolutionService` 读取：
   - 当前输入
   - 最近 resolution 摘要
   - 当前轮次
   - `pendingResolution`
4. `ResolutionService` 调用 `ResolutionAgent`
5. `ResolutionAgent` 按需调用：
   - `search_stock_candidates`
   - `get_stock_profile`
6. Agent 输出结构化结果
7. `ResolutionService` 校验输出并落库
8. 前端按状态渲染：
   - 补充提示
   - 确认卡片
   - 候选列表
   - 或直接进入已确认状态

#### 时序 B：结构化确认链路

1. 用户点击确认按钮或候选项
2. 前端调用 `/resolution/confirm`
3. `ResolutionService` 读取 `pendingResolution`
4. `ResolutionService` 校验：
   - `resolutionId`
   - 当前状态
   - 候选合法性
5. `ResolutionService` 直接完成收尾
6. 会话状态推进为 `ready_to_analyze`
7. 前端收到 `resolved`
8. 前端调用正式分析任务创建接口

#### 边界与约束

- 自然语言输入触发 `ResolutionAgent`
- 结构化确认事件由 `ResolutionService` 直接处理
- `ResolutionService` 负责校验 `resolutionId`、候选合法性和状态一致性
- 只有时序完成到 `ready_to_analyze`，F3 才视为完成

### 3.5 ResolutionService 状态机设计

#### 做什么

定义 `ResolutionService` 在 F3 完整实现中的业务状态、触发事件和状态迁移规则。

#### 怎么做


一期采用轻量业务状态机，只定义 F3 必需的稳定状态，不约束 Agent 的内部推理路径。Agent 可以自主决定“问什么、查什么、如何判断”，Service 负责定义“当前处于哪个业务阶段、下一步允许做什么、何时可以结束”。

#### 状态定义

- `collecting_inputs`
  - 当前仍处于标的定位阶段
  - 系统允许继续接收自然语言补充
  - 会话状态保持 `collecting_inputs`
- `need_confirm`
  - 当前存在唯一高置信候选
  - 系统等待用户点击确认或改口
  - `pendingResolution` 中保存唯一候选快照
- `need_disambiguation`
  - 当前存在多个合理候选
  - 系统等待用户从候选中选择或补充说明
  - `pendingResolution` 中保存候选列表快照
- `ready_to_analyze`
  - 当前股票已确认完成
  - 系统允许前端调用正式分析任务创建接口
  - 当前 `resolution` 结束
- `unsupported`
  - 当前输入属于一期范围外
  - 系统返回范围提示，并结束本轮 `resolution`
- `failed`
  - 当前 `resolution` 因工具失败或超限结束
  - 系统返回失败或兜底提示，并结束本轮 `resolution`

#### 触发事件

- `submit_message`
  - 用户提交自然语言分析诉求、补充说明或改口说明
- `confirm_resolution`
  - 用户确认唯一候选
- `select_candidate`
  - 用户从候选列表中选择股票
- `restart_resolution`
  - 用户放弃当前待确认结果并重新输入
- `resolution_timeout`
  - 单轮执行超时或外部工具失败
- `round_limit_reached`
  - 超过最大澄清轮次

#### 状态迁移规则

1. 初始进入 F3 时：
   - 会话状态进入 `collecting_inputs`
   - `ResolutionService` 接收 `submit_message`
   - 调用 `ResolutionAgent`

2. Agent 输出 `collect_more` 时：
   - 状态保持 `collecting_inputs`
   - 更新 `pendingResolution` 的轮次和上下文摘要
   - 返回补充提示

3. Agent 输出 `need_confirm` 时：
   - 状态迁移到 `need_confirm`
   - 写入唯一候选到 `pendingResolution`
   - 返回确认卡片

4. Agent 输出 `need_disambiguation` 时：
   - 状态迁移到 `need_disambiguation`
   - 写入候选列表到 `pendingResolution`
   - 返回候选选择卡片

5. Agent 输出 `confirmed` 时：
   - 状态迁移到 `ready_to_analyze`
   - 写入最终股票对象
   - 清理待确认快照
   - 返回已确认结果

6. 用户提交 `confirm_resolution` 时：
   - `ResolutionService` 校验当前 `resolutionId` 和状态
   - 当前状态为 `need_confirm` 时，直接迁移到 `ready_to_analyze`
   - 写入最终股票对象并清理待确认快照

7. 用户提交 `select_candidate` 时：
   - `ResolutionService` 校验所选 ticker 属于当前候选集
   - 校验通过后直接迁移到 `ready_to_analyze`
   - 写入最终股票对象并清理待确认快照

8. 用户提交 `restart_resolution` 或发生改口时：
   - `ResolutionService` 清理当前 `pendingResolution`
   - 当前状态回到 `collecting_inputs`
   - 以最新输入重新触发 Agent

9. Agent 输出 `unsupported` 时：
   - 当前 `resolution` 进入 `unsupported`
   - 写入结束状态
   - 返回范围提示

10. 工具失败或超过轮次时：
    - 当前 `resolution` 进入 `failed`
    - 写入失败原因或超限原因
    - 返回兜底提示

#### Service 承接规则

- 自然语言事件一定先进入 `ResolutionService`
- 只有自然语言事件触发 `ResolutionAgent`
- 结构化确认事件由 `ResolutionService` 直接处理，不再次触发 Agent
- 只有 `ready_to_analyze` 允许进入正式分析任务创建
- 旧 `resolutionId`、非法候选项和重复确认请求统一由 `ResolutionService` 拦截

#### 持久化快照

`ResolutionService` 通过 `pendingResolution` 承接状态机当前快照。MVP 至少保存以下信息：

- `resolutionId`
- `status`
- `round`
- `originalMessage`
- `assistantReply`
- `candidates`
- `resolvedStock`
- `focusPoints`
- `updatedAt`

该快照用于：

- 页面刷新后的状态恢复
- `/resolution/confirm` 的直接收尾
- 改口时的状态重置
- 服务侧幂等和合法性校验

#### 与会话状态的映射

- `collecting_inputs` -> `conversation.status = collecting_inputs`
- `need_confirm` -> `conversation.status = collecting_inputs`
- `need_disambiguation` -> `conversation.status = collecting_inputs`
- `ready_to_analyze` -> `conversation.status = ready_to_analyze`
- `unsupported` -> `conversation.status = collecting_inputs`
- `failed` -> `conversation.status = collecting_inputs`

#### 边界与约束

`ResolutionService` 状态机负责定义业务阶段和迁移规则，`ResolutionAgent` 负责输出语义判断。两者配合后，F3 可以同时具备 Agent 的灵活性和系统流程的确定性。

### 3.6 Skill 设计

#### 做什么

定义 `ResolutionAgent` 在 F3 阶段使用的内部 skills 及其职责分工。

#### 怎么做


4 个 skills 均作为 Agent 内部能力存在，由单次 Agent 运行按需激活。

#### 1. `Intent Framing Skill`

做什么：

- 判断用户是否在发起分析请求
- 提取用户关注点
- 判断当前输入是否属于一期范围

怎么做：

- 每轮自然语言输入必跑
- 输出：
  - 是否分析请求
  - 是否单股票场景
  - 用户目标
  - 关注点

#### 2. `Security Grounding Skill`

做什么：

- 从自然语言中提取股票线索

怎么做：

- 提取：
  - 显式 ticker 线索
  - 公司名线索
  - 市场提示
  - 排除条件
- 决定是否调用 `search_stock_candidates`

#### 3. `Disambiguation Skill`

做什么：

- 判断当前最优动作是确认、候选选择还是继续提问

怎么做：

- 只有一个高置信候选时：
  - 输出 `need_confirm`
  - 或直接 `confirmed`
- 多个合理候选时：
  - 输出 `need_disambiguation`
- 信息不足时：
  - 输出 `collect_more`

#### 4. `Confirmation Packaging Skill`

做什么：

- 将内部决策包装成前端可消费结果

怎么做：

- 输出：
  - `assistantReply`
  - `stock`
  - `candidates`
  - `status`
  - `shouldCreateAnalysisTask`
  - `terminate`

#### 边界与约束

- skills 作为 Agent 内部能力存在，不对外暴露为独立接口
- skills 不替代 `ResolutionService` 的状态控制、门禁和持久化职责
- skills 的目标是提升判断质量，不改变 F3 的业务边界和一期范围

### 3.7 Tools 设计

#### 做什么

定义 Agent 在 F3 阶段需要使用的外部工具能力。

#### 怎么做

定义 Agent 的外部工具能力。一期 tools 统一保留两个。

#### Tool 1：`search_stock_candidates`

- 根据用户股票线索召回候选股票

输入：

```json
{
  "query": "苹果",
  "marketHints": ["US"],
  "limit": 5
}
```

输出：

```json
{
  "candidates": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "market": "US",
      "exchange": "NASDAQ",
      "aliases": ["Apple", "苹果"],
      "score": 0.97,
      "assetType": "stock"
    }
  ]
}
```

技术选型：

- 由 `StockLookupGateway` 提供
- MVP 优先使用：
  - `tushare stock_basic / hk_basic / us_basic`
- 补充来源采用：
  - `futu get_stock_basicinfo(market=...)`

内部依赖：

- `ResolutionService` 只依赖 gateway
- `StockLookupGateway` 负责调用 `tradingagents`
- `tradingagents` 负责 vendor 接入与 symbol 归一化

边界处理：

- 一期搜索逻辑统一由 `ta_service` 服务侧完成：
  - 名称匹配
  - 市场过滤
  - 候选排序
  - 去重
- 后续若需要更强搜索质量，方案扩展为内部 `stock_master` 或缓存索引层

#### Tool 2：`get_stock_profile`

- 查询候选股票的标准资料

输入：

```json
{
  "ticker": "AAPL"
}
```

输出：

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "market": "US",
  "exchange": "NASDAQ",
  "assetType": "stock",
  "isActive": true,
  "aliases": ["Apple", "苹果"]
}
```

#### 边界与约束

- tools 只用于访问外部股票数据能力
- 显式 ticker 提取、候选判断、确认文案和范围校验由 Agent 或 Service 内部承担
- 一期 tools 数量控制在最小闭环范围内，不扩展为通用工具集

### 3.8 出错处理

#### 做什么


规定 `resolution` 阶段的失败、超限和超范围处理方式。

#### 怎么做


#### 场景 1：tool 调用失败

处理方式：

- Agent 输出 `failed`
- `ResolutionService` 返回明确失败提示

示例文案：

- `我暂时无法完成股票候选查询。请稍后重试，或直接输入公司全名或标准 ticker。`

#### 场景 2：超过最大轮次

处理方式：

- 超过 `2` 轮仍未确认时，当前 `resolution` 结束
- 系统返回清晰补充指引

示例文案：

- `我暂时还无法准确定位你想分析的股票。请直接提供公司全名或标准 ticker，例如 AAPL、0700.HK、300750.SZ。`

#### 场景 3：输入超出一期范围

处理方式：

- Agent 输出 `unsupported`
- `ResolutionService` 返回范围说明

示例文案：

- `当前一期支持单股票分析。请告诉我你想分析的具体股票名称或 ticker。`

#### 边界与约束

- 出错处理以明确结束当前轮次和返回清晰提示为目标
- 错误场景不允许绕过确认流程直接进入正式分析
- 一期仅收敛到 `failed` 和 `unsupported` 等稳定状态，不扩展复杂补偿流程

### 3.9 可观测性

#### 做什么

定义 `resolution` 的日志和指标方案。

#### 怎么做

#### 日志

记录：

- `resolutionId`
- `conversationId`
- 当前轮次
- 用户原始输入
- 工具调用摘要
- 最终结构化输出
- 异常信息

#### 指标

统计：

- `resolved_rate`
- `need_confirm_rate`
- `need_disambiguation_rate`
- `not_found_rate`
- `unsupported_rate`
- `avg_rounds_to_confirm`
- `avg_latency_ms`

#### 边界与约束

- 可观测性以定位主链路问题为目标，不记录模型完整推理内容
- 日志与指标围绕 `ResolutionService`、tools 调用和最终状态收敛设计
- 一期优先满足问题定位和评估需求，不引入重型观测平台设计

### 3.10 测试与评估

#### 做什么

定义一期测试范围和效果评估方式。

#### 怎么做

#### 单元测试

覆盖：

- `ResolutionService`
  - 轮次限制
  - 改口清理
  - 结构化确认收尾
  - 候选合法性校验
- `StockLookupGateway`
  - 候选映射
  - 股票详情映射
  - vendor fallback 行为
- Agent 输出校验
  - schema 合法性
  - 状态字段合法性

#### 集成测试

覆盖场景：

1. 明确 ticker，直接收敛
2. 中文股票名，进入确认
3. 模糊简称，进入候选选择
4. 行业/主题输入，返回范围提示
5. 超过 `2` 轮，进入兜底结束
6. 用户点击确认后，Service 直接结束 resolution
7. 会话进入 `ready_to_analyze` 后，前端创建正式分析任务

#### 评估指标

关注：

- 首轮命中率
- 平均确认轮次
- 候选正确率
- 误识别率
- 平均响应时间
- tool 失败率

#### 边界与约束

- 测试目标是验证 F3 闭环和状态迁移正确性，不下沉到代码级实现细节
- 评估重点放在识别收敛能力、流程稳定性和分析前门禁有效性
- 二期增强项如搜索质量和排序优化以效果评估结果为后续输入

## 4. 验收标准

- 用户提交自然语言分析诉求后，系统能够返回以下之一：补充提示、唯一候选确认、候选列表、范围提示或失败提示
- 系统能够在正式分析任务创建前完成股票标的识别与确认闭环
- 用户点击确认按钮或候选项后，`ResolutionService` 能够不重新触发 Agent 而直接完成收尾
- 当前会话只有进入 `ready_to_analyze` 后，前端才进入正式分析任务创建链路
- `ResolutionService` 能够通过 `pendingResolution` 支持页面刷新后的状态恢复和结构化确认处理
- 系统能够拦截旧 `resolutionId`、非法候选项和重复确认请求，保持流程一致性
- 当输入超出一期范围时，系统能够稳定返回范围提示，并保持在 F3 支持边界内
- 当工具失败或超过最大澄清轮次时，系统能够稳定结束当前 `resolution` 并返回兜底提示
- 文档中定义的职责边界、依赖方向、接口契约、状态机和验收标准能够支持前后端按同一方案推进实现

