# Expanded Kyoto Foliage Weather Drivers Implementation Plan

> **For Hermes:** Use repository-development guidelines and TDD. Implement task-by-task; verify with tests, scans, and independent review before commit/push.

**Goal:** Extend the Kyoto autumn foliage research repo beyond mean temperature by adding a first-phase set of weather drivers that plausibly influence official red-leaf timing and tourist viewing quality.

**Architecture:** Keep the source set conservative: reuse the existing JMA Kyoto station daily weather page and official JMA `かえでの紅葉日` proxy. Expand the standard-library fetch/analyze script to parse more columns, derive interpretable annual features, regenerate CSV artifacts, and update the notebook/README so conclusions stay reproducible.

**Tech Stack:** Python standard library for `scripts/fetch_and_analyze.py`; existing pandas/NumPy/Matplotlib/Seaborn notebook; `unittest` for repository checks.

---

## Scope

First-phase dimensions to add:

1. **Night cooling / minimum temperature**
   - `nov_min_mean_c`
   - `nov_dec10_min_mean_c`
   - `nov_min_days_le_8c`
   - `nov_min_days_le_5c`
   - `first_min_le_8`
   - `first_min_le_8_day_from_oct1`

2. **Day-night range**
   - `nov_diurnal_range_mean_c`
   - `nov_dec10_diurnal_range_mean_c`
   - `nov_days_range_ge_10c`

3. **Sunshine**
   - `nov_sunshine_hours_total`
   - `nov_dec10_sunshine_hours_total`
   - `sunny_cold_nights_nov_dec10` where sunshine is at least 5h and daily minimum is at most 8°C.

4. **Precipitation / rain damage proxy**
   - `oct_nov_precip_total_mm`
   - `nov_precip_total_mm`
   - `rain_days_nov`
   - `heavy_rain_days_after_nov15` where daily precipitation is at least 20mm.

5. **Wind / storm damage proxy**
   - `max_gust_nov_dec10_ms`
   - `windy_days_after_nov15` where daily maximum gust is at least 10 m/s.

## Non-goals

- Do not introduce third-party tourism website scraping in this pass.
- Do not build a multivariate predictive model; 2010–2025 has only 15 effective official red-leaf observations after excluding 2021.
- Do not claim attraction-level peak forecasts. Keep JMA `かえでの紅葉日` as the official city-level proxy.
- Do not add new package dependencies.

## Affected Files

- Modify: `scripts/fetch_and_analyze.py`
- Modify generated data: `data/raw/kyoto_daily_temperature_oct_dec_2010_2025.csv`
- Modify generated data: `data/processed/kyoto_koyo_temperature_2010_2025_summary.csv`
- Modify generated data: `data/processed/correlation_results.csv`
- Modify: `kyoto_autumn_research_workflow.ipynb`
- Modify: `README.md`
- Modify: `tests/test_outputs.py`

---

### Task 1: Add failing tests for expanded raw weather columns

**Objective:** Ensure the daily raw CSV captures the additional JMA weather dimensions needed for analysis.

**Files:**
- Modify: `tests/test_outputs.py`

**Step 1: Write failing test**

Add a test asserting `DAILY` contains these columns:

```python
expected_columns = {
    "precip_total_mm",
    "humidity_mean_pct",
    "humidity_min_pct",
    "wind_mean_ms",
    "wind_max_ms",
    "gust_max_ms",
    "sunshine_hours",
    "weather_day",
    "weather_night",
}
```

Also assert representative 2025-11-01 values from JMA are stable enough to validate parsing:

```python
row = next(row for row in rows if row["date"] == "2025-11-01")
self.assertEqual(row["precip_total_mm"], "0.000000")
self.assertEqual(row["t_mean_c"], "15.700000")
self.assertEqual(row["t_min_c"], "12.200000")
self.assertEqual(row["sunshine_hours"], "5.200000")
self.assertEqual(row["weather_day"], "曇後晴一時雨")
```

**Step 2: Run failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_outputs.KyotoAutumnOutputsTest.test_daily_weather_includes_expanded_driver_columns -v
```

Expected: FAIL because the new columns are absent.

---

### Task 2: Add failing tests for derived annual driver features

**Objective:** Lock the summary and correlation schema before production code changes.

**Files:**
- Modify: `tests/test_outputs.py`

**Step 1: Write failing test**

Assert `SUMMARY` has columns for the five chosen dimensions and that rows contain non-empty values for years with daily data.

Required columns:

```python
expected_summary_columns = {
    "nov_min_mean_c",
    "nov_dec10_min_mean_c",
    "nov_min_days_le_8c",
    "nov_min_days_le_5c",
    "first_min_le_8",
    "first_min_le_8_day_from_oct1",
    "nov_diurnal_range_mean_c",
    "nov_dec10_diurnal_range_mean_c",
    "nov_days_range_ge_10c",
    "nov_sunshine_hours_total",
    "nov_dec10_sunshine_hours_total",
    "sunny_cold_nights_nov_dec10",
    "oct_nov_precip_total_mm",
    "nov_precip_total_mm",
    "rain_days_nov",
    "heavy_rain_days_after_nov15",
    "max_gust_nov_dec10_ms",
    "windy_days_after_nov15",
}
```

Assert `CORRELATIONS` includes at least:

```python
{
    "nov_min_mean_c",
    "nov_diurnal_range_mean_c",
    "nov_sunshine_hours_total",
    "nov_precip_total_mm",
    "max_gust_nov_dec10_ms",
}
```

**Step 2: Run failure**

Run:

```bash
.venv/bin/python -m unittest tests.test_outputs.KyotoAutumnOutputsTest.test_summary_and_correlations_include_expanded_weather_drivers -v
```

Expected: FAIL because features are absent.

---

### Task 3: Expand JMA daily parser and raw CSV writer

**Objective:** Parse additional JMA daily table columns without adding dependencies.

**Files:**
- Modify: `scripts/fetch_and_analyze.py`
- Regenerate: `data/raw/kyoto_daily_temperature_oct_dec_2010_2025.csv`

**Implementation notes:**

Daily table indices for `view=p1`:

- `values[3]`: daily total precipitation mm
- `values[9]`: mean humidity percent
- `values[10]`: minimum humidity percent
- `values[11]`: mean wind speed m/s
- `values[12]`: maximum wind speed m/s
- `values[14]`: maximum gust m/s
- `values[16]`: sunshine hours
- `values[19]`: daytime weather summary
- `values[20]`: nighttime weather summary

Use existing `parse_float` for numeric fields. Keep weather text as strings.

**Verification:**

Run the Task 1 test and confirm it passes.

---

### Task 4: Add annual feature builders and correlation metrics

**Objective:** Derive interpretable annual features from expanded daily weather rows.

**Files:**
- Modify: `scripts/fetch_and_analyze.py`
- Regenerate: `data/processed/kyoto_koyo_temperature_2010_2025_summary.csv`
- Regenerate: `data/processed/correlation_results.csv`

**Implementation notes:**

Add helper functions:

- `sum_values(rows, key)`
- `count_numeric_threshold(rows, key, threshold, op)` or small explicit count helpers
- `first_threshold_date(rows, year, key, threshold, op, start_date)`
- `diurnal_range(row)`

Add selected new metrics to `build_summary()` and include a curated subset in `build_correlations()`.

**Verification:**

Run the Task 2 test and confirm it passes.

---

### Task 5: Update notebook and README with analysis framing

**Objective:** Make the research artifact explain the expanded dimensions without overclaiming.

**Files:**
- Modify: `kyoto_autumn_research_workflow.ipynb`
- Modify: `README.md`

**Notebook requirements:**

- Keep every table/figure section with `**阅读方法：**` and `**表格说明：**` or `**图表说明：**`.
- Add a section distinguishing:
  - drivers of official red-leaf timing;
  - drivers of tourist viewing quality / window durability.
- Add or update at least one table showing expanded weather driver correlations.
- Do not introduce multivariate overfitting claims.
- Retain all source URLs.

**README requirements:**

- Update research question from “temperature only” to “weather drivers, starting from temperature”.
- Add a concise paragraph listing the added dimensions and the reason they matter.
- Keep date-window recommendations conservative.

---

### Task 6: Full verification and review

**Objective:** Prove the repo remains reproducible and safe.

**Commands:**

```bash
.venv/bin/python scripts/fetch_and_analyze.py
.venv/bin/python -m unittest discover -s tests -v
```

Additional scans:

- Git tracked file encoding smell scan.
- Static diff scan for hardcoded secrets, concrete delivery targets, shell injection, `eval`/`exec`, unsafe pickle, SQL string formatting.
- `git diff --stat` and human diff review.
- Independent `delegate_task` code review before commit/push.

**Expected:** All tests pass, scans report zero blocking findings, independent review passes.
