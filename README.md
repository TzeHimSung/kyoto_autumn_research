# Kyoto Autumn Research

京都红叶日期与秋季气温关系的可复现研究。

本仓库使用日本气象厅官方数据，整理 2010—2025 年京都 10—12 月日别气温与京都官方 `かえでの紅葉日`（枫叶红叶日）之间的关系。主要阅读入口是根目录下的 Jupyter Notebook：

- `kyoto_autumn_research_workflow.ipynb`

## 主要结论

- 京都官方枫叶红叶平年日是 12 月 5 日。
- 2010—2025 年中，2021 年气象厅累年 CSV 对京都 `かえでの紅葉` 记录为 0，按缺测处理；相关性分析使用 15 个有效年份。
- 11 月均温与红叶日偏晚有明显正相关：Pearson r≈0.714。
- 简单线性关系：11 月均温每升高 1°C，官方红叶日大约推迟 3 天。
- 10 月均温单独解释力弱：Pearson r≈0.309。10 月偏暖不能单独推出红叶大幅偏晚，11 月降温节奏更关键。
- 10—11 月均温相关性最高：Pearson r≈0.729，每 +1°C 约晚 4.4 天。
- 11/1—12/10 期间日均温 ≤10°C 的天数越多，红叶越早。

行程窗口推论：

- 常规稳妥窗口：11月28日—12月10日
- 显著偏暖年份：12月3日—12月14日
- 明显偏冷年份：11月22日—12月5日

## 数据源

1. 气象厅生物季节观测累年值 CSV：かえで紅葉
   https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv

2. 气象厅过去天气数据：京都站日别值
   https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no=61&block_no=47759&year=YYYY&month=MM&day=&view=p1

## 仓库结构

```text
.
├── kyoto_autumn_research_workflow.ipynb
├── data/
│   ├── raw/
│   │   └── kyoto_daily_temperature_oct_dec_2010_2025.csv
│   └── processed/
│       ├── correlation_results.csv
│       └── kyoto_koyo_temperature_2010_2025_summary.csv
├── scripts/
│   └── fetch_and_analyze.py
└── tests/
    └── test_outputs.py
```

## 复现

本项目只依赖 Python 3 标准库，不需要安装 pandas/numpy/scipy。

```bash
python3 scripts/fetch_and_analyze.py
python3 -m unittest discover -s tests -v
```

脚本会重新从气象厅抓取数据并覆盖生成：

- `data/raw/kyoto_daily_temperature_oct_dec_2010_2025.csv`
- `data/processed/kyoto_koyo_temperature_2010_2025_summary.csv`
- `data/processed/correlation_results.csv`

## 关键文件

- `kyoto_autumn_research_workflow.ipynb`：研究正文，包含数据来源、清洗规则、统计计算、图表和结论。
- `scripts/fetch_and_analyze.py`：抓取、解析、计算并生成 CSV 结果的一体化脚本。
- `tests/test_outputs.py`：验证官方关键年份、日别气温覆盖范围、相关性方向、Notebook 结构与安全约束。

## 解释边界

`かえでの紅葉日` 是官方、跨年份一致的物候指标，但不是每个寺社的“见顷”精确日期。京都内部海拔差异很大：高雄、大原、贵船、鞍马通常更早；市区、低海拔寺社可能更晚。因此本研究适合判断红叶季大方向和偏晚/偏早风险，不适合精确预测某个寺院的最佳一天。
