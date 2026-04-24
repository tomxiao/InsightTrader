# 多标的回测实验执行手册

这份文档只解决一件事：

**多标的回测实验，今后应该按什么步骤执行、目录怎么组织、每轮必须产出什么。**

它不是方法论文档，而是执行规范。  
如果后面实验越做越多，默认都以这里为准。

相关文档分工：

- [README.md](/D:/CodeBase/InsightTrader/backtest/README.md)：单次 backtest 的基础说明
- `EXPERIMENT_RUNBOOK.md`：多标的实验的固定流程、目录结构、结果分析与调优要求

## 一、实验主题

在进入 `round` 之前，必须先定义 **实验主题**。

实验主题代表一组长期不变的实验上下文，至少固定这几件事：

- 样本池
- 回测时间窗
- 采样频率
- 实验目标的大方向

例如下面这些都应该被视为不同主题：

- `ticker 组合 A`，区间 `时间窗 A`
- `ticker 组合 B`，区间 `时间窗 A`
- `ticker 组合 A`，区间 `时间窗 B`
- 同样的样本池，但从 `daily` 改成 `weekly`

只要以下任一项变化，就不应继续沿用原来的连续 round 编号，而应该新开一个实验主题：

- ticker 组合变化
- 回测起止时间变化
- 采样频率变化
- 实验主目标发生明显变化

### 实验主题与 round 的关系

- **实验主题**：长期容器，定义“这一串 round 在比较什么”
- **round**：主题内部的一次具体迭代

可以理解成：

- 主题负责“固定上下文”
- round 负责“逐轮调优”

### 主题目录规划

为了避免不同主题下都出现 `round03 / round04` 而混淆，推荐采用两层目录：

```text
backtest/experiments/
  <theme_name>/
    theme_meta.json
    README.md
    rounds/
      round01/
      round02/
      round03/
```

其中：

- `<theme_name>`：建议显式编码样本池、区间和频率，例如：
  - `theme-<tickers>-<start>-<end>-<freq>`
- `theme_meta.json`：记录主题级固定上下文
- `rounds/roundXX/`：每一轮具体实验目录

结论上，**round 编号只能在同一个实验主题内部连续使用**。

## 二、核心原则

每一轮实验都必须满足：

- 有唯一实验目录
- 有固定样本池
- 有固定时间窗
- 有唯一主目标
- 有完整可复现输出

默认一轮实验只改一个方向，例如：

- 收紧偏弱买入
- 补足该有卖出
- 减少 `hold` 滥用
- 修复某一类 bad case

不要在一轮里同时改：

- analyst prompt
- decision manager
- parser
- execution rules

除非这是刻意定义的“整链实验”。

## 三、术语定义

为了避免后面目录和口径混乱，统一使用这些术语。

### 1. theme

实验主题。  
它定义一串 round 共享的固定上下文，例如：

- ticker 组合
- 时间窗
- 采样频率
- 主题目标

### 2. experiment / round

主题内部的一轮具体迭代，例如：

- `round01`
- `round02`
- `round03`

它代表“一次调优 + 一组输出 + 一次复盘”。

### 3. full_round

完整生成：

- `1_analysts`
- `2_decision`

适用场景：

- 新样本池的 baseline
- 上游 analyst 有变更
- 需要重新建立基线输入

### 4. decision_only_round

复用 baseline 的：

- `1_analysts`

仅重新生成：

- `2_decision/summary.md`

适用场景：

- 当前只调 `decision manager`
- 希望提高实验效率
- 希望让归因更干净

### 5. baseline batch

指某个 ticker 的 full_round 报告批次，例如：

- `backtest/experiments/<theme_name>/rounds/round01/reports/<ticker>/<batch_dir>`

它提供后续 decision-only round 要复用的 `1_analysts/`。

### 6. experiment result

指某一轮实验被正式记录在主题目录中的内容：

- `backtest/experiments/<theme_name>/rounds/<round_name>/...`

## 四、实验目录结构

实验目录统一放在：

```text
backtest/experiments/
```

如果采用“主题目录 + rounds 子目录”，推荐结构为：

```text
backtest/experiments/<theme_name>/
  theme_meta.json
  README.md
  rounds/
    round01/
      reports/
        <ticker_a>/
          <batch_dir>/
        <ticker_b>/
          <batch_dir>/
        <ticker_c>/
          <batch_dir>/
      experiment_meta.json
      compare.md
      compare_summary.json
      compare_summary.md
      tickers/
        ...
    round02/
      ...
```

如果当前仍沿用“单层 round 目录”，则每轮结构固定为：

```text
backtest/experiments/<experiment_name>/
  reports/
    <ticker_a>/
      <batch_dir>/
    <ticker_b>/
      <batch_dir>/
    <ticker_c>/
      <batch_dir>/
  experiment_meta.json
  compare.md
  compare_summary.json
  compare_summary.md
  tickers/
    <ticker_a>/
      batch/
        batch_metadata.json
        report_manifest.json
        report_manifest.csv
      result/
        summary.json
        signals.csv
        trades.csv
        signal_case_label_summary.json
        signal_case_labels.csv
        signal_case_labels.md
        *-ohlcv.csv
        *-bt.png
      notes.md
    <ticker_b>/
      batch/
      result/
      notes.md
    <ticker_c>/
      batch/
      result/
      notes.md
```

### report 存储规则

从现在开始，每个 round 的原始报告批次必须直接落在 round 目录内部。

统一约定：

- `backtest/experiments/<theme_name>/rounds/<round_name>/reports/...`：该 round 的唯一正式 batch 输出目录

推荐结构：

```text
roundXX/
  reports/
    <ticker_a>/
      <batch_dir_a>/
    <ticker_b>/
      <batch_dir_b>/
    <ticker_c>/
      <batch_dir_c>/
```

要求：

- 每个 ticker 保留原始 batch 目录名，避免丢失时间戳信息
- 后续生成结果图、`signals.csv`、`trades.csv`、`summary.json`、`reports/...` 全部随 batch 一起归档
- `tickers/<ticker>/result/` 仍保留“便于查看的收编副本”，但它不是原始报告主存储
- 真正的原始回测产物，以 `roundXX/reports/` 下面的 batch 为准

字段说明：

- `experiment_meta.json`
  - 记录实验元信息
  - 至少包含：`name`、`tickers`、`start_date`、`end_date`、`sample_mode`、`step`、`mode`、`baseline_round`

- `decision_manager_prompt_snapshot.md`
  - 记录本轮开始时 `decision manager` 的 prompt 快照
  - 用于复盘“这一轮到底是在什么 prompt 版本上跑出来的”

- `compare.md`
  - 这一轮的人工总结
  - 不是模板占位，必须填写

- `compare_summary.*`
  - 跨标的机器汇总

- `tickers/<ticker>/batch/`
  - 只存本轮这个 ticker 对应的报告批次元信息
  - 不放整份 `reports/`

- `tickers/<ticker>/result/`
  - 只存本轮最终分析和复盘需要看的结果文件

- `tickers/<ticker>/notes.md`
  - 该 ticker 在本轮的人工复盘结论
  - 必须填写

## 五、每轮实验的固定步骤

今后默认按这 8 步执行。

### 1. 初始化实验目录

```powershell
.\.venv\Scripts\python.exe backtest\init_experiment.py `
  --base-dir backtest\experiments\<theme_name>\rounds `
  --name round05 `
  --tickers <ticker_a>,<ticker_b>,<ticker_c> `
  --start-date <start_date> `
  --end-date <end_date> `
  --sample-mode <daily_or_weekly> `
  --step <step_if_daily> `
  --mode decision_only_round `
  --baseline-round round04
```

规则：

- `mode=full_round` 时，`baseline_round` 可空
- `mode=decision_only_round` 时，`baseline_round` 必填
- 初始化完成后，必须确认 round 根目录下已生成 `decision_manager_prompt_snapshot.md`

### 2. 生成报告批次

#### full_round

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker <ticker_a> `
  --start-date <start_date> `
  --end-date <end_date> `
  --sample-mode <daily_or_weekly> `
  --step <step_if_daily> `
  --output-dir backtest\experiments\<theme_name>\rounds\round05\reports\<ticker_a>
```

#### decision_only_round

```powershell
.\.venv\Scripts\python.exe backtest\generate_report_batch.py `
  --ticker <ticker_a> `
  --start-date <start_date> `
  --end-date <end_date> `
  --sample-mode <daily_or_weekly> `
  --step <step_if_daily> `
  --decision-only `
  --output-dir backtest\experiments\<theme_name>\rounds\round05\reports\<ticker_a> `
  --reuse-analyst-from backtest\experiments\<theme_name>\rounds\round01\reports\<ticker_a>\<baseline_batch_dir>
```

decision-only 模式下：

- 复制 baseline 的 `1_analysts/`
- 只重新生成 `2_decision/summary.md`
- 不重跑 `market / news / fundamentals`

### 3. 中断就续跑，不新开批次

统一使用：

- `--resume-dir`

规则：

- 不要因为中途中断就重新生成一个新 batch 目录
- `--resume-dir` 必须指向同一个 round 下已有的 batch 目录
- 不要把两个不同 batch 混用到同一轮实验里

### 4. 跑回测

必须显式传 `--ticker`。

标准形式：

```powershell
$dir = 'D:\CodeBase\InsightTrader\backtest\experiments\<theme_name>\rounds\round05\reports\<ticker_a>\<batch_dir>'
$manifest = Import-Csv (Join-Path $dir 'report_manifest.csv')
$reports = @()
foreach ($row in $manifest) { $reports += @('--report', $row.decision_path) }
& .\.venv\Scripts\python.exe backtest\run_report_backtest.py `
  @reports `
  --ticker <ticker_a> `
  --end-date <end_date> `
  --max-holding-days <days>
```

### 5. 自动打标

```powershell
.\.venv\Scripts\python.exe backtest\label_signal_cases.py `
  --result-dir backtest\experiments\<theme_name>\rounds\round05\reports\<ticker_a>\<batch_dir>
```

### 6. 出图

`run_report_backtest.py` 默认会尝试自动出图。  
如果需要单独补图：

```powershell
.\.venv\Scripts\python.exe backtest\render_backtest_chart.py `
  --output-dir backtest\experiments\<theme_name>\rounds\round05\reports\<ticker_a>\<batch_dir> `
  --out backtest\experiments\<theme_name>\rounds\round05\reports\<ticker_a>\<batch_dir>\<batch_dir>-bt.png
```

规则：

- 图始终依赖当前目录下的本地 `*-ohlcv.csv`
- 图标题必须使用当前批次真实 ticker

### 7. 收编进实验目录

每个 ticker 必须复制这些文件：

放到 `tickers/<ticker>/batch/`：

- `batch_metadata.json`
- `report_manifest.json`
- `report_manifest.csv`

放到 `tickers/<ticker>/result/`：

- `summary.json`
- `signals.csv`
- `trades.csv`
- `signal_case_label_summary.json`
- `signal_case_labels.csv`
- `signal_case_labels.md`
- `*-ohlcv.csv`
- `*-bt.png`

重要规则：

- 收编时必须覆盖旧图，不能保留 experiment 目录里的旧副本
- 不要把图或 batch 产物输出到 round 目录以外的路径

### 8. 生成跨标的汇总

```powershell
.\.venv\Scripts\python.exe backtest\summarize_experiment.py `
  --experiment-dir backtest\experiments\<theme_name>\rounds\round05
```

## 六、每轮实验必须填写的人工输出

这部分不能留空模板。

### 1. `compare.md`

每轮必须至少写：

- 本轮目标
- 本轮实际改动
- 跨标的结果总结
- 下一轮建议

### 2. `tickers/<ticker>/notes.md`

每个 ticker 必须至少写：

- 本轮目标
- 改动内容
- 观察结论
- 下一步

如果 `notes.md` 和 `compare.md` 没填，这轮实验就不算真正收尾。

## 七、结果阅读顺序

### 第一层：先看结构

看：

- `compare_summary.md`
- 每个 ticker 的 `summary.json`
- 每个 ticker 的 `signals.csv`

先回答：

- `buy / hold / sell` 是否明显失衡
- 有没有几乎不交易
- 有没有过度交易
- `sell` 是否大多发生在无持仓时

### 第二层：再看好坏样本

看：

- `signal_case_labels.md`
- `signal_case_label_summary.json`

先回答：

- `good / bad / unclear` 比例是否改善
- `bad_case` 是否集中在同一类动作
- 是否把太多样本推回 `hold`

### 第三层：最后回到正文

看：

- 对应日期的 `reports/<date>/2_decision/summary.md`

重点找：

- 哪些表述在稳定推错
- 哪些表述导致过早买入
- 哪些表述导致该卖不卖
- 哪些表述让港股样本被压得过度保守

## 八、结果分析与调优方法

### 1. 不要只看 `summary.json`

单个 `summary.json` 只能告诉你这一批结果如何，不能直接告诉你：

- 为什么错
- 错在 analyst、decision manager 还是执行规则
- 这个改动是否能跨标的成立

正确顺序始终是：

1. 先看分布
2. 再看 `good / bad / unclear`
3. 最后回到具体日期的 `summary.md`

### 2. 先识别 `bad_case`，再谈提升收益

每轮调优先回答：

- 哪类信号最容易错
- 错误是否集中在同一种动作
- 是不是出现了新的坏模式

优先减少这些典型错误：

- 应该 `buy` 却给了 `hold`
- 应该 `sell` 却给了 `hold`
- 过早 `sell`
- 过弱证据下仍给 `buy_on_pullback`
- 港股或高波动样本被压得过度保守

### 3. `good_case / bad_case / unclear` 的使用原则

不要只给成交交易打标签。

`hold` 和 `sell` 同样要打，因为：

- `hold` 最容易漏掉本该参与的大行情
- `sell` 最容易暴露“风险主导判断”是否真的成立

如果一轮实验里：

- `bad_case` 总量没有下降
- 只是把大量样本推回 `hold`

那通常不算真正改好。

### 4. bad case 归因顺序

建议固定按下面顺序归因：

1. 先看 `decision manager` 输出的 `趋势判断` 和 `建议行动` 是否一致
2. 再看 `1_analysts/` 输入是否已经明显偏向某个方向
3. 最后才看 parser 或 execution 是否把本来合理的文本执行歪了

也就是优先区分：

- 趋势判断错
- 动作映射错
- 上游 analyst 输入就不稳定
- 执行规则放大了问题

### 5. 每轮只改一个方向

每轮只允许一个主目标，例如：

- 收紧弱证据买入
- 补足风险主导卖出
- 修复港股样本过度保守

不要同一轮同时改：

- analyst prompt
- decision manager
- parser
- execution rules

否则你只能看到“结果变了”，看不出“为什么变了”。

### 6. 先做回归，再做扩展

每次调优后，先回归当前主题样本池，再决定是否引入新主题。

如果一个改动只改善了某一只样本，却让其他样本明显变差：

那就不应该继续放大。

### 7. 进入下一轮前必须回答 3 个问题

1. 本轮主要减少了哪类 `bad_case`
2. 本轮是否引入了新的坏模式
3. 本轮改动是否能在当前主题的多标的样本里同时成立

如果这 3 个问题答不清，就不要直接进入下一轮。

## 九、当前已验证的坑

### 1. `run_report_backtest.py` 必须传 `--ticker`

否则可能从路径误推 ticker，造成行情取数或出图异常。

### 2. 图标题不能写死 ticker

标题必须从当前批次结果动态读取。  
否则不同 ticker 的图会错误显示成上一次运行的标的。

### 3. 收编 experiment 目录时，图要同步覆盖

源批次目录里的图即使是新的，experiment 目录里的旧图也不会自动更新。  
收编时必须显式覆盖。

### 4. 生成实验汇总时，不要和复制结果并行跑

正确顺序：

1. 先复制结果
2. 再单独运行 `summarize_experiment.py`

否则容易出现：

- `compare_summary.md` 只有表头
- `compare_summary.json` 为空

### 5. `.venv` 必须带 `matplotlib`

当前已把 `matplotlib` 放进项目 dev 依赖。  
后续统一用：

- `.venv\Scripts\python.exe`

来补图。

## 十、推荐执行节奏

以后默认按下面节奏推进：

1. `round01` 或某个新的 `full_round` 建 baseline
2. 观察多标的结构、收益和 bad case
3. 只改一处 decision 规则
4. 开下一轮 `decision_only_round`
5. 重跑多标的
6. 填 `notes.md` 和 `compare.md`
7. 再决定是否继续下一轮

不要跳过：

- 多标的对照
- 自动打标
- 人工 notes
- compare 总结

否则实验很快又会重新变乱。
