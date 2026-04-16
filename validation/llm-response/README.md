# LLM Response Lab

本目录用于重放固定的 LLM 输入用例，并横向对比不同模型供应商的响应结果，为后续模型选型提供可复核的基础样本。

## 目标

当前首版聚焦 3 个 `research.debate` 输入用例，对比以下供应商：

- `DeepSeek`
- `Qwen`
- `MiniMax`

每次运行都会保存：

- 原始响应文本
- 请求耗时
- token 用量
- 错误信息
- 汇总 JSONL / CSV / Markdown

## 目录结构

- `cases/research_debate_cases.json`: 固定用例清单
- `configs/providers.json`: 供应商与模型配置
- `llm_response_lab/`: Python 实现
- `outputs/<timestamp>/`: 每次运行的结果目录
- `run_validation.py`: 批量执行入口

## 环境变量

运行前需要配置对应 API Key：

- `DEEPSEEK_API_KEY`
- `DASHSCOPE_API_KEY`
- `MINIMAX_API_KEY`

## 默认模型与端点

默认配置定义在 `configs/providers.json`：

- `DeepSeek`: `https://api.deepseek.com/v1`, model=`deepseek-chat`
- `Qwen`: `https://dashscope.aliyuncs.com/compatible-mode/v1`, model=`qwen-max-latest`
- `MiniMax`: `https://api.minimaxi.com/anthropic`, model=`MiniMax-M2.7`

如需切换模型或端点，可直接修改该配置文件。

## 运行方式

在仓库根目录执行：

```bash
python "validation/llm-response-lab/run_validation.py"
```

也可以显式指定清单与配置：

```bash
python "validation/llm-response-lab/run_validation.py" \
  --cases "validation/llm-response-lab/cases/research_debate_cases.json" \
  --providers "validation/llm-response-lab/configs/providers.json"
```

## 输出说明

每次运行会写入 `outputs/<timestamp>/`，包含：

- `results.jsonl`: 每次调用一行完整结果
- `summary.csv`: 方便筛选排序的平铺结果
- `summary.md`: 面向阅读的运行简报
- `responses/<case_id>/<provider>.md`: 各 case 的原始响应

## 设计说明

- `DeepSeek` 与 `Qwen` 都通过 OpenAI-compatible Chat Completions 接口访问
- `MiniMax` 通过 Anthropic-compatible 接口访问
- 该子项目不依赖主 CLI 流程，避免 `openai` provider 默认 `Responses API` 假设对第三方端点造成干扰
- 首版只做原始响应与基础指标对比，不做自动评分
