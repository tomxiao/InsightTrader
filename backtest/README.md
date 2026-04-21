# backtest 目录说明

`backtest/` 是 `InsightTrader` 的报告驱动回测模块。

它只负责这几件事：

- 批量生成历史 `lite team` 报告
- 从 `2_decision/summary.md` 解析结构化信号
- 按最小执行规则回放买卖信号
- 输出回测统计、结果图和实验汇总
- 支持按“实验主题 / round”组织多标的调优

## 目录职责

- [generate_report_batch.py](/D:/CodeBase/InsightTrader/backtest/generate_report_batch.py)
  - 生成历史报告批次
  - 支持 `full_round` 和 `decision_only_round`

- [run_report_backtest.py](/D:/CodeBase/InsightTrader/backtest/run_report_backtest.py)
  - 读取一批 `summary.md`
  - 执行回测
  - 产出 `signals.csv / trades.csv / summary.json / *-bt.png`

- [report_parser.py](/D:/CodeBase/InsightTrader/backtest/report_parser.py)
  - 解析 `建议行动 / 截面价格 / 入场方式 / 失效条件`

- [execution_rules.py](/D:/CodeBase/InsightTrader/backtest/execution_rules.py)
  - 定义最小执行规则
  - 当前是多头回放模型，`sell` 用于平已有多仓，不开空

- [render_backtest_chart.py](/D:/CodeBase/InsightTrader/backtest/render_backtest_chart.py)
  - 绘制结果图

- [label_signal_cases.py](/D:/CodeBase/InsightTrader/backtest/label_signal_cases.py)
  - 给信号打 `good / bad / unclear` 标签

- [summarize_experiment.py](/D:/CodeBase/InsightTrader/backtest/summarize_experiment.py)
  - 汇总一轮实验的跨标的结果

- [init_experiment.py](/D:/CodeBase/InsightTrader/backtest/init_experiment.py)
  - 初始化实验 round 目录骨架

- [EXPERIMENT_RUNBOOK.md](/D:/CodeBase/InsightTrader/backtest/EXPERIMENT_RUNBOOK.md)
  - 多标的实验的唯一执行手册
  - 包含主题定义、目录规范、命令示例、结果分析与调优方法

## 当前工作流

当前 `backtest/` 已经统一到主题目录工作流：

- 新 round 的报告、回测结果、图表产物
- 只能落在  
  `backtest/experiments/<theme>/rounds/<round>/reports/<ticker>/<batch>/`

`backtest/` 下不再使用独立的 `output/` 作为正式输出路径。

## 如何执行

执行方法、命令示例、目录规范、结果阅读顺序、调优方法，统一看：

- [EXPERIMENT_RUNBOOK.md](/D:/CodeBase/InsightTrader/backtest/EXPERIMENT_RUNBOOK.md)
