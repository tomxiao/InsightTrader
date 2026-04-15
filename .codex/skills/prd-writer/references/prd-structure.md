# PRD Structure

Use this as the default section order for InsightTrader-style PRDs.

## 1. 文档信息

- 文档名称
- 版本
- 当前方案
- 文档类型
- 面向对象
- 适用范围

## 2. 背景与问题定义

- 当前版本基础能力
- 当前问题
- 根因判断
- 本次改版定位

Write this section so a reader understands:
- what already exists,
- what is broken or insufficient,
- why the problem matters,
- and what kind of change this version is making.

## 3. 产品定位

Restate the stable product definition in one concise sentence, then list the perception or experience emphasis for this version.

## 4. 目标与非目标

Split clearly:
- 产品目标: what this version must improve
- 非目标: what this version explicitly does not attempt

Non-goals should be concrete enough to stop scope creep.

## 5. 适用范围与影响范围

Cover:
- 适用范围
- 受影响模块 or 受影响页面
- 不受影响范围

If engineering alignment matters, name files, services, or modules directly.

## 6. 角色与术语定义

Define:
- user-facing roles
- system roles
- message types
- task states
- domain-specific terms

Only define terms that are used repeatedly or can cause interpretation drift.

## 7. 需求原则

List the guiding principles that should shape detailed decisions. These are not slogans; they should be testable against later requirements.

## 8. 功能范围 or 功能需求总览

Summarize the feature items included in this version.

Use stable identifiers like `F6`, `F7`, `F8` when multiple requirements coexist.

## 9. 详细功能需求

This is the core of the document.

For each feature, prefer a pattern like:
- 需求目标
- 功能规则
- 展示要求 / 交互要求 / 行为规则
- 状态机要求
- 文案规则
- 数据要求
- 边界约束

Use tables when mappings are easier to understand than prose:
- message type -> UI role
- stage_id -> business stage
- node_id -> display meaning
- field -> meaning -> required

## 10. 页面与交互影响

Describe:
- whether new pages are added
- which page or flow changes
- message or task flow rules
- history replay / return-to-page behavior if applicable

## 11. 后端能力要求

Use this when backend behavior must change to satisfy the requirement.

Describe:
- service or agent responsibilities
- context or data needs
- state transition obligations
- event or API expectations

## 12. 前端能力要求

Use this when frontend must carry distinct rendering or interaction constraints.

Describe:
- default display strategy
- component or layout expectations
- rhythm/readability constraints
- compatibility with future structured payloads if needed

## 13. 验收标准

Separate:
- 功能验收
- 体验验收

Acceptance points should be observable and close to test cases.

## 14. 风险与注意事项

List failure modes that could produce false optimization or ambiguous implementation.

Good examples:
- shorter but emptier answers
- technically correct but user-confusing wording
- broken status consistency
- backend/frontend contract drift

## 15. 版本结论

Close with one concise statement that defines the essence of the version.

Use this section to make the version memorable, not to restate the whole document.
