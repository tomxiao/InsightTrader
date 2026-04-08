# Data Source Lab

本目录是一个用于评估候选金融数据源的实验区，在将其正式接入 `tradingagents/dataflows/` 之前，先在这里完成能力验证、适配判断和文档沉淀。

## 目标

针对每一个候选数据源，明确以下问题：

1. 它覆盖哪些市场
2. 它能提供哪些数据项
3. 它的输出能否被规范化为 TradingAgents 现有工具所需的数据形态
4. 哪些分析 Agent 可以安全地消费这些数据

## 当前 TradingAgents 的输入分类

这些分类来自 `tradingagents/dataflows/interface.py`，定义了系统当前对数据源的输入期望：

- `core_stock_apis`: 通过 `get_stock_data` 提供 OHLCV 行情历史
- `technical_indicators`: 通过 `get_indicators` 提供技术指标时间序列
- `fundamental_data`: 通过 `get_fundamentals`、`get_balance_sheet`、`get_cashflow`、`get_income_statement` 提供公司概览与财务报表
- `news_data`: 通过 `get_news`、`get_global_news`、`get_insider_transactions` 提供个股新闻、宏观新闻和内幕交易数据

## Agent 适配判断标准

验证一个数据源时，应当按照各 Agent 的真实需求来判断：

- 市场分析 Agent 需要：
  - OHLCV 历史数据
  - 足够的字段用于本地计算技术指标，或直接提供可规范化的指标
- 基本面分析 Agent 需要：
  - 公司资料 / 公司概览
  - 资产负债表
  - 现金流量表
  - 利润表
- 新闻分析 Agent 需要：
  - 能按 ticker 过滤的新闻
  - 宏观 / 全球新闻
  - 可选的内幕交易数据

## 目录结构

- `sources/`: 每个候选数据源一个独立的 Markdown 文档
- `matrices/coverage_matrix_template.csv`: 对比数据源在市场和数据项维度上的覆盖情况
- `matrices/agent_fit_template.csv`: 对比数据源与 Agent / 工具的适配关系
- `templates/source_profile_template.md`: 单个数据源的详细模板
- `templates/agent_input_checklist.md`: 判断某个数据源是否可供现有 Agent 使用的检查清单

## 验证规则

建议优先围绕以下问题验证每一个数据源：

1. 市场覆盖：
   - A股
   - 港股
   - 美股
   - ETF / 指数
   - 宏观数据
2. 工具覆盖：
   - `get_stock_data`
   - `get_indicators`
   - `get_fundamentals`
   - `get_balance_sheet`
   - `get_cashflow`
   - `get_income_statement`
   - `get_news`
   - `get_global_news`
   - `get_insider_transactions`
3. 输出规范化：
   - 是否能返回表格化的 OHLCV？
   - 是否能以稳定的行列结构返回财务报表？
   - 是否能返回可读的文本摘要或元数据？
4. 运行适配性：
   - 是否需要 API Key？
   - 是否有限频？
   - 是否有付费分层？
   - 服务是否稳定 / 是否官方？
   - 是否值得做缓存？

## 服务稳定性约束

当两个数据源在能力覆盖上看起来接近时，优先选择服务更稳定的那个。

当前在评估中应当作为事实约束使用的稳定性先验排序为：

1. `tushare`
2. `futu`
3. `finnhub`
4. `akshare`

解释如下：

- 从服务稳定性视角看，排序为 `tushare > futu > finnhub > akshare`
- 这个约束应影响能力接近时的取舍、`production_risk` 标注以及 fallback 顺序设计
- 除非某个具体工作流已经有直接验证证据，否则不要用“功能更广”去覆盖这个稳定性排序

## 期望输出形态

当一个数据源被标记为“可供 Agent 使用”时，意味着它的数据可以被转换成以下现有形态之一：

- OHLCV：带表头的类 CSV 表格文本
- 技术指标：带日期的指标值序列和指标说明
- 基本面概览：可读的键值对文本块
- 财务报表：带表头的类 CSV 报表表格
- 新闻：包含标题、来源、日期、链接等信息的可读文章列表

不要把“接口可调用”直接等同于“可用”。只有当该数据源的结果可以在不过度依赖临时 Prompt 处理的前提下，稳定规范化为上述形态时，才应被标记为兼容。

## 验证结论

验证日期：`2026-04-09`

下表是当前关于“按市场与数据项选择单一最佳数据源”的验证结论。该结论优先依据已验证能力，其次在能力接近时使用当前稳定性约束 `tushare > futu > finnhub > akshare` 做裁决。

| 数据项 | 项说明 | Agent | A股 | 港股 | 美股 |
| --- | --- | --- | --- | --- | --- |
| `get_stock_data` | OHLCV 价格历史，提供开盘价、最高价、最低价、收盘价、成交量等基础行情 | `market_analyst` | `tushare` | `tushare` | `tushare` |
| `get_indicators` | 技术指标时间序列，通常由 OHLCV 在本地派生 | `market_analyst` | `tushare` | `tushare` | `tushare` |
| `get_fundamentals` | 公司概览、关键财务指标和基础面摘要 | `fundamentals_analyst` | `tushare` | `akshare` | `finnhub` |
| `get_balance_sheet` | 资产负债表 | `fundamentals_analyst` | `tushare` | `akshare` | `finnhub` |
| `get_cashflow` | 现金流量表 | `fundamentals_analyst` | `tushare` | `akshare` | `finnhub` |
| `get_income_statement` | 利润表 / 收益表 | `fundamentals_analyst` | `tushare` | `akshare` | `finnhub` |
| `get_news` | 个股相关新闻、公司相关新闻流 | `news_analyst` | `tushare` | `tushare` | `finnhub` |
| `get_global_news` | 宏观、全球或市场层面的新闻流 | `news_analyst` | `tushare` | `tushare` | `finnhub` |
| `get_insider_transactions` | 内幕交易、高管交易或内部人交易记录 | `news_analyst` | `无` | `无` | `finnhub` |

### 解释说明

- A股在当前验证结果下，市场数据和基本面数据都最适合映射到 `tushare`
- 港股在当前验证结果下，行情优先 `tushare`，而基本面覆盖当前以 `akshare` 更强
- 美股在当前验证结果下，行情仍默认使用 `tushare`，但基本面、新闻和内幕交易最适合映射到 `finnhub`
- 该表刻意只选择每个单元格中的一个“最佳数据源”，不定义 fallback
- 如果后续某个数据源新增了经过验证的能力，这份结论应随之更新，而不应被视为永久不变
