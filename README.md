# Kyoto Autumn Research

京都官方枫叶红叶日期与秋季天气驱动因素的可复现分析。

本仓库使用日本气象厅官方数据，整理 2010—2025 年京都站 10—12 月日别天气，并与京都官方 `かえでの紅葉日`（枫叶红叶日）进行对照。研究重点从秋季气温出发，扩展到夜间低温、昼夜温差、日照、降水和强风等维度，从而辅助京都红叶旅行日期选择与现场观赏风险判断。

## 阅读入口

主文档是仓库根目录的 Jupyter Notebook：

- `kyoto_autumn_research_workflow.ipynb`

Notebook 包含完整研究过程：研究问题、数据来源、清洗规则、统计分析、图表和结论。当前版本使用 pandas 与 NumPy 进行数据整理和统计计算，并使用 Matplotlib 与 Seaborn 生成可复核的 SVG 图表。

## 研究问题

当京都 10—12 月天气偏暖、偏冷、少日照、多雨或强风时，官方枫叶红叶日期是否存在系统性提前或推迟？哪些指标适合判断红叶推进，哪些指标更适合判断游客现场“见顷”窗口质量？

## 核心结论

- 京都官方枫叶红叶平年日为 12 月 5 日。
- 2010—2025 年中，2021 年气象厅累年 CSV 对京都 `かえでの紅葉` 记录为 `0`，按缺测处理；相关性分析使用 15 个有效年份。
- 11 月均温与红叶日期偏晚有明显正相关：Pearson r≈0.714。
- 简单线性关系显示：11 月均温每升高 1°C，官方红叶日期约推迟 3 天。
- 10 月均温单独解释力较弱：Pearson r≈0.309。10 月偏暖不能单独推出红叶会大幅推迟，11 月降温节奏更关键。
- 10—11 月均温在候选指标中相关性最高：Pearson r≈0.729，每 +1°C 约晚 4.4 天。
- 11/1—12/10 期间日均温 ≤10°C 的天数越多，红叶通常越早。
- 第一阶段扩展维度优先使用同一个气象厅日别数据源：夜间最低温用于补充红叶推进信号；昼夜温差、日照、降水和强风更偏向解释颜色质量、落叶速度和见顷窗口稳定性。
- 样本量只有 15 个有效官方红叶日期，本仓库保持单变量探索和残差解释，不把扩展维度包装成过度拟合的多元预测模型。

## 日期选择推论

- 常规稳妥窗口：11月28日—12月10日
- 显著偏暖年份：12月3日—12月14日
- 明显偏冷年份：11月22日—12月5日

这些窗口针对京都整体红叶季风险判断，不等同于任一寺社的精确“见顷”日期。若 11 月下旬出现强降水或强风，即使官方红叶日信号正常，实际观赏窗口也可能缩短。

## 数据源

1. 气象厅生物季节观测累年值 CSV：かえで紅葉
   https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv

2. 气象厅过去天气数据：京都站日别值
   https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no=61&block_no=47759&year=YYYY&month=MM&day=&view=p1

## 扩展天气维度

第一阶段只使用日本气象厅京都站同一日别页面，不引入脆弱的第三方旅游网站抓取。新增维度包括：

- 夜间低温：11 月平均最低温、最低温 ≤8°C / ≤5°C 天数、第一次最低温 ≤8°C 日期（从 11 月 1 日起搜索）。
- 昼夜温差：11 月平均日较差、日较差 ≥10°C 天数。
- 日照：11 月总日照、11/1—12/10 总日照、晴朗冷夜天数。
- 降水：10—11 月累计降水、11 月累计降水、11 月雨日数（≥1 mm）、11 月 15 日后强降水天数（≥20 mm）。
- 强风：11/1—12/10 最大瞬间风速、11 月 15 日后强风天数（最大瞬间风速 ≥10 m/s）。

这些指标分成两类解释：夜间低温和冷日数更接近官方红叶日推进机制；日照、降水和强风更接近游客见顷窗口质量与落叶风险。

## 仓库结构

```text
.
├── kyoto_autumn_research_workflow.ipynb
├── requirements.txt
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

Notebook 与测试需要科学计算栈：NumPy、pandas、Matplotlib、Seaborn 和 IPython。依赖集中记录在 `requirements.txt`。

推荐使用虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

如需重新从气象厅抓取数据并覆盖生成 CSV：

```bash
.venv/bin/python scripts/fetch_and_analyze.py
.venv/bin/python -m unittest discover -s tests -v
```

`fetch_and_analyze.py` 本身仍保持 Python 标准库实现，便于在最小环境中刷新数据；Notebook 负责使用科学计算与画图库进行研究展示。脚本解析气象厅日别页面中的气温、降水、湿度、风、日照和天气概况字段。

脚本会重新生成以下 CSV：

- `data/raw/kyoto_daily_temperature_oct_dec_2010_2025.csv`
- `data/processed/kyoto_koyo_temperature_2010_2025_summary.csv`
- `data/processed/correlation_results.csv`

## 文件说明

- `kyoto_autumn_research_workflow.ipynb`：研究正文，包含数据来源、清洗规则、pandas/NumPy 统计计算、Matplotlib/Seaborn 图表、扩展天气维度和结论。
- `requirements.txt`：Notebook 与测试所需的科学计算和可视化依赖。
- `scripts/fetch_and_analyze.py`：抓取、解析、计算并生成 CSV 结果的一体化脚本。
- `tests/test_outputs.py`：验证官方关键年份、日别天气覆盖范围、扩展天气字段、相关性方向、Notebook 结构、科学计算栈使用、图表输出和安全约束。

## 解释边界

`かえでの紅葉日` 是官方、跨年份一致的物候指标，但不是每个寺社的旅游“见顷”精确日期。京都内部海拔与地形差异很大：高雄、大原、贵船、鞍马通常早于市区；清水寺、东福寺、下鸭神社等低海拔或市区点位可能更晚。因此，本研究适合判断红叶季整体方向和偏晚/偏早风险，不适合精确预测某个寺院的最佳一天。
