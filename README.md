# 价值投资大师的方法，能不能写成规则？

这个仓库做一件公开的研究：把几位著名价值投资者**说过和做过的事**，收成可以打分的买卖规则，用免费数据回测，再把结论原样公布。结论可以是失败。

问题只有一句：**大师的方法，能不能被别人用规则照着做？**

每位大师都走同一条路：

1. **写成规则。** 买什么、什么时候卖、买几只，都要能让另一个人独立执行。逛商场、拜访管理层这种无法打分的部分，只记在局限里，不拿去回测。
2. **先锁及格线，再看结果。** 在算出任何收益之前，先写死「怎样算通过」。这叫预注册：标准事先定好，避免事后只留下好看的数字。
3. **用历史数据回测。** 尽量处理退市、偷看未来数据、交易成本和分红。原料是美国证监会 EDGAR 的公开申报，加上免费行情。付费数据库不在本批里。
4. **给一个诚实结论。** 只有四种：

| 结论 | 意思 |
|---|---|
| **放弃** | 这条规则没过事先写死的及格线 |
| **前向观察** | 历史上看起来过了，但还要换更早的起点或更好的数据才能当真 |
| **备忘录门槛** | 过线，并且数据质量够写进正式研究备忘录 |
| **数据 blocker** | 免费数据缺关键的一块，现在测不了真伪，所以先停 |

成长股、分拆、并购价差，只要问题仍是「付出的价格对上得到的价值」，在这里都算价值投资。分得清的是另一件事：哪一段能写成规则，哪一段只能靠当时的判断。

**Calmar（卡尔玛）** 是本仓库的主分数：年化收益率 ÷ 最大回撤的绝对值。最大回撤是净值从高点跌到低点的最大跌幅。Calmar 可以粗看成「每承受一单位最深亏损，换到多少长期增速」。

**及格线（2026-10-19 锁定，之后没有因结果改动）：** 相对标普 500（下面写 SPY）**或**作者自己的保守基准组合（不公开），Calmar 至少高出 0.05，同时最大回撤不能再深超过 5 个百分点；去掉相对超额最好的 3 个自然年后仍然更好；换成更早的起点再测一次仍然成立；交易成本从每边 0.10% 提高到 0.30% 后仍然成立。公开对照是 **SPY** 和 **标普成分等权**。作者自己的组合只参加打分，成分不公开，本仓库也不附带它的持仓或净值序列。

本研究只公开过程和结论，不构成投资建议。

## 第一批结果

| 案例 | 结论 | 一句话 |
|---|---|---|
| [林奇：用 PEG 买成长股](cases/lynch/) | **放弃** | 用过去三年利润增长来算 PEG，在 2012–2026 的大盘股里没过线。过去的利润增长预测不了未来的利润增长。麦哲伦基金的超额来自主观选股和当年的小规模，不是这条公式。 |
| [格林布拉特：现金并购套利（2009 年起）](cases/greenblatt/) | **放弃** | 从 SEC 并购委托书里能算出价差，单笔平均大约赚 7%，但够 5% 价差的交易太少，组合大部分时间拿着现金，核查后年化约 1%。 |
| [格林布拉特：分拆](cases/greenblatt/) | **数据 blocker** | 免费行情只覆盖大约一半已完成的分拆。被收购或退市的那一批正好缺失，真伪现在测不了。 |
| [巴菲特合伙年代：便宜，并且有催化剂（2009 年起）](cases/buffett/) | **放弃** | 把后来退市的公司加回宇宙之后，篮子能组出来，但跑输标普，也跑输「同样便宜、却没有回购催化剂」的对照。 |
| [施洛斯：跌落的蓝筹（M2 / M3 / M4）](cases/schloss/) | **放弃** | 买跌到多年低点的标普成分，2000–2026 年化约 6.5%、最深跌约 61%，不如直接持有标普。分批买、换一种卖法，都救不了这条规则。用市净率再滤一遍时，财报覆盖不够，那一档记为数据 blocker。 |

每个案例目录里，先是白话结论，然后是做法、数字和局限。回测脚本在 `code/`，小结果表在 `out/`。原始行情和申报缓存没有放进仓库，要重跑请看 [docs/data.md](docs/data.md)。

## 仓库里还有什么

- [案例索引](cases/README.md)
- [要自己抓哪些数据](docs/data.md)
- [用 EDGAR 表格类型做事件表](docs/edgar-form-event-table.md)（第一批里可复用的做法）
- [公开什么、不公开什么](docs/BUILD_IN_PUBLIC.md)

## English

This repo turns what famous value investors said and did into rules that can fail a test. The pass bar is written down before any backtest (preregistration: lock the scoreboard first). Then we run the rule on free data — SEC EDGAR filings plus free prices — and publish one verdict: abandon, forward-watch, memo-gate, or data blocker.

Batch 1, in one line each: Lynch-style PEG on trailing earnings growth — abandon (past profit growth did not predict future profit growth; Magellan’s edge was not this formula). Greenblatt cash merger arbitrage from 2009, built from SEC merger proxies — abandon (the spread is real, the portfolio sits in cash). Greenblatt spin-offs — data blocker (free prices cover about half the completed deals). Buffett partnership-era “cheap plus a catalyst” from 2009 — abandon (it lost to the S&P and to the same cheap basket with no catalyst). Schloss-style fallen S&P blue chips — abandon (buying multi-year lows lost to the S&P; the price-to-book version is a data blocker).

**Calmar** = annualized return divided by the absolute value of the worst peak-to-trough loss. The public benchmarks are SPY and an equal-weight S&P. A private conservative portfolio used as an extra benchmark is not published. Research only, not investment advice.

## License

MIT
