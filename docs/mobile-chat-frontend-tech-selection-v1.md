# frontend_mobile 技术选型说明 v1

## 1. 文档目的

本文档用于明确 `frontend_mobile` 的一期技术选型、工程边界与实施原则。

本文档服务于以下目标：

- 为移动端前端一期提供稳定、保守、可快速交付的技术方案
- 明确 `frontend_mobile` 与现有桌面端 `frontend` 的边界
- 避免后续在开发、测试、构建和运行阶段出现“共用工程”或“隐式依赖”的混乱

## 2. 结论

`frontend_mobile` 一期采用以下保守版技术选型：

- `Vue 3`
- `Vite`
- `TypeScript`
- `Vue Router`
- `Pinia`
- `Axios`
- `Vant`
- `@vueuse/core`
- `SCSS`
- `CSS Variables`
- `marked`（仅用于完整报告阅读层的 Markdown 渲染）

该方案目标是：

- 界面简洁
- 首屏和交互响应快
- 多型号手机和主流手机浏览器适配稳定
- 与当前团队已有 Vue 技术经验保持一致

## 3. 硬约束声明

### 3.1 与桌面端 `frontend` 无任何依赖

`frontend_mobile` 必须作为一个**完全独立的前端工程**存在，并严格遵守以下原则：

- 不依赖桌面端 `frontend` 的源码
- 不依赖桌面端 `frontend` 的组件、布局、样式、路由、store 或工具函数
- 不依赖桌面端 `frontend` 的打包产物
- 不依赖桌面端 `frontend` 的构建流程
- 不依赖桌面端 `frontend` 的运行时环境

### 3.2 开发、测试、构建、运行完全独立

`frontend_mobile` 必须具备独立的：

- `package.json`
- 依赖安装
- 本地开发命令
- 测试命令
- 打包命令
- 运行命令
- 环境变量配置
- 部署输出目录

即：

- 开发独立
- 测试独立
- 构建独立
- 运行独立

### 3.3 禁止的实现方式

以下方式在一期中明确禁止：

- 将移动端页面直接加进现有桌面端 `frontend` 工程
- 在 `frontend_mobile` 中直接引用 `frontend/src/**`
- 共用桌面端 `frontend` 的路由配置
- 共用桌面端 `frontend` 的 UI 组件库封装层
- 共用桌面端 `frontend` 的布局系统
- 共用桌面端 `frontend` 的全局样式入口
- 将 `frontend_mobile` 作为桌面端 `frontend` 的子路由或子模块开发

## 4. 为什么采用保守版技术选型

## 4.1 继续使用 Vue 生态

当前项目桌面端已使用 Vue 3 技术栈，团队已有相关经验。移动端继续采用 Vue 3，可以降低以下成本：

- 技术学习成本
- 接口联调成本
- 状态管理理解成本
- 工程搭建与排错成本

但这里的“继续使用 Vue 生态”仅指技术范式一致，不代表工程复用或代码耦合。

## 4.2 使用 Vite

选择 `Vite` 的原因：

- 本地开发启动快
- 热更新速度快
- 构建链条简单
- 与 Vue 3 配合成熟
- 适合单独开一个新的移动端工程

## 4.3 使用 Pinia

选择 `Pinia` 的原因：

- 轻量
- 官方推荐
- 与 Vue 3 组合自然
- 足以支撑登录态、用户信息、会话状态、任务状态等移动端一期需求

## 4.4 使用 Vant

移动端一期选择 `Vant` 作为基础交互组件库，原因如下：

- 面向移动 H5 场景
- 对主流手机浏览器兼容成熟
- 基础表单、弹层、菜单、提示类组件完备
- 比桌面管理台组件体系更适合当前产品形态

但需注意：

- `Vant` 只用于移动基础交互组件
- 页面骨架、聊天布局、执行摘要卡片、完整报告卡片等业务 UI 以自定义实现为主

## 5. 推荐技术栈说明

### 5.1 核心框架层

- `Vue 3`：页面与组件开发基础
- `TypeScript`：类型约束与接口契约清晰化
- `Vue Router`：登录页、当前会话页、完整报告阅读层等页面路由
- `Pinia`：登录态、用户信息、会话状态、任务状态管理

### 5.2 网络与通用能力

- `Axios`：请求封装
- `@vueuse/core`：常见组合式工具能力，如网络状态、节流、防抖、设备能力封装

### 5.3 UI 与交互层

- `Vant`：按钮、输入框、弹窗、抽屉、动作菜单、Toast、Loading、Skeleton 等基础交互

推荐使用 `Vant` 的场景：

- 登录表单
- Toast / Dialog
- 左侧抽屉容器
- 底部账户菜单
- 加载态 / 空态 / 错误态

不建议过度依赖 `Vant` 的场景：

- 当前会话页整体骨架
- 聊天气泡
- 执行摘要卡片
- 完整报告卡片
- 长文阅读层整体布局

### 5.4 样式层

推荐采用：

- `SCSS`
- `CSS Variables`

建议做法：

- 使用 CSS Variables 管理颜色、圆角、字号、间距、阴影
- 用 `flex` / `grid` 完成页面布局
- 重点处理底部安全区、键盘弹起、不同手机宽度适配

## 6. 适配与性能原则

## 6.1 适配原则

移动端一期要重点适配：

- iPhone Safari
- Android Chrome
- 微信内置浏览器
- 常见国产浏览器 WebView

布局策略建议：

- 流式布局优先，不采用设计稿等比缩放
- 重点覆盖 360px 到 430px 宽度区间
- 处理 `safe-area-inset-bottom`
- 处理键盘弹起后的输入区位置

## 6.2 性能原则

移动端一期必须优先保证：

- 首屏轻量
- 会话页响应快
- 长报告阅读时不卡顿

建议原则：

- 路由级懒加载
- 完整报告阅读层单独分包
- Markdown 渲染按需加载
- 不将复杂图表库纳入首包
- 不将桌面端重量级依赖带入移动端工程

## 7. 明确不采用的方案

一期明确不采用以下方案：

- `Nuxt / SSR`
- `Next.js`
- `Flutter Web`
- 继续以 `Element Plus` 作为移动端主 UI 方案
- 在桌面端 `frontend` 中直接扩展移动端路由和页面

原因包括：

- 会显著增加工程复杂度
- 不利于控制包体与移动端体验
- 不符合“完全独立工程”的硬约束

## 8. 推荐工程边界

建议将移动端前端单独建设为：

- `frontend_mobile`

建议该目录独立拥有：

- 自己的依赖声明
- 自己的 Vite 配置
- 自己的环境变量文件
- 自己的路由与页面目录
- 自己的 UI 组件目录
- 自己的样式入口
- 自己的构建输出目录

## 9. 推荐目录结构

建议 `frontend_mobile` 采用如下独立目录结构：

```text
frontend_mobile/
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  .env.development
  .env.production
  public/
  src/
    main.ts
    App.vue
    router/
      index.ts
    stores/
      auth.ts
      user.ts
      conversation.ts
      task.ts
    api/
      request.ts
      auth.ts
      analysis.ts
      reports.ts
      user.ts
    views/
      login/
        LoginPage.vue
      conversation/
        ConversationPage.vue
      report/
        ReportReaderPage.vue
      settings/
        SettingsPage.vue
    components/
      layout/
      conversation/
      report/
      common/
    composables/
      useAuth.ts
      useTaskStatus.ts
      useDraft.ts
      useSafeArea.ts
    utils/
      storage.ts
      format.ts
      env.ts
    styles/
      index.scss
      variables.scss
      reset.scss
      vant-overrides.scss
    types/
      auth.ts
      analysis.ts
      report.ts
```

### 9.1 目录设计原则

- 页面目录只服务移动端产品，不与桌面端目录对齐
- `api` 仅复用后端接口契约，不引用桌面端实现
- `stores` 只保存移动端真正需要的状态
- `components` 优先以业务模块分组，而不是沿用桌面后台组件分类
- `styles` 独立维护，禁止引用桌面端样式入口

## 10. 首批依赖清单

## 10.1 生产依赖

建议首批安装以下依赖：

- `vue`
- `vue-router`
- `pinia`
- `axios`
- `vant`
- `@vueuse/core`
- `marked`

### 10.2 开发依赖

建议首批安装以下开发依赖：

- `vite`
- `@vitejs/plugin-vue`
- `typescript`
- `vue-tsc`
- `sass`
- `unplugin-auto-import`
- `unplugin-vue-components`

### 10.3 一期不建议首批引入的依赖

以下依赖建议一期不要进入 `frontend_mobile` 首批依赖：

- `element-plus`
- `echarts`
- `vue-echarts`
- `mermaid`
- 与桌面端后台布局强绑定的任何 UI 依赖

## 11. 命令约定

`frontend_mobile` 必须拥有自己的命令体系，不得复用桌面端 `frontend` 命令。

### 11.1 推荐脚本

建议 `package.json` 至少包含：

- `dev`：本地开发
- `build`：生产构建
- `preview`：本地预览构建产物
- `type-check`：类型检查
- `lint`：代码检查
- `test`：自动化测试

### 11.2 推荐命令语义

建议采用以下约定：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview",
    "type-check": "vue-tsc --noEmit",
    "lint": "eslint . --ext .vue,.ts",
    "test": "vitest run"
  }
}
```

### 11.3 独立命令原则

- 运行移动端开发环境时，只进入 `frontend_mobile`
- 安装移动端依赖时，只在 `frontend_mobile` 内执行
- 打包移动端时，只构建 `frontend_mobile`
- 不允许通过桌面端 `frontend` 的命令间接触发移动端构建

## 12. 环境变量与运行约定

### 12.1 独立环境变量

`frontend_mobile` 应独立维护自己的环境变量文件，例如：

- `.env.development`
- `.env.production`

建议至少包含：

- `VITE_API_BASE_URL`
- `VITE_APP_NAME`
- `VITE_ENABLE_MOCK`（如后续需要）

### 12.2 独立运行约定

- 移动端本地开发端口独立
- 移动端构建输出目录独立
- 部署时作为独立前端静态站点或独立静态资源目录处理

## 13. 测试建议

### 13.1 一期测试层次

建议一期至少覆盖：

- 类型检查
- lint
- 基础组件/页面单测
- 关键用户流程冒烟测试

### 13.2 关键冒烟流程

建议优先验证以下流程：

1. 登录成功并进入当前会话页
2. 发起分析任务并看到运行中状态
3. 运行中输入内容后被保留为草稿
4. 分析完成后看到执行摘要卡片与完整报告卡片
5. 点击完整报告卡片进入独立阅读层

## 14. 与后端的关系

`frontend_mobile` 可以复用后端接口能力，但只允许复用**接口契约**，不允许复用桌面端前端实现。

允许复用的对象：

- 登录鉴权接口
- 分析任务接口
- 任务状态接口
- 报告详情接口
- 用户信息接口

不允许复用的对象：

- 桌面端 `frontend` 的 API 封装实现代码
- 桌面端 `frontend` 的页面或组件实现
- 桌面端 `frontend` 的 store 实现

## 15. 一期实施建议

一期按以下原则推进最稳妥：

1. 先搭建独立 `frontend_mobile` 工程
2. 先实现登录页、当前会话页、左侧抽屉、完整报告阅读层
3. 先完成基础 API 联调和移动端适配
4. 再逐步补齐状态恢复、草稿保留、长报告阅读体验

## 16. 最终结论

`frontend_mobile` 一期建议采用以下独立技术方案：

**Vue 3 + Vite + TypeScript + Vue Router + Pinia + Axios + Vant**

并严格执行以下工程原则：

**与桌面端 `frontend` 无任何依赖，开发、测试、构建、运行完全独立。**
