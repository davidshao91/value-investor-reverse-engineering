# 重跑之前要自己抓的数据

仓库里只有规则、脚本和小结果表。行情、财报大表、EDGAR 正文缓存都在 `data/`，这个目录被 git 忽略。不抓这些文件，脚本会直接退出并指出缺哪一个路径。完整重跑不是阅读结论的前提。

把数据根目录换到别处：`export VIRE_DATA=/path/to/data`。

调用 SEC 之前要设置真实联系方式（SEC 要求 User-Agent 里能找到人）：

```bash
export EDGAR_USER_AGENT="Your Name you@domain.com"
```

请求请低于每秒 10 次。脚本里用 `latin-1` 解码季度索引，并在读到第一段 `</DOCUMENT>` 时停下。细节见 [EDGAR 表单事件表](edgar-form-event-table.md)。

## 公共基准

| 文件 | 内容 |
|---|---|
| `data/benchmarks/spy_daily.csv` | 列：`date`, `adj_close`。SPY 全收益日净值。没有这个文件时，指标脚本会试着用 yfinance 现拉。 |
| `data/spx/hist.csv` | 标普 500 时点成分。列：`date`, `tickers`（逗号分隔）。来源可以是公开的历史成分表（本批用的是 fja05680 那份日度快照）。 |
| `data/private/author_benchmark.csv` | **可选，不要提交。** 列：`date`, `nav`。作者自己的保守基准组合。不提供这个文件时，脚本只和 SPY（以及案例里自己算的标普等权）比较。 |

## 财务与行情（林奇、巴菲特，以及施洛斯的市净率档）

| 路径 | 内容 |
|---|---|
| `data/xbrl/frames/` | SEC XBRL frames JSON。公司事实接口，例如 `https://data.sec.gov/api/xbrl/frames/us-gaap/NetIncomeLoss/USD/CY2012.json`。文件名沿用 `{概念}_CY{年}.json` 或季度 `{概念}_CY{年}Q{季}I.json`。 |
| `data/xbrl/panel_fund.pkl` | 年度财务面板，至少要有 `cik`, `fy`, `eq`, `debt`, `shares`, `nc_cons`, `ca`, `cl`, `liab`, `cash`, `sti`, `ebit`。可由 frames 自行拼。 |
| `data/xbrl/tickers_map.csv` | 列：`cik`, `yf`。CIK 到行情代码。SEC `company_tickers.json` 可以当起点。 |
| `data/xbrl/sic.json` | CIK 到 SIC 行业码。没有的代码，林奇脚本会按需向 `data.sec.gov/submissions` 补，并写到 `data/xbrl/sic_extra.json`。 |
| `data/prices/monthly/batch_*.pkl` | yfinance 月度行情，列多层：`Close`, `Adj Close`, `Stock Splits`。**只有今天还在上市的代码**，所以有幸存者偏差，案例 README 里写了。 |
| `data/lynch/float/float_CY{年}Q2I.json` | `dei:EntityPublicFloat` 的 frames，用来给没有行情的公司一个流通市值上界。 |
| `data/buffett/float/` | 同上，给巴菲特宽宇宙用。 |
| `data/buffett/buyback_frames.csv` | 列：`cik`, `fy`, `bb_amt`。回购金额，来自 `PaymentsForRepurchaseOfEquity` 与 `TreasuryStockValueAcquiredCostMethod` 的较大值。 |

## 格林布拉特

分拆脚本把索引和申报史写到 `data/greenblatt/`（`idx/`, `subs/`, `events_raw.csv`, `events_flags.csv`, `px_events.pkl`）。

并购套利脚本把缓存写到 `data/greenblatt/arb/`（`idx/`, `docs/*.gz`, `subs/`, 中间 CSV，以及失败交易的月线 `px_broken.pkl`）。结果小表写回 `cases/greenblatt/out/`。

## 施洛斯

| 路径 | 内容 |
|---|---|
| `data/schloss/finsaber_sp500.pkl` | 含退市的标普价格长表，列：`symbol`, `date`, `adjusted_close`, `close`。FINSABER 的 `all_sp500_prices_FULL.csv` 可转成这个 pickle。 |
| `data/schloss/yf_adj.pkl` | 复权收盘价宽表，用来补 2000 年以前和 2025 年以后。 |
| `data/schloss/yf_close.pkl` | 未复权收盘价，市净率档使用。 |
| `data/schloss/yf_bench.pkl` | 列：`SPY`, `^IRX`（13 周国库券收益率，现金利息）。 |
| `data/schloss/company_tickers.json` | SEC `https://www.sec.gov/files/company_tickers.json`。 |
| `data/schloss/frames/` | 权益、负债、股本的季度 frames。`s07_fetch.py` 会去拉。 |

`s01`–`s03` 会在 `data/schloss/` 里生成 `px.pkl`, `members_me.pkl`, `feat.pkl`。这些是中间缓存，不进 git。

价格拼接时排除了四个已知对不上的代码：`PBG`, `SLR`, `CBE`, `FBF`。这是行情审计里的坏序列，不是一份持仓名单。
