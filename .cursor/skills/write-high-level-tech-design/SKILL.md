---
name: write-high-level-tech-design
description: Write high-level technical design documents for PRD features and engineering方案. Use when drafting 技术方案, 高阶设计, 架构方案, 工程设计文档, feature implementation plans, or when the user asks to沉淀/重写/规范技术方案文档. Focus on decisions, constraints, boundaries, and implementation approach; avoid code-level implementation details and discussion history.
---

# Write High-Level Technical Design

## Purpose
Produce a high-level technical design document for a product feature or PRD item.
The document should support decision-making, implementation alignment, and review.

## Default positioning
- Treat the document as high-level design, not code design.
- Focus on decisions, constraints, boundaries, dependencies, and implementation approach.
- Keep the document oriented around the feature, not a single technical component.
- Prefer the PRD feature name as the document theme and title.
- Default to Chinese unless the user explicitly asks for another language.

## Use this skill when
- The user asks for a 技术方案, 高阶设计, 架构方案, 工程设计文档, or 实现方案.
- The task is to rewrite or normalize an existing design doc.
- The user wants a reusable, review-friendly document instead of exploratory notes.
- The design needs to cover a PRD feature end to end across frontend, backend, state, protocol, and system boundaries.

## Document rules
- Keep only final conclusions.
- Do not include discussion history, back-and-forth comparisons, meeting-note style content, or unresolved brainstorming.
- Do not drift into code-level implementation unless the user explicitly asks for lower-level design.
- Do not make the document read like a task breakdown or coding to-do list.
- State the recommended route directly. If alternatives matter, mention only the chosen route and the reason it is chosen.

## Required chapter structure
Use exactly these top-level chapters unless the user explicitly asks for a different structure:

1. `设计目标`
2. `设计原则`
3. `具体方案`
4. `验收标准`

## Chapter guidance

### `设计目标`
- State what feature problem is being solved.
- State the scope of this phase.
- State the desired product and engineering outcome.

### `设计原则`
- State the core constraints and architectural rules.
- Emphasize boundaries, ownership, reuse strategy, and control points.
- Prefer short, directive statements.

### `具体方案`
- Organize this chapter by key implementation tasks, not by abstract theory.
- Typical task sections include:
  - 接口
  - 协议
  - 调用时序
  - 状态机
  - 数据流或依赖关系
  - 错误处理
  - 可观测性
  - 测试与评估
- Use only the tasks that matter for the current feature.

For each task section, default to this structure:

#### 做什么
- Define the task's purpose in the full feature.

#### 怎么做
- State the chosen solution directly.
- Cover technical direction, system integration, and collaboration between components.

#### 边界与约束
- State ownership boundaries.
- State what must be guaranteed by the system.
- State the current phase scope and stopping point where necessary.

### `验收标准`
- Make acceptance criteria observable and testable.
- Use statements that can be verified through behavior, state transition, API response, or review.
- Avoid vague wording such as “体验良好”, “方案完整”, or “系统稳定”.

## Writing guidance
- Write in a review-friendly style.
- Prefer concise sections and direct statements.
- Use consistent terminology throughout the document.
- Keep the feature as the primary subject; mention technical components as supporting design elements.
- When the design spans multiple layers, explicitly state:
  - dependency direction
  - ownership boundaries
  - upstream/downstream handoff points

## Default exclusions
Unless the user explicitly asks for deeper design, do not include:
- code snippets
- class or method signatures
- file-level implementation plans
- field-level database schema
- pseudocode
- task decomposition checklists
- migration scripts
- commit plans

## Quality checklist
Before finalizing the document, verify:
- The title matches the PRD feature rather than a single internal component.
- The document reads as a final design, not a discussion record.
- The top-level structure is `设计目标 / 设计原则 / 具体方案 / 验收标准`.
- `具体方案` is organized by key tasks.
- Each key task uses `做什么 / 怎么做 / 边界与约束` unless the user asks for another structure.
- The document stays at high-level design depth.
- Acceptance criteria are concrete and verifiable.

## Output pattern
When drafting from scratch, use this skeleton:

```markdown
# <PRD功能名>技术方案 v1

## 1. 设计目标

## 2. 设计原则

## 3. 具体方案

### 3.1 <重点任务>

#### 做什么

#### 怎么做

#### 边界与约束

## 4. 验收标准
```
