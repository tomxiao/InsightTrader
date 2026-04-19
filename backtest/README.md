# Report Backtest

`backtest/` 用于把 `InsightTrader` 的 `lite team` 报告转成可执行信号，再做最小回测。

当前版本只覆盖：

- `lite team` 的 `2_decision/summary.md`
- 只做多
- 重点解析 `建议行动 / 截面价格 / 入场方式 / 失效条件`
- 支持的建议行动：
  - `确信买入` -> 次日开盘买入
  - `择机买入` -> 等待入场区间触发
  - `保持观望` -> 不交易
  - `建议卖出` -> 第一版仅记录为跳过，不做空

## 目录

- [models.py](/D:/CodeBase/InsightTrader/backtest/models.py)
- [report_parser.py](/D:/CodeBase/InsightTrader/backtest/report_parser.py)
- [execution_rules.py](/D:/CodeBase/InsightTrader/backtest/execution_rules.py)
- [metrics.py](/D:/CodeBase/InsightTrader/backtest/metrics.py)
- [run_report_backtest.py](/D:/CodeBase/InsightTrader/backtest/run_report_backtest.py)
- [generate_report_batch.py](/D:/CodeBase/InsightTrader/backtest/generate_report_batch.py)

## 回测口径

第一版执行规则：

1. `确信买入`：分析日后的第一个交易日按开盘价买入。
2. `择机买入`：若报告存在 `24.50-25.50` 这类入场区间，则在未来窗口内首次触达该区间时买入。
3. 若入场前先出现明确失效价位被收盘跌破，则该信号失效。
4. 开仓后若价格触发失效价位，则按失效价止损。
5. 若未止损，则持有到 `max_holding_days` 或回测窗口结束。

## 执行手册

下面这套流程适用于当前 `backtest/` 的标准用法。

### 1. 先生成历史分析报告

使用 [generate_report_batch.py](/D:/CodeBase/InsightTrader/backtest/generate_report_batch.py) 批量跑 `lite team` 报告。

常用参数：

- `--ticker`：要回测的标的，例如 `AXTI`
- `--start-date`：起始日期，格式 `YYYY-MM-DD`
- `--end-date`：结束日期，格式 `YYYY-MM-DD`
- `--llm-model`：历史报告生成所使用的模型，默认 `deepseek-chat`
- `--sample-mode weekly`：按周抽样，取每周第一个交易日
- `--sample-mode daily`：按天抽样
- `--step`：仅在 `daily` 模式下生效，表示每隔多少个交易日取一个样本
- `--resume-dir`：续跑一个已有批次目录，跳过已完成报告

周频示例：

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode weekly
```

日频示例：

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode daily `
  --step 3
```

断点续传示例：

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode weekly `
  --resume-dir backtest\output\0419-2234-AXTI
```

### 2. 查看批次输出目录

每次运行都会创建一个新的输出目录：

- `backtest/output/MMdd-HHmm-ticker/`

例如：

- `backtest/output/0419-2234-AXTI/`

该目录下会包含：

- `batch_metadata.json`
- `report_manifest.json`
- `report_manifest.csv`
- `reports/`

其中：

- `reports/yyyy-MMdd-ticker/` 保存每个分析日对应的完整报告副本
- `report_manifest.csv` 记录所有样本与对应的 `decision_path`
- `batch_metadata.json` 会记录这批历史报告生成所使用的 `llm_provider=deepseek` 与 `llm_model`
- 如果生成过程被打断，可用同一个目录执行 `--resume-dir` 继续跑，脚本会自动跳过已存在且 `decision_path` 可读的报告

### 3. 用报告清单执行回测

回测脚本是 [run_report_backtest.py](/D:/CodeBase/InsightTrader/backtest/run_report_backtest.py)。

当前它接收一组 `--report` 参数，每个参数都指向一个 `2_decision/summary.md`。

最简单的做法是从 `report_manifest.csv` 中取出所有 `decision_path`，再统一喂给回测脚本。

手动示例：

```powershell
.\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  --report backtest\output\0419-2234-AXTI\reports\2026-0102-AXTI\2_decision\summary.md `
  --report backtest\output\0419-2234-AXTI\reports\2026-0105-AXTI\2_decision\summary.md `
  --report backtest\output\0419-2234-AXTI\reports\2026-0112-AXTI\2_decision\summary.md `
  --end-date 2026-04-19 `
  --max-holding-days 60
```

如果你已经有标准 OHLCV 文件，也可以跳过在线取数：

```powershell
.\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  --report backtest\output\0419-2234-AXTI\reports\2026-0102-AXTI\2_decision\summary.md `
  --ohlcv-csv path\to\AXTI_ohlcv.csv `
  --end-date 2026-04-19 `
  --max-holding-days 60
```

### 4. 查看回测结果

如果 `--report` 都来自同一个批次目录下的 `reports/`，回测结果会直接写到这个批次目录根部，也就是和 `reports/` 同级。

例如输入：

- `backtest/output/0419-2234-AXTI/reports/.../2_decision/summary.md`

则输出会落到：

- `backtest/output/0419-2234-AXTI/`

目录内包含：

- `signals.csv`
- `trades.csv`
- `summary.json`

含义如下：

- `signals.csv`：报告解析后的结构化信号
- `trades.csv`：信号执行后的逐笔结果
- `summary.json`：整批回测的汇总统计

如果传入的 `--report` 不属于同一个批次目录，或者你显式传了 `--output-dir`，则会改为写到指定目录；没有指定时才会退回到新的 `backtest/output/MMdd-HHmm-ticker/`。

### 5. 推荐的实际操作顺序

建议按下面顺序执行：

1. 先用 `generate_report_batch.py` 为单一标的生成一批历史报告
2. 打开 `report_manifest.csv` 检查 `decision_path` 是否完整
3. 用 `run_report_backtest.py` 跑这批 `decision_path`
4. 先看 `summary.json` 判断整体结果
5. 再看 `trades.csv` 逐笔核对入场、止损和退出原因

### 6. 当前默认约束

执行时默认会遵守这些约束：

- 数据源优先使用 `tushare`
- 历史报告生成默认使用 `deepseek-chat`
- 批量生成报告固定使用 `3` 并发
- 生成阶段支持断点续传，但需要显式传 `--resume-dir`
- 当前只支持 `lite team` 决策摘要回测
- 当前只做多，不做空
- `择机买入` 按报告里的入场区间触发
- `保持观望` 直接跳过
- 当 `--report` 来自同一个批次目录时，回测结果默认写回该批次目录根部
- 只有无法推断批次目录时，才会新建 `backtest/output/MMdd-HHmm-ticker/`

## 示例

```powershell
.\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  --report backtest\output\0419-2216-AXTI\reports\2026-0223-AXTI\2_decision\summary.md `
  --report backtest\output\0419-2216-AXTI\reports\2026-0413-AXTI\2_decision\summary.md `
  --end-date 2026-04-19 `
  --max-holding-days 60
```

如果报告来自同一个批次目录，输出文件默认落到该目录根部，并与 `reports/` 同级。

- `signals.csv`
- `trades.csv`
- `summary.json`

## 批量生成历史报告

可以先批量生成 `lite team` 历史报告，再把 manifest 里的 `decision_path` 批量喂给回测脚本。

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker AXTI `
  --start-date 2026-01-01 `
  --end-date 2026-04-17 `
  --sample-mode weekly
```

批量脚本会创建：

- `backtest/output/MMdd-HHmm-ticker/batch_metadata.json`
- `backtest/output/MMdd-HHmm-ticker/report_manifest.json`
- `backtest/output/MMdd-HHmm-ticker/report_manifest.csv`
- `backtest/output/MMdd-HHmm-ticker/reports/yyyy-MMdd-ticker/`

其中每个历史报告都会被复制到本批次目录下的 `reports/` 中，且 `report_manifest.csv` 里的 `decision_path` 会直接指向这些本地副本。

## 已知限制

- 目前 parser 仍依赖中文固定字段和数字表达。
- `建议卖出` 还没有做空执行。
- 同一根 K 线内若同时触发入场与止损，第一版采用保守规则，优先视为风险较高场景。
- 批量报告生成固定使用 `3` 并发。
- 终端会按报告粒度打印 `SKIP / RUN / DONE / FAIL` 进度。
