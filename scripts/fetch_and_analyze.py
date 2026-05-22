#!/usr/bin/env python3
"""Fetch and analyze Kyoto autumn foliage / temperature data.

This script intentionally uses only the Python standard library so the research
repo can be reproduced on a fresh machine without package installation.

Sources:
- JMA biological phenology cumulative CSV, maple red leaves:
  https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv
- JMA historical daily weather data, Kyoto station 47759:
  https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import io
import math
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
PHENOLOGY_URL = "https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv"
WEATHER_URL_TEMPLATE = (
    "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
    "?prec_no=61&block_no=47759&year={year}&month={month}&day=&view=p1"
)
USER_AGENT = "Mozilla/5.0 (kyoto-autumn-research; reproducible research script)"
YEARS = range(2010, 2026)
MONTHS = (10, 11, 12)
NORMAL_RED_DATE_MONTH_DAY = (12, 5)  # JMA 1991-2020 normal for Kyoto kaede red leaves.

SUMMARY_PATH = ROOT / "data" / "processed" / "kyoto_koyo_temperature_2010_2025_summary.csv"
DAILY_PATH = ROOT / "data" / "raw" / "kyoto_daily_temperature_oct_dec_2010_2025.csv"
CORRELATION_PATH = ROOT / "data" / "processed" / "correlation_results.csv"
REPORT_PATH = ROOT / "reports" / "kyoto_autumn_temperature_correlation_2010_2025.md"


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def parse_jma_mmdd(value: str, year: int) -> dt.date | None:
    value = value.strip()
    if not value or value == "0":
        return None
    number = int(value)
    month = number // 100
    day = number % 100
    return dt.date(year, month, day)


def parse_phenology() -> tuple[dict[int, dt.date | None], dict[int, str], str]:
    """Return Kyoto official maple red-leaf dates, JMA remark codes, and normal date."""
    text = fetch_bytes(PHENOLOGY_URL).decode("shift_jis")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[1]

    kyoto_row = None
    for row in rows[2:]:
        if len(row) > 1 and row[1].strip().startswith("京都"):
            kyoto_row = row
            break
    if kyoto_row is None:
        raise RuntimeError("Kyoto row not found in JMA phenology CSV")

    dates: dict[int, dt.date | None] = {}
    remarks: dict[int, str] = {}
    for year in YEARS:
        idx = header.index(str(year))
        dates[year] = parse_jma_mmdd(kyoto_row[idx], year)
        remarks[year] = kyoto_row[idx + 1].strip()

    normal_idx = header.index("平年値")
    normal_value = kyoto_row[normal_idx].strip()
    normal_date = f"{int(normal_value) // 100:02d}-{int(normal_value) % 100:02d}"
    return dates, remarks, normal_date


def parse_float(value: str) -> float | None:
    value = value.strip()
    if value in {"", "--", "×", "//"}:
        return None
    match = re.match(r"[-+]?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def clean_cell(cell_html: str) -> str:
    cell_html = re.sub(r"<script.*?</script>", "", cell_html, flags=re.S)
    text = re.sub(r"<[^>]+>", "", cell_html)
    return html.unescape(text).replace("\n", "").replace("\r", "").strip()


def parse_daily_weather_page(year: int, month: int) -> list[dict[str, object]]:
    url = WEATHER_URL_TEMPLATE.format(year=year, month=month)
    page = fetch_bytes(url).decode("utf-8", errors="replace")
    row_htmls = re.findall(r'<tr class="mtx" style="text-align:right;">(.*?)</tr>', page, flags=re.S)
    if not row_htmls:
        raise RuntimeError(f"No daily rows parsed for {year}-{month:02d}: {url}")

    output: list[dict[str, object]] = []
    for row_html in row_htmls:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.S)
        values = [clean_cell(cell) for cell in cells]
        if len(values) < 9:
            continue
        day = int(values[0])
        date = dt.date(year, month, day)
        output.append(
            {
                "date": date.isoformat(),
                "year": year,
                "month": month,
                "day": day,
                "t_mean_c": parse_float(values[6]),
                "t_max_c": parse_float(values[7]),
                "t_min_c": parse_float(values[8]),
                "source_url": url,
            }
        )
    return output


def row_int(row: dict[str, object], key: str) -> int:
    return int(str(row[key]))


def row_float(row: dict[str, object], key: str) -> float:
    value = row[key]
    if value is None:
        raise ValueError(f"Missing numeric value for {key}: {row}")
    return float(str(value))


def fetch_daily_weather() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in YEARS:
        for month in MONTHS:
            rows.extend(parse_daily_weather_page(year, month))
            time.sleep(0.05)  # Be gentle to JMA servers.

    counts: dict[tuple[int, int], int] = defaultdict(int)
    for row in rows:
        counts[(row_int(row, "year"), row_int(row, "month"))] += 1
    expected_counts = {10: 31, 11: 30, 12: 31}
    bad = [key for key, count in counts.items() if count != expected_counts[key[1]]]
    if bad:
        raise RuntimeError(f"Unexpected daily row counts: {bad}")
    return rows


def average(values: Iterable[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def count_threshold(rows: Iterable[dict[str, object]], threshold: float) -> int:
    return sum(1 for row in rows if row["t_mean_c"] is not None and row_float(row, "t_mean_c") <= threshold)


def first_trailing_5d_mean_le(rows: list[dict[str, object]], year: int, threshold: float) -> dt.date | None:
    by_date = {dt.date.fromisoformat(str(row["date"])): row["t_mean_c"] for row in rows}
    for date in sorted(by_date):
        if date < dt.date(year, 11, 1):
            continue
        window = [date - dt.timedelta(days=offset) for offset in range(4, -1, -1)]
        if all(day in by_date and by_date[day] is not None for day in window):
            mean = sum(float(str(by_date[day])) for day in window) / 5
            if mean <= threshold:
                return date
    return None


def pearson(xs: Sequence[float | None], ys: Sequence[float | None]) -> tuple[float | None, int]:
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None, n
    mean_x = sum(x for x, _ in pairs) / n
    mean_y = sum(y for _, y in pairs) / n
    ss_x = sum((x - mean_x) ** 2 for x, _ in pairs)
    ss_y = sum((y - mean_y) ** 2 for _, y in pairs)
    if ss_x == 0 or ss_y == 0:
        return None, n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    return cov / math.sqrt(ss_x * ss_y), n


def ranks(values: list[float]) -> list[float]:
    sorted_values = sorted((value, index) for index, value in enumerate(values))
    result = [0.0] * len(values)
    i = 0
    while i < len(sorted_values):
        j = i
        while j < len(sorted_values) and sorted_values[j][0] == sorted_values[i][0]:
            j += 1
        rank = (i + 1 + j) / 2
        for _, index in sorted_values[i:j]:
            result[index] = rank
        i = j
    return result


def spearman(xs: list[float | None], ys: list[float | None]) -> tuple[float | None, int]:
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None, len(pairs)
    ranked_x = ranks([x for x, _ in pairs])
    ranked_y = ranks([y for _, y in pairs])
    return pearson(ranked_x, ranked_y)


def linear_regression(xs: list[float | None], ys: list[float | None]) -> dict[str, float | int | None]:
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return {"n": n, "slope": None, "intercept": None, "r2": None, "resid_se_days": None}
    mean_x = sum(x for x, _ in pairs) / n
    mean_y = sum(y for _, y in pairs) / n
    ss_x = sum((x - mean_x) ** 2 for x, _ in pairs)
    if ss_x == 0:
        return {"n": n, "slope": None, "intercept": None, "r2": None, "resid_se_days": None}
    slope = sum((x - mean_x) * (y - mean_y) for x, y in pairs) / ss_x
    intercept = mean_y - slope * mean_x
    predictions = [intercept + slope * x for x, _ in pairs]
    ss_res = sum((y - pred) ** 2 for (_, y), pred in zip(pairs, predictions))
    ss_tot = sum((y - mean_y) ** 2 for _, y in pairs)
    r2 = 1 - ss_res / ss_tot if ss_tot else None
    resid_se = math.sqrt(ss_res / (n - 2)) if n > 2 else None
    return {"n": n, "slope": slope, "intercept": intercept, "r2": r2, "resid_se_days": resid_se}


def day_from_oct1(date: dt.date, year: int) -> int:
    return (date - dt.date(year, 10, 1)).days + 1


def build_summary(red_dates: dict[int, dt.date | None], remarks: dict[int, str], daily_rows: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    by_year: dict[int, list[dict[str, object]]] = {year: [] for year in YEARS}
    for row in daily_rows:
        by_year[row_int(row, "year")].append(row)

    summary: dict[int, dict[str, object]] = {}
    for year in YEARS:
        rows = by_year[year]
        oct_rows = [row for row in rows if row_int(row, "month") == 10]
        nov_rows = [row for row in rows if row_int(row, "month") == 11]
        dec_rows = [row for row in rows if row_int(row, "month") == 12]
        oct_nov_rows = oct_rows + nov_rows
        nov_dec10_rows = [
            row
            for row in rows
            if dt.date(year, 11, 1) <= dt.date.fromisoformat(str(row["date"])) <= dt.date(year, 12, 10)
        ]
        nov16_dec10_rows = [
            row
            for row in rows
            if dt.date(year, 11, 16) <= dt.date.fromisoformat(str(row["date"])) <= dt.date(year, 12, 10)
        ]
        red_date = red_dates[year]
        delay = (red_date - dt.date(year, *NORMAL_RED_DATE_MONTH_DAY)).days if red_date else None
        first_5d_le_12 = first_trailing_5d_mean_le(rows, year, 12)
        first_5d_le_10 = first_trailing_5d_mean_le(rows, year, 10)

        summary[year] = {
            "year": year,
            "red_date": red_date.isoformat() if red_date else "",
            "red_md": red_date.strftime("%m/%d") if red_date else "",
            "red_day_from_oct1": day_from_oct1(red_date, year) if red_date else None,
            "delay_vs_dec5_days": delay,
            "oct_mean_c": average(row_float(row, "t_mean_c") for row in oct_rows),
            "nov_mean_c": average(row_float(row, "t_mean_c") for row in nov_rows),
            "dec_mean_c": average(row_float(row, "t_mean_c") for row in dec_rows),
            "oct_nov_mean_c": average(row_float(row, "t_mean_c") for row in oct_nov_rows),
            "nov_dec10_mean_c": average(row_float(row, "t_mean_c") for row in nov_dec10_rows),
            "nov16_dec10_mean_c": average(row_float(row, "t_mean_c") for row in nov16_dec10_rows),
            "nov_days_le_10c": count_threshold(nov_rows, 10),
            "nov_days_le_12c": count_threshold(nov_rows, 12),
            "nov_dec10_days_le_10c": count_threshold(nov_dec10_rows, 10),
            "nov_dec10_days_le_12c": count_threshold(nov_dec10_rows, 12),
            "first_5d_mean_le_12": first_5d_le_12.isoformat() if first_5d_le_12 else "",
            "first_5d_mean_le_10": first_5d_le_10.isoformat() if first_5d_le_10 else "",
            "first_5d_le_12_day_from_oct1": day_from_oct1(first_5d_le_12, year) if first_5d_le_12 else None,
            "first_5d_le_10_day_from_oct1": day_from_oct1(first_5d_le_10, year) if first_5d_le_10 else None,
            "red_rm": remarks[year],
        }
    return summary


def as_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(str(value))


def build_correlations(summary: dict[int, dict[str, object]]) -> list[dict[str, object]]:
    metrics = [
        "oct_mean_c",
        "nov_mean_c",
        "dec_mean_c",
        "oct_nov_mean_c",
        "nov_dec10_mean_c",
        "nov16_dec10_mean_c",
        "nov_days_le_10c",
        "nov_days_le_12c",
        "nov_dec10_days_le_10c",
        "nov_dec10_days_le_12c",
        "first_5d_le_12_day_from_oct1",
        "first_5d_le_10_day_from_oct1",
    ]
    target = [as_optional_float(summary[year]["delay_vs_dec5_days"]) for year in YEARS]
    rows: list[dict[str, object]] = []
    for metric in metrics:
        xs = [as_optional_float(summary[year][metric]) for year in YEARS]
        pearson_r, n = pearson(xs, target)
        spearman_r, _ = spearman(xs, target)
        lr = linear_regression(xs, target)
        rows.append(
            {
                "metric": metric,
                "n": n,
                "pearson_r": pearson_r,
                "spearman_r": spearman_r,
                "slope_days_per_unit": lr["slope"],
                "intercept_days": lr["intercept"],
                "r2": lr["r2"],
                "residual_se_days": lr["resid_se_days"],
            }
        )
    rows.sort(key=lambda row: abs(float(row["pearson_r"])) if row["pearson_r"] is not None else -1, reverse=True)
    return rows


def fmt_csv(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_daily(daily_rows: list[dict[str, object]]) -> None:
    DAILY_PATH.parent.mkdir(parents=True, exist_ok=True)
    columns = ["date", "year", "month", "day", "t_mean_c", "t_max_c", "t_min_c", "source_url"]
    with DAILY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in daily_rows:
            writer.writerow({column: fmt_csv(row[column]) for column in columns})


def write_summary(summary: dict[int, dict[str, object]]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "year",
        "red_date",
        "red_md",
        "delay_vs_dec5_days",
        "oct_mean_c",
        "nov_mean_c",
        "dec_mean_c",
        "oct_nov_mean_c",
        "nov_dec10_mean_c",
        "nov16_dec10_mean_c",
        "nov_days_le_10c",
        "nov_days_le_12c",
        "nov_dec10_days_le_10c",
        "nov_dec10_days_le_12c",
        "first_5d_mean_le_12",
        "first_5d_mean_le_10",
        "red_rm",
    ]
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for year in YEARS:
            row = {column: fmt_csv(summary[year][column]) for column in columns}
            for integer_column in [
                "year",
                "delay_vs_dec5_days",
                "nov_days_le_10c",
                "nov_days_le_12c",
                "nov_dec10_days_le_10c",
                "nov_dec10_days_le_12c",
                "red_rm",
            ]:
                if row[integer_column].endswith(".000000"):
                    row[integer_column] = row[integer_column].replace(".000000", "")
            writer.writerow(row)


def write_correlations(correlations: list[dict[str, object]]) -> None:
    CORRELATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "metric",
        "n",
        "pearson_r",
        "spearman_r",
        "slope_days_per_unit",
        "intercept_days",
        "r2",
        "residual_se_days",
    ]
    with CORRELATION_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in correlations:
            writer.writerow({column: fmt_csv(row[column]) for column in columns})


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_report(summary: dict[int, dict[str, object]], correlations: list[dict[str, object]], normal_date: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    corr_by_metric = {str(row["metric"]): row for row in correlations}

    annual_rows = []
    for year in YEARS:
        row = summary[year]
        annual_rows.append(
            [
                str(year),
                str(row["red_md"] or "缺测"),
                "" if row["delay_vs_dec5_days"] is None else f"{int(row['delay_vs_dec5_days']):+d}天",
                f"{float(row['oct_mean_c']):.2f}",
                f"{float(row['nov_mean_c']):.2f}",
                f"{float(row['oct_nov_mean_c']):.2f}",
                f"{float(row['nov_dec10_mean_c']):.2f}",
                str(row["nov_dec10_days_le_10c"]),
            ]
        )

    corr_rows = []
    labels = {
        "oct_nov_mean_c": "10-11月均温",
        "nov_mean_c": "11月均温",
        "nov_dec10_mean_c": "11/1-12/10均温",
        "nov_dec10_days_le_10c": "11/1-12/10 日均≤10°C天数",
        "dec_mean_c": "12月均温",
        "oct_mean_c": "10月均温",
    }
    for metric in labels:
        row = corr_by_metric[metric]
        corr_rows.append(
            [
                labels[metric],
                str(row["n"]),
                f"{float(row['pearson_r']):+.3f}",
                f"{float(row['slope_days_per_unit']):+.2f}",
                f"{float(row['r2']):.3f}",
            ]
        )

    nov = corr_by_metric["nov_mean_c"]
    oct_nov = corr_by_metric["oct_nov_mean_c"]
    cold = corr_by_metric["nov_dec10_days_le_10c"]

    text = f"""# 京都红叶季与气温关系：2010-2025

## 摘要

本研究把“红叶季时间”定义为气象厅京都地方气象台的官方 `かえでの紅葉日`（枫叶红叶日），并抓取京都站 2010—2025 年 10 月、11 月、12 月每日气温，探索气温与红叶时间偏差的关系。

关键发现：

- 京都官方枫叶红叶平年日为 `{normal_date}`，即 12 月 5 日。
- 2021 年京都 `かえでの紅葉` 在气象厅累年 CSV 中为 0，按缺测处理；相关性分析使用 15 个有效年份。
- 10 月单独解释力弱；11 月温度更关键。
- 11月均温每升高 1°C，官方红叶日大约推迟 {float(nov['slope_days_per_unit']):.1f} 天（Pearson r={float(nov['pearson_r']):.3f}）。
- 10—11月均温的相关性最高：r={float(oct_nov['pearson_r']):.3f}，每 +1°C 约晚 {float(oct_nov['slope_days_per_unit']):.1f} 天。
- 11/1—12/10 期间日均温 ≤10°C 的天数越多，红叶越早：r={float(cold['pearson_r']):.3f}。

## 数据源

1. 气象厅生物季节观测累年值 CSV：かえで紅葉
   {PHENOLOGY_URL}

2. 气象厅过去天气数据：京都站日别值
   {WEATHER_URL_TEMPLATE.replace('{year}', 'YYYY').replace('{month}', 'MM')}

## 年度汇总

{md_table(['年份', '官方红叶日', '较12/5', '10月均温°C', '11月均温°C', '10-11月均温°C', '11/1-12/10均温°C', '11/1-12/10≤10°C天数'], annual_rows)}

## 相关性结果

{md_table(['指标', '有效年份', 'Pearson r', '斜率：天/单位', 'R²'], corr_rows)}

## 旅行攻略解释

如果你要做抗偏差的京都红叶攻略，核心不是盯着 10 月，而是持续观察 11 月降温节奏。

- 11 月均温接近 11—12°C：红叶大概率正常或偏早，核心行程可押 11 月下旬到 12 月上旬。
- 11 月均温约 12.5—13.5°C：大概率略晚，更稳窗口是 11 月底到 12 月 10 日。
- 11 月均温 ≥14°C：明显偏晚风险上升，核心赏枫日应往 12 月上旬到中旬靠。
- 10 月热但 11 月中旬后转冷：不必过度恐慌，2025 年就是这种类型，最终只比平年晚 5 天。
- 10 月热、11 月也持续暖，尤其 11 月下旬仍不冷：要防 2024 年那种大幅推迟。

最稳通用窗口：11月28日—12月10日。
偏暖年份备用窗口：12月3日—12月14日。
偏冷年份可提前到：11月22日—12月5日。

## 限制

- 官方 `かえでの紅葉日` 是跨年份稳定指标，但不等价于所有寺社的旅游“见顷”日。
- 京都山区、高雄、大原、贵船、鞍马通常早于市区；清水寺、东福寺、下鸭神社等低海拔/市区景点可能更晚。
- 样本只有 15 个有效年份，适合判断方向和大致偏差，不适合精确预测某一天。

## 复现

```bash
python3 scripts/fetch_and_analyze.py
python3 -m unittest discover -s tests -v
```
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    red_dates, remarks, normal_date = parse_phenology()
    daily_rows = fetch_daily_weather()
    summary = build_summary(red_dates, remarks, daily_rows)
    correlations = build_correlations(summary)

    write_daily(daily_rows)
    write_summary(summary)
    write_correlations(correlations)
    write_report(summary, correlations, normal_date)

    print(f"Wrote {DAILY_PATH.relative_to(ROOT)}")
    print(f"Wrote {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Wrote {CORRELATION_PATH.relative_to(ROOT)}")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
