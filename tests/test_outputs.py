import csv
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "data" / "processed" / "kyoto_koyo_temperature_2010_2025_summary.csv"
DAILY = ROOT / "data" / "raw" / "kyoto_daily_temperature_oct_dec_2010_2025.csv"
CORRELATIONS = ROOT / "data" / "processed" / "correlation_results.csv"
REPORT = ROOT / "reports" / "kyoto_autumn_temperature_correlation_2010_2025.md"


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class KyotoAutumnOutputsTest(unittest.TestCase):
    def test_expected_artifacts_exist(self):
        for path in [SUMMARY, DAILY, CORRELATIONS, REPORT]:
            self.assertTrue(path.exists(), f"missing artifact: {path.relative_to(ROOT)}")
            self.assertGreater(path.stat().st_size, 100, f"artifact too small: {path.relative_to(ROOT)}")

    def test_summary_has_expected_years_and_official_red_dates(self):
        rows = {int(row["year"]): row for row in read_csv(SUMMARY)}
        self.assertEqual(set(rows), set(range(2010, 2026)))
        self.assertEqual(rows[2024]["red_date"], "2024-12-20")
        self.assertEqual(rows[2024]["delay_vs_dec5_days"], "15")
        self.assertEqual(rows[2025]["red_date"], "2025-12-10")
        self.assertEqual(rows[2025]["delay_vs_dec5_days"], "5")
        self.assertEqual(rows[2021]["red_date"], "")
        self.assertEqual(rows[2021]["delay_vs_dec5_days"], "")

    def test_daily_temperature_covers_october_to_december_for_all_years(self):
        rows = read_csv(DAILY)
        self.assertEqual(len(rows), 16 * (31 + 30 + 31))
        months = {(int(row["year"]), int(row["month"])) for row in rows}
        self.assertEqual(months, {(year, month) for year in range(2010, 2026) for month in (10, 11, 12)})

    def test_november_temperature_has_strong_positive_correlation_with_later_red_leaf_date(self):
        rows = {row["metric"]: row for row in read_csv(CORRELATIONS)}
        nov = rows["nov_mean_c"]
        r = float(nov["pearson_r"])
        slope = float(nov["slope_days_per_unit"])
        self.assertGreater(r, 0.70)
        self.assertTrue(math.isclose(slope, 2.979, abs_tol=0.02))

    def test_report_contains_source_urls_and_practical_window(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv", text)
        self.assertIn("11月28日—12月10日", text)
        self.assertIn("11月均温每升高 1°C", text)


if __name__ == "__main__":
    unittest.main()
