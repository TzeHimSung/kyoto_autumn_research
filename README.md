# Kyoto Autumn Research

京都官方枫叶红叶日期与秋季气温关系的可复现分析。

本仓库使用日本气象厅官方数据，整理 2010—2025 年京都站 10—12 月日别气温，并与京都官方 `かえでの紅葉日`（枫叶红叶日）进行对照。研究重点是识别秋季气温对红叶日期提前或推迟的解释力，从而辅助京都红叶旅行日期选择。

## 阅读入口

主文档是仓库根目录的 Jupyter Notebook：

- `kyoto_autumn_research_workflow.ipynb`

Notebook 包含完整研究过程：研究问题、数据来源、清洗规则、统计分析、图表和结论。README 只保留项目索引、核心结论和复现说明。

## 研究问题

当京都 10—12 月气温偏暖或偏冷时，官方枫叶红叶日期是否存在系统性提前或推迟？如果存在，哪些温度指标最值得用于旅行日期选择？

## 核心结论

- 京都官方枫叶红叶平年日为 12 月 5 日。
- 2010—2025 年中，2021 年气象厅累年 CSV 对京都 `かえでの紅葉` 记录为 `0`，按缺测处理；相关性分析使用 15 个有效年份。
- 11 月均温与红叶日期偏晚有明显正相关：Pearson r≈0.714。
- 简单线性关系显示：11 月均温每升高 1°C，官方红叶日期约推迟 3 天。
- 10 月均温单独解释力较弱：Pearson r≈0.309。10 月偏暖不能单独推出红叶会大幅推迟，11 月降温节奏更关键。
- 10—11 月均温在候选指标中相关性最高：Pearson r≈0.729，每 +1°C 约晚 4.4 天。
- 11/1—12/10 期间日均温 ≤10°C 的天数越多，红叶通常越早。

## 日期选择推论

- 常规稳妥窗口：11月28日—12月10日
- 显著偏暖年份：12月3日—12月14日
- 明显偏冷年份：11月22日—12月5日

这些窗口针对京都整体红叶季风险判断，不等同于任一寺社的精确“见顷”日期。

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

## 复现方法

本项目只依赖 Python 3 标准库，不需要安装 pandas、NumPy、SciPy 或 matplotlib。

```bash
python3 scripts/fetch_and_analyze.py
python3 -m unittest discover -s tests -v
```

脚本会重新从气象厅抓取数据并覆盖生成以下 CSV：

- `data/raw/kyoto_daily_temperature_oct_dec_2010_2025.csv`
- `data/processed/kyoto_koyo_temperature_2010_2025_summary.csv`
- `data/processed/correlation_results.csv`

## 文件说明

- `kyoto_autumn_research_workflow.ipynb`：研究正文，包含数据来源、清洗规则、统计计算、图表和结论。
- `scripts/fetch_and_analyze.py`：抓取、解析、计算并生成 CSV 结果的一体化脚本。
- `tests/test_outputs.py`：验证官方关键年份、日别气温覆盖范围、相关性方向、Notebook 结构、图表输出和安全约束。

## 解释边界

`かえでの紅葉日` 是官方、跨年份一致的物候指标，但不是每个寺社的旅游“见顷”精确日期。京都内部海拔与地形差异很大：高雄、大原、贵船、鞍马通常早于市区；清水寺、东福寺、下鸭神社等低海拔或市区点位可能更晚。因此，本研究适合判断红叶季整体方向和偏晚/偏早风险，不适合精确预测某个寺院的最佳一天。
