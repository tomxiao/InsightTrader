# Backtest Experiment Runbook

这份文档是实际执行手册。  
目标不是解释理念，而是回答一件事：

**下次要继续做回测实验时，按什么顺序、用什么脚本、看什么结果。**

相关文档分工：

- [README.md](/D:/CodeBase/InsightTrader/backtest/README.md)：单次 backtest 的基础执行说明
- [TUNING_WORKFLOW.md](/D:/CodeBase/InsightTrader/backtest/TUNING_WORKFLOW.md)：调优方法论与实验原则
- `EXPERIMENT_RUNBOOK.md`：具体怎么落地执行一轮实验

## 一轮实验的标准目标

一轮实验必须满足这几个条件：

- 有唯一实验目录
- 有固定样本池
- 有固定时间窗
- 有唯一主目标
- 有可复现的输出

不要在一轮里同时改很多东西。  
默认一轮实验只改一个方向，例如：

- 减少 `hold` 滥用
- 减少过早 `sell`
- 提高 `buy_on_pullback` 质量

## 当前推荐样本池

当前最小双市场样本池：

- `AXTI`
- `1347.HK`

当前推荐时间窗：

- `AXTI`: `2026-03-02` 到 `2026-04-07`
- `1347.HK`: `2026-03-01` 到 `2026-04-01`

默认频次：

- `daily`
- `step=1`

## 目录规范

实验目录统一放在：

```text
backtest/experiments/
```

每轮结构：

```text
backtest/experiments/<experiment_name>/
  experiment_meta.json
  compare.md
  compare_summary.json
  compare_summary.md
  tickers/
    AXTI/
      batch/
      result/
      notes.md
    1347.HK/
      batch/
      result/
      notes.md
```

说明：

- `batch/`：放该轮生成的历史报告批次信息
- `result/`：放回测产物、打标结果、图表
- `compare_summary.*`：跨标的实验汇总
- `notes.md`：该标的本轮结论

## 必用脚本

当前实验相关脚本：

- [init_experiment.py](/D:/CodeBase/InsightTrader/backtest/init_experiment.py)
- [generate_report_batch.py](/D:/CodeBase/InsightTrader/backtest/generate_report_batch.py)
- [run_report_backtest.py](/D:/CodeBase/InsightTrader/backtest/run_report_backtest.py)
- [label_signal_cases.py](/D:/CodeBase/InsightTrader/backtest/label_signal_cases.py)
- [summarize_experiment.py](/D:/CodeBase/InsightTrader/backtest/summarize_experiment.py)
- [render_backtest_chart.py](/D:/CodeBase/InsightTrader/backtest/render_backtest_chart.py)

## 标准执行顺序

### 1. 初始化实验目录

```powershell
.\.venv\Scripts\python.exe backtest\init_experiment.py `
  --name 2026-0421-round03 `
  --tickers AXTI,1347.HK `
  --start-date 2026-03-01 `
  --end-date 2026-04-07 `
  --sample-mode daily `
  --step 1
```

说明：

- `experiment_meta.json` 记录这轮实验元信息
- `tickers/<ticker>/batch` 和 `tickers/<ticker>/result` 会自动创建

### 2. 为每个 ticker 生成历史报告

#### AXTI

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-03-02 `
  --end-date 2026-04-07 `
  --sample-mode daily `
  --step 1
```

#### 1347.HK

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker 1347.HK `
  --start-date 2026-03-01 `
  --end-date 2026-04-01 `
  --sample-mode daily `
  --step 1
```

输出目录会落到：

```text
backtest/output/MMdd-HHmm-TICKER/
```

### 3. 如果生成中断，用 `--resume-dir` 续跑

不要新开批次，直接续跑原目录。

#### AXTI 示例

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-03-02 `
  --end-date 2026-04-07 `
  --sample-mode daily `
  --step 1 `
  --resume-dir backtest\output\0421-0119-AXTI
```

#### 1347.HK 示例

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker 1347.HK `
  --start-date 2026-03-01 `
  --end-date 2026-04-01 `
  --sample-mode daily `
  --step 1 `
  --resume-dir backtest\output\0421-0119-1347HK
```

规则：

- 遇到外部连接错误，优先续跑
- 不要丢弃已完成的批次
- 不要混用两个不同批次做同一轮回测

### 4. 用 manifest 批量跑回测

注意：

- 必须显式传 `--ticker`
- 否则脚本有可能从路径误推 ticker

#### AXTI

```powershell
$dir = 'D:\CodeBase\InsightTrader\backtest\output\0421-0119-AXTI'
$manifest = Import-Csv (Join-Path $dir 'report_manifest.csv')
$reports = @()
foreach ($row in $manifest) { $reports += @('--report', $row.decision_path) }
& .\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  @reports `
  --ticker AXTI `
  --end-date 2026-04-07 `
  --max-holding-days 60
```

#### 1347.HK

```powershell
$dir = 'D:\CodeBase\InsightTrader\backtest\output\0421-0119-1347HK'
$manifest = Import-Csv (Join-Path $dir 'report_manifest.csv')
$reports = @()
foreach ($row in $manifest) { $reports += @('--report', $row.decision_path) }
& .\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  @reports `
  --ticker 1347.HK `
  --end-date 2026-04-01 `
  --max-holding-days 60
```

### 5. 自动打标

#### AXTI

```powershell
.\.venv\Scripts\python.exe backtest\label_signal_cases.py `
  --result-dir backtest\output\0421-0119-AXTI
```

#### 1347.HK

```powershell
.\.venv\Scripts\python.exe backtest\label_signal_cases.py `
  --result-dir backtest\output\0421-0119-1347HK
```

输出：

- `signal_case_labels.csv`
- `signal_case_labels.md`
- `signal_case_label_summary.json`

### 6. 补图

`run_report_backtest.py` 默认会尝试画图。  
如果图没生成，可以单独补：

```powershell
.\.venv\Scripts\python.exe backtest\render_backtest_chart.py `
  --output-dir backtest\output\0421-0119-AXTI `
  --out backtest\output\0421-0119-AXTI\0421-0119-AXTI-bt.png
```

前提：

- `.venv` 里已安装 `matplotlib`

### 7. 把结果收编进实验目录

每个 ticker 至少复制这些文件到：

```text
backtest/experiments/<experiment_name>/tickers/<ticker>/result/
```

必备文件：

- `summary.json`
- `signals.csv`
- `trades.csv`
- `signal_case_label_summary.json`
- `signal_case_labels.csv`
- `signal_case_labels.md`
- `*-ohlcv.csv`
- `*-bt.png`

### 8. 生成实验汇总

```powershell
.\.venv\Scripts\python.exe backtest\summarize_experiment.py `
  --experiment-dir backtest\experiments\2026-0421-round03
```

输出：

- `compare_summary.json`
- `compare_summary.md`

## 一轮结束后必须看的输出

按优先级看：

### 第一层：结构是否失控

- `compare_summary.md`
- 每个 ticker 的 `summary.json`
- 每个 ticker 的 `signals.csv`
- 每个 ticker 的 `trades.csv`

先回答：

- `buy/hold/sell` 是否明显失衡
- 是否几乎不交易
- 是否过度交易
- `sell` 是否大多发生在无持仓时

### 第二层：错在哪里

- `signal_case_labels.md`
- `signal_case_label_summary.json`

先看：

- `good/bad/unclear` 比例
- `bad_case` 是否集中在同一类动作
- `hold` 是否在吸收太多模糊样本

### 第三层：为什么错

- 对应日期的 `reports/<date>/2_decision/summary.md`

重点找：

- 哪些表述稳定推向错误的 `hold`
- 哪些表述稳定推向错误的 `sell`
- 哪些表述把“附近支撑”误当成“可执行低吸”

## 每轮实验必须记录的结论

建议在实验目录额外写：

- `round01_vs_round02.md`
- `bad_case_patterns.md`
- `decision_summary_patterns.md`

至少回答：

1. 本轮主要修复了哪类 bad case
2. 本轮新引入了什么坏模式
3. 改动是否跨标的成立

## 当前已验证过的注意事项

### 1. `run_report_backtest.py` 必须显式传 `--ticker`

否则可能从报告路径误推 ticker，导致行情取数失败。

### 2. 外部连接中断时，不要重开新批次

优先用：

- `--resume-dir`

### 3. 生成实验汇总时，不要把“复制结果”和“汇总脚本”并行跑

否则容易出现：

- `compare_summary.json` 为空
- `compare_summary.md` 只有表头

正确顺序：

1. 先复制文件
2. 再单独运行 `summarize_experiment.py`

### 4. 图表渲染依赖 `.venv` 的 `matplotlib`

如果回测时出现：

```text
ModuleNotFoundError: No module named 'matplotlib'
```

先安装：

```powershell
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install matplotlib
```

然后单独补图。

## 当前建议的执行节奏

未来继续实验时，默认按下面节奏：

1. 开一轮实验目录
2. 跑 `AXTI + 1347.HK`
3. 自动打标
4. 生成实验汇总
5. 做坏例归因
6. 只改一处提示词或规则
7. 开下一轮实验

不要跳过：

- 自动打标
- 跨标的对比
- 坏例归因

否则很容易回到“单看收益、靠感觉调 prompt”的低效率状态。
