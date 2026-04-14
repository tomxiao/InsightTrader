#!/bin/bash
cat > /opt/insighttrader/.env << 'EOF'
# ── ta_service 核心配置 ────────────────────────────────────────────────────────
TA_SERVICE_ENV=production
TA_SERVICE_HOST=0.0.0.0
TA_SERVICE_PORT=8100

# ── 数据库（Docker 内网服务名）────────────────────────────────────────────────
TA_SERVICE_MONGO_URI=mongodb://mongo:27017
TA_SERVICE_MONGO_DB=ta_service
TA_SERVICE_REDIS_URL=redis://redis:6379/0

# ── 安全 ──────────────────────────────────────────────────────────────────────
TA_SERVICE_AUTH_TOKEN_PREFIX=a4af310921fb070fcd4d4a19402df7c296b6fc45bae343277f757ee930ff7e0d

# ── 跨域 ──────────────────────────────────────────────────────────────────────
TA_SERVICE_CORS_ORIGINS=https://93901.pro,https://www.93901.pro

# ── 任务配置 ──────────────────────────────────────────────────────────────────
TA_SERVICE_ANALYSIS_TASK_TTL_SECONDS=1800
TA_SERVICE_LOG_LEVEL=INFO
TA_SERVICE_REPORTS_DIR=./reports

# ── LLM ───────────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY=sk-549765764f4c475c9c283e5df5d6be7f
MINIMAX_API_KEY=
DASHSCOPE_API_KEY=

# ── 数据源 ────────────────────────────────────────────────────────────────────
TUSHARE_TOKEN=ea69c88db6a454da49269ff93783b1ec7d3e5224ddcb24e92b427d7c
FINNHUB_TOKEN=d6p2ol9r01qk3chimcbgd6p2ol9r01qk3chimcc0
EOF
echo ".env written"
