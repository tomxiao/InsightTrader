# InsightTrader Mobile H5

`mobile_h5` 是 InsightTrader 的移动端 H5 前端，基于 `Vue 3 + Vite + TypeScript + Vant` 构建，主要提供以下能力：

- 登录与鉴权
- 当前会话页与历史会话抽屉
- 发起分析任务与轮询任务状态
- 查看完整报告
- 基础设置页

## 技术栈

- `Vue 3`
- `Vite`
- `TypeScript`
- `Vue Router`
- `Pinia`
- `Axios`
- `Vant`
- `Vitest`

## 目录结构

```text
mobile_h5/
  src/
    api/           接口封装
    components/    通用组件与业务组件
    composables/   组合式逻辑
    router/        路由定义与导航守卫
    stores/        Pinia 状态管理
    styles/        全局样式、变量、Vant 覆盖
    types/         类型定义
    utils/         工具方法与环境变量
    views/         页面级视图
```

## 页面说明

- `Login`：登录页
- `Conversation`：当前会话页，支持会话抽屉、消息流、任务状态和输入区
- `ReportReader`：完整报告阅读页
- `Settings`：设置页

路由定义位于 `src/router/index.ts`。

## 环境变量

当前前端支持以下环境变量：

- `VITE_API_BASE_URL`：后端 API 基地址，默认值为 `http://127.0.0.1:8100`
- `VITE_APP_NAME`：应用名称，默认值为 `InsightTrader Mobile`

环境变量读取逻辑位于 `src/utils/env.ts`。

可以在 `mobile_h5/.env.local` 中覆盖，例如：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8100
VITE_APP_NAME=InsightTrader Mobile
```

## 本地开发

### 1. 安装依赖

```bash
npm install
```

### 2. 启动后端

默认前端会请求 `http://127.0.0.1:8100`，因此本地开发时需要先启动主项目后端服务。

### 3. 启动前端

```bash
npm run dev
```

默认开发端口见 `vite.config.ts`，当前配置为：

- `host: 0.0.0.0`
- `port: 5175`

## 常用脚本

```bash
npm run dev
npm run build
npm run preview
npm run type-check
npm run test
```

含义如下：

- `dev`：启动 Vite 开发服务
- `build`：执行类型检查并产出构建结果
- `preview`：预览构建产物
- `type-check`：执行 `vue-tsc --noEmit`
- `test`：运行 `vitest`

## 接口与鉴权说明

- Axios 实例位于 `src/api/request.ts`
- 所有请求默认使用 `VITE_API_BASE_URL`
- 若本地存在登录态，会自动注入 `Bearer Token`
- 接口返回 `401` 时会清空登录态并跳回 `/login`

## UI 约定

- 全局视觉变量位于 `src/styles/variables.scss`
- 全局样式入口位于 `src/styles/index.scss`
- Vant 主题覆盖位于 `src/styles/vant-overrides.scss`
- 页面骨架组件位于 `src/components/layout/MobilePageLayout.vue`

## 适合补充的内容

如果后续要继续维护这个目录，建议再补充：

- 截图或页面录屏
- 后端接口清单
- 登录账号获取方式
- 打包与部署方式
- 常见问题排查
