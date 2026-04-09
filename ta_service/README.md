# ta_service

`ta_service` 是面向 `mobile_h5` 一期产品的后端骨架，采用同仓库 Python 顶层包方案，内部复用 `tradingagents` 作为分析引擎。

## 当前范围

- FastAPI 应用工厂与 REST 路由骨架
- MongoDB / Redis 客户端接入
- 会话、任务、报告的最小 repository / service 分层
- `TradingAgentsRunner` 运行适配层
- 单任务单进程的分析 task runner

## 已提供的接口骨架

- `POST /auth/login`
- `GET /auth/me`
- `POST /analysis/tasks`
- `GET /analysis/tasks/{taskId}/status`
- `GET /reports/{id}/detail`
- `POST /conversations`
- `GET /conversations`
- `GET /conversations/{id}`
- `POST /conversations/{id}/messages`（预留）

## 运行要求

- 本地 MongoDB
- 本地 Redis
- Python 依赖需包含 `fastapi`、`uvicorn`、`pymongo`、`redis`

## 环境变量

- `TA_SERVICE_HOST`
- `TA_SERVICE_PORT`
- `TA_SERVICE_API_PREFIX`
- `TA_SERVICE_MONGO_URI`
- `TA_SERVICE_MONGO_DB`
- `TA_SERVICE_REDIS_URL`
- `TA_SERVICE_REDIS_LOCK_PREFIX`
- `TA_SERVICE_REDIS_LOCK_TTL_SECONDS`
- `TA_SERVICE_RESULTS_DIR`
- `TA_SERVICE_AUTH_TOKEN_PREFIX`
- `TA_SERVICE_DEFAULT_OUTPUT_LANGUAGE`

说明：
- `ta_service` 启动时会自动加载仓库根目录 `.env`
- `llm_provider`、模型选择、`data_vendors`、`market_routing_enabled` 默认由 `tradingagents/default_config.py` 决定
- `ta_service` 不再覆盖 `TradingAgents` 的 LLM 与数据源配置

## 本地启动

API:

```bash
python -m ta_service.main
```

## 当前约束

- 鉴权仍是开发态占位实现，后续需接入正式登录体系
- `POST /conversations/{id}/messages` 仅预留，下一步再与 `mobile_h5` 的会话契约对齐
- 分析任务由 API 直接拉起一次性 task runner，任务结束后进程自然退出
- 任务执行已具备 `TradingAgents` 运行适配骨架，但还未做完整阶段事件回填与取消控制
