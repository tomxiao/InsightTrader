# News Vendor Lab

`vendor-news-lab` 是一个只读验证子项目，用来沉淀 CN / HK / US 个股新闻的数据源证据，不改动主业务路由。

当前验证两条链路：

- `vendor-comparison`：直接调用仓库内已有 `get_news` vendor 实现，比较 `akshare`、`tushare`、`finnhub` 在不同市场上的可用性、返回体量和错误模式。
- `keyword-expansion`：为同一标的生成多组 ticker / 名称 / alias 关键词，通过实验适配层验证哪些关键词泛化能补到更多新闻。

## 目录

- `cases/market_news_cases.json`：验证用例清单。
- `configs/vendors.json`：vendor 配置与支持市场声明。
- `vendor_news_lab/loader.py`：manifest loader。
- `vendor_news_lab/keywords.py`：CN/HK/US 关键词泛化规则。
- `vendor_news_lab/runner.py`：批量运行、结果聚合与输出落盘。
- `run_validation.py`：命令行入口。

## 运行

先确保 `.env` 里已经配置需要的 key：

- `TUSHARE_TOKEN`
- `FINNHUB_TOKEN`

然后运行：

```bash
python validation/vendor-news-lab/run_validation.py
```

只跑单条链路时可选：

```bash
python validation/vendor-news-lab/run_validation.py --mode vendor-comparison
python validation/vendor-news-lab/run_validation.py --mode keyword-expansion
```

## 输出

每次运行会写入 `validation/vendor-news-lab/outputs/<timestamp>/`：

- `results.jsonl`：每次调用一行，保留 mode、market、vendor、keyword、耗时、原始响应和错误信息。
- `summary.csv`：平铺后的筛选视图，便于按市场 / vendor / 关键词角色做透视。
- `summary.md`：人工阅读的聚合摘要。
- `snapshots/<case_id>/<vendor>/<mode>__<variant>.md`：单次调用快照，便于人工复核原始返回。

## 设计约束

- `tushare` 个股新闻仍然是“时间窗拉取 + 文本过滤”模式，结果里会保留 `news_mode=time_window_filter`。
- `akshare` 关键词验证优先尝试 `stock_news_em(symbol=...)`，失败或无结果时退到 `stock_news_main_cx()` 并按关键词过滤。
- `finnhub` 关键词扩展仅对 US 且仅支持 symbol 等价关键词，名称类关键词会记录为 `unsupported`，避免误导性对比。
- summary 只展示证据，不自动给出“最佳 vendor”结论。
