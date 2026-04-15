# Mobile Chat Frontend v1.1 测试验收方案

## 1. 文档目的

本文档用于说明移动端 H5 会话页 v1.1 的测试验收方式、自动化覆盖范围、执行结果与残余风险。

本方案以“尽量不依赖人工浏览器走查”为原则，将可验证的需求尽可能落成自动化检查与测试用例。

## 2. 适用范围

本次验收范围对应 [mobile-chat-frontend-prd-v1.1.md](./mobile-chat-frontend-prd-v1.1.md) 中的以下需求：

- F6：小I 对话角色统一化
- F7：消息元信息紧凑化
- F8：投资团队工作进度反馈增强

主要覆盖对象：

- 移动端 H5 当前会话页
- `text`、`ticker_resolution`、`insight_reply`、`summary_card`、`error` 五类系统消息展示
- `task_status` 主卡片与时间线展示
- 前后端任务状态映射与返回契约

## 3. 验收原则

### 3.1 总体原则

- 优先使用自动化手段验证功能正确性与展示逻辑
- 将体验要求尽可能转译为可断言的页面规则
- 对无法完全自动化验证的视觉观感项，单独列为残余风险

### 3.2 验收分层

本次验收分为三层：

1. 前端页面级自动化验收
2. 前端静态校验
3. 后端状态映射与契约测试

## 4. 自动化验收设计

### 4.1 前端页面级验收

测试文件：

- [ConversationPage.test.ts](/D:/CodeBase/InsightTrader/mobile_h5/src/views/conversation/__tests__/ConversationPage.test.ts)

覆盖点如下：

1. `小I` 统一展示
   - `text`
   - `ticker_resolution`
   - `insight_reply`
   - `summary_card`
   - `error`

2. 消息元信息规则
   - 角色与时间戳处于同一行
   - 不再出现“标的确认”“研究结果”等冗余眉标题

3. `task_status` 单卡片规则
   - 多条阶段状态只渲染为一张主卡片
   - 启动阶段的泛化 `task_status` 不进入最终展示
   - 卡片内保留阶段时间线

4. `task_status` 状态规则
   - 分析进行中显示进行态和时间信息
   - 分析完成后转为完成态
   - 完成后不再保留当前阶段高亮

5. 文案规则
   - `Trader` 节点文案为“交易分析师输出交易方案与执行思路”

### 4.2 前端静态校验

命令：

```bash
npm run type-check
```

目的：

- 校验 Vue 模板与 TypeScript 类型一致性
- 避免因空值、模板分支或状态字段变更导致编译级问题

### 4.3 后端状态映射与契约测试

测试文件：

- [test_ta_service_status_mapper.py](/D:/CodeBase/InsightTrader/tests/test_ta_service_status_mapper.py)
- [test_ta_service_conversations_contracts.py](/D:/CodeBase/InsightTrader/tests/test_ta_service_conversations_contracts.py)

覆盖点如下：

1. `stageId` 文案映射
2. `nodeId` 文案映射
3. `displayState` 的 `active / stalled / done / failed`
4. `build_task_progress` 的字段组装
5. `report_ready / failed` 状态下任务快照保留

命令：

```bash
pytest tests/test_ta_service_status_mapper.py tests/test_ta_service_conversations_contracts.py
```

## 5. 执行结果

执行日期：

- 2026-04-15

执行结果：

1. 前端页面级验收
   - `npm run test -- src/views/conversation/__tests__/ConversationPage.test.ts`
   - 结果：`4 passed`

2. 前端静态校验
   - `npm run type-check`
   - 结果：通过

3. 后端状态映射与契约测试
   - `pytest tests/test_ta_service_status_mapper.py tests/test_ta_service_conversations_contracts.py`
   - 结果：`8 passed`

## 6. 本次验收覆盖后的结论

根据当前自动化验收结果，可以得出以下结论：

- v1.1 核心功能开发已完成
- 可自动验证的关键需求已通过验收
- 当前版本具备进入提测的条件

建议对外口径：

`v1.1 开发完成，自动化验收通过，进入提测阶段。`

## 7. 残余风险

以下项目未被本次自动化验收完全覆盖：

- 不同真机尺寸下的细微视觉差异
- 动效强弱的主观体验
- 极端视口下的间距与密度观感
- 长时间真实轮询过程中的体感流畅度

说明：

上述风险不影响当前“可提测”判断，但在正式上线前，仍建议安排一次轻量人工体验确认。

## 8. 后续建议

建议在后续版本继续补充：

1. `ConversationPage` 更细粒度的组件交互测试
2. `task_status` 时间线更多边界状态测试
3. 结果卡片与继续追问场景的回归用例
4. 真机或截图基线类视觉回归能力
