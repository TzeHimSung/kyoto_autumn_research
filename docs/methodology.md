# Methodology

## Research question

Can Kyoto autumn foliage timing be usefully estimated from October-to-December temperature patterns?

The practical motivation is travel planning: if a year is warmer or colder than usual, should the Kyoto autumn foliage itinerary be shifted earlier or later?

## Definition of foliage timing

This repository uses the Japan Meteorological Agency biological phenology observation `かえでの紅葉日` for Kyoto as the target variable.

This is a deliberate choice:

- It is official and consistently measured across years.
- It is available as a cumulative CSV.
- It gives a single comparable date per year.

It is not identical to tourist-facing `見頃` dates for specific temples. Individual sites differ by elevation, exposure, tree species, garden microclimate, and management. Treat the official date as a city-level reference signal, not as a site-level forecast.

## Data sources

### Red-leaf date

JMA biological phenology cumulative CSV:

https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv

Encoding: Shift-JIS.

The script extracts the row whose station name starts with `京都` and reads yearly values for 2010—2025.

The JMA normal date from the same CSV is 12/05 for Kyoto maple red leaves. This repository uses 12/05 as the zero point for delay calculations.

### Temperature

JMA historical daily weather data, Kyoto station:

https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no=61&block_no=47759&year=YYYY&month=MM&day=&view=p1

The script fetches October, November, and December daily values for every year 2010—2025 and parses:

- Daily mean temperature, °C
- Daily maximum temperature, °C
- Daily minimum temperature, °C

## Derived variables

For each year, the pipeline computes:

- `red_date`: official Kyoto `かえでの紅葉日`
- `delay_vs_dec5_days`: days after 12/05; negative values mean earlier than normal
- `oct_mean_c`: October mean daily temperature
- `nov_mean_c`: November mean daily temperature
- `dec_mean_c`: December mean daily temperature
- `oct_nov_mean_c`: October-November mean daily temperature
- `nov_dec10_mean_c`: November 1 to December 10 mean daily temperature
- `nov16_dec10_mean_c`: November 16 to December 10 mean daily temperature
- `nov_days_le_10c`: count of November days with daily mean temperature ≤10°C
- `nov_days_le_12c`: count of November days with daily mean temperature ≤12°C
- `nov_dec10_days_le_10c`: count of November 1 to December 10 days with daily mean temperature ≤10°C
- `nov_dec10_days_le_12c`: count of November 1 to December 10 days with daily mean temperature ≤12°C
- `first_5d_mean_le_12`: first date after November 1 when trailing 5-day mean temperature is ≤12°C
- `first_5d_mean_le_10`: first date after November 1 when trailing 5-day mean temperature is ≤10°C

## Missing data policy

The 2021 Kyoto `かえでの紅葉` value in the JMA cumulative CSV is `0`.

The repository treats this as missing and excludes 2021 from correlations involving red-leaf timing. Temperature rows for 2021 are still retained in the raw and summary data.

## Statistical analysis

The script computes:

- Pearson correlation between each temperature metric and `delay_vs_dec5_days`
- Spearman rank correlation
- Simple one-variable linear regression slope
- R²
- Residual standard error in days

The model is intentionally simple. The goal is not to build a black-box forecast; it is to identify interpretable travel-planning signals.

## Interpretation rules

The strongest practical signal is November temperature.

Empirical result from 2010—2025 valid years:

- 11月均温 vs red-leaf delay: Pearson r≈0.714
- 11月均温 +1°C corresponds to roughly +3 days later official red-leaf date
- 10月均温 alone has weak explanatory power: r≈0.309

Recommended travel-planning heuristic:

- 11 月均温 11—12°C: normal or early season risk profile
- 11 月均温 12.5—13.5°C: slightly late risk profile
- 11 月均温 ≥14°C: significantly late risk profile

## Limitations

1. Small sample size

Only 15 years have valid red-leaf dates from 2010—2025. The results are directionally useful but should not be overfit.

2. Official date vs tourist peak

The official `かえでの紅葉日` is not exactly the peak color date at 清水寺, 東福寺, 永観堂, 嵐山, 高雄, 大原, or other individual sites.

3. Geography inside Kyoto matters

Higher-elevation and northern sites are earlier; central and low-elevation sites are later. A single Kyoto-wide indicator necessarily hides that spread.

4. Temperature is not the only factor

Solar radiation, rainfall, typhoons, leaf damage, tree health, and species composition also matter. This repository currently analyzes temperature only.

## Reproduction

Run from the repository root:

```bash
python3 scripts/fetch_and_analyze.py
python3 -m unittest discover -s tests -v
```

The tests verify:

- Output artifacts exist
- 2024 official red-leaf date is 2024-12-20
- 2025 official red-leaf date is 2025-12-10
- 2021 official red-leaf date is treated as missing
- Daily weather data covers October, November, and December for all 2010—2025 years
- November temperature correlation is strongly positive
- Report contains source URLs and the practical travel window
