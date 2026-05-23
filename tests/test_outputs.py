import csv
import importlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "data" / "processed" / "kyoto_koyo_temperature_2010_2025_summary.csv"
DAILY = ROOT / "data" / "raw" / "kyoto_daily_temperature_oct_dec_2010_2025.csv"
CORRELATIONS = ROOT / "data" / "processed" / "correlation_results.csv"
NOTEBOOK = ROOT / "kyoto_autumn_research_workflow.ipynb"
REQUIREMENTS = ROOT / "requirements.txt"


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_notebook():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


class KyotoAutumnOutputsTest(unittest.TestCase):
    def test_expected_artifacts_exist(self):
        for path in [SUMMARY, DAILY, CORRELATIONS, NOTEBOOK, REQUIREMENTS]:
            self.assertTrue(path.exists(), f"missing artifact: {path.relative_to(ROOT)}")
            self.assertGreater(path.stat().st_size, 50, f"artifact too small: {path.relative_to(ROOT)}")

    def test_scientific_dependencies_are_declared_and_importable(self):
        requirements = REQUIREMENTS.read_text(encoding="utf-8")
        for package in ["numpy", "pandas", "matplotlib", "seaborn", "ipython"]:
            self.assertIn(package, requirements.lower())

        for module in ["numpy", "pandas", "matplotlib", "seaborn", "IPython"]:
            with self.subTest(module=module):
                importlib.import_module(module)

    def test_notebook_is_at_repository_root(self):
        self.assertEqual(NOTEBOOK.parent, ROOT)
        self.assertTrue(NOTEBOOK.exists())

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
        counts = {}
        for row in rows:
            key = (int(row["year"]), int(row["month"]))
            counts[key] = counts.get(key, 0) + 1
        expected_counts = {10: 31, 11: 30, 12: 31}
        self.assertEqual(set(counts), {(year, month) for year in range(2010, 2026) for month in (10, 11, 12)})
        for (year, month), count in counts.items():
            self.assertEqual(count, expected_counts[month], f"unexpected row count for {year}-{month:02d}")

    def test_daily_weather_includes_expanded_driver_columns(self):
        with DAILY.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = set(reader.fieldnames or [])

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
        self.assertTrue(expected_columns <= fieldnames)

        sample = next(row for row in rows if row["date"] == "2025-11-01")
        self.assertEqual(sample["precip_total_mm"], "0.000000")
        self.assertEqual(sample["t_mean_c"], "15.700000")
        self.assertEqual(sample["t_min_c"], "12.200000")
        self.assertEqual(sample["sunshine_hours"], "5.200000")
        self.assertEqual(sample["weather_day"], "曇後晴一時雨")

        dry_sample = next(row for row in rows if row["date"] == "2010-10-01")
        self.assertEqual(dry_sample["precip_total_mm"], "0.000000")

    def test_summary_and_correlations_include_expanded_weather_drivers(self):
        with SUMMARY.open(newline="", encoding="utf-8") as f:
            summary_reader = csv.DictReader(f)
            summary_rows = list(summary_reader)
            summary_fields = set(summary_reader.fieldnames or [])

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
            "first_5d_le_12_day_from_oct1",
            "first_5d_le_10_day_from_oct1",
        }
        self.assertTrue(expected_summary_columns <= summary_fields)

        row_2025 = next(row for row in summary_rows if row["year"] == "2025")
        for column in expected_summary_columns:
            self.assertNotEqual(row_2025[column], "", f"missing 2025 value for {column}")

        correlation_metrics = {row["metric"] for row in read_csv(CORRELATIONS)}
        expected_correlation_metrics = {
            "nov_min_mean_c",
            "nov_diurnal_range_mean_c",
            "nov_sunshine_hours_total",
            "nov_precip_total_mm",
            "max_gust_nov_dec10_ms",
        }
        self.assertTrue(expected_correlation_metrics <= correlation_metrics)

    def test_correlation_results_recompute_from_serialized_summary_csv(self):
        spec = importlib.util.spec_from_file_location(
            "fetch_and_analyze", ROOT / "scripts" / "fetch_and_analyze.py"
        )
        self.assertIsNotNone(spec)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        summary_rows = {int(row["year"]): row for row in read_csv(SUMMARY)}
        recomputed = {row["metric"]: row for row in module.build_correlations(summary_rows)}
        stored = {row["metric"]: row for row in read_csv(CORRELATIONS)}
        self.assertEqual(set(recomputed), set(stored))

        for metric, expected in stored.items():
            actual = recomputed[metric]
            with self.subTest(metric=metric):
                self.assertEqual(actual["n"], int(expected["n"]))
                for column in [
                    "pearson_r",
                    "spearman_r",
                    "slope_days_per_unit",
                    "intercept_days",
                    "r2",
                    "residual_se_days",
                ]:
                    self.assertTrue(
                        math.isclose(float(actual[column]), float(expected[column]), abs_tol=5e-7),
                        f"{metric} {column}: recomputed={actual[column]} stored={expected[column]}",
                    )

    def test_november_temperature_has_strong_positive_correlation_with_later_red_leaf_date(self):
        rows = {row["metric"]: row for row in read_csv(CORRELATIONS)}
        nov = rows["nov_mean_c"]
        r = float(nov["pearson_r"])
        slope = float(nov["slope_days_per_unit"])
        self.assertGreater(r, 0.70)
        self.assertTrue(math.isclose(slope, 2.979, abs_tol=0.02))

    def test_notebook_contains_sources_practical_window_sections_and_charts(self):
        notebook = read_notebook()
        self.assertEqual(notebook["nbformat"], 4)
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell["cell_type"] == "markdown"
        )
        for phrase in ["研究问题", "数据来源", "数据清洗", "统计分析", "结果可视化", "结论"]:
            self.assertIn(phrase, markdown)
        self.assertIn("https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv", markdown)
        self.assertIn("11月28日—12月10日", markdown)

        rich_figure_outputs = 0
        for cell in notebook["cells"]:
            for output in cell.get("outputs", []):
                data = output.get("data", {})
                html_output = data.get("text/html", "")
                if "image/svg+xml" in data or "image/png" in data or "<svg" in html_output:
                    rich_figure_outputs += 1
        self.assertGreaterEqual(rich_figure_outputs, 4)

    def test_each_table_and_figure_has_reading_guidance_and_explanation(self):
        notebook = read_notebook()
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell["cell_type"] == "markdown"
        )

        expected_items = [
            ("表 1：年度观测与天气指标", "表格说明"),
            ("表 2：日别天气覆盖检查", "表格说明"),
            ("表 3：缺测处理规则", "表格说明"),
            ("表 4：天气指标与红叶延迟的统计关系", "表格说明"),
            ("图 1：年度红叶偏移与 11 月均温", "图表说明"),
            ("图 2：11 月均温与红叶延迟的回归关系", "图表说明"),
            ("图 3：天气指标相关性排序", "图表说明"),
            ("图 4：10—12 月日别降温轨迹", "图表说明"),
        ]
        for title, explanation_label in expected_items:
            with self.subTest(title=title):
                start = markdown.find(title)
                self.assertNotEqual(start, -1, f"missing title: {title}")
                section = markdown[start : start + 900]
                self.assertIn("**阅读方法：**", section)
                self.assertIn(f"**{explanation_label}：**", section)
                self.assertGreaterEqual(len(section), 160)

    def test_notebook_uses_scientific_python_stack(self):
        notebook = read_notebook()
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell["cell_type"] == "code"
        )
        required_snippets = [
            "import numpy as np",
            "import pandas as pd",
            "import matplotlib",
            "import matplotlib.pyplot as plt",
            "import seaborn as sns",
            "pd.read_csv",
            "sns.regplot",
            "sns.heatmap",
            "np.polyfit",
        ]
        for snippet in required_snippets:
            self.assertIn(snippet, code)

    def test_notebook_uses_formal_academic_wording(self):
        text = NOTEBOOK.read_text(encoding="utf-8")
        banned_phrases = [
            "给人读的",
            "业务流程",
            "业务问题",
            "业务结论",
            "不必过度恐慌",
            "最有用的一张",
            "这张图",
        ]
        for phrase in banned_phrases:
            self.assertNotIn(phrase, text)

    def test_notebook_has_no_encoding_smells(self):
        raw_text = NOTEBOOK.read_text(encoding="utf-8")
        notebook = read_notebook()

        slash = "\\"
        byte_escape_pattern = re.escape(slash + "x") + r"[0-9A-Fa-f]{2}"
        unicode_degree_c_pattern = re.escape(slash + "u00") + r"[bB]0[cC]"
        mojibake_markers = [chr(0x00C2), chr(0x00C3), chr(0x00E2)]
        replacement_character = chr(0xFFFD)

        forbidden_patterns = {
            byte_escape_pattern: "literal Python byte escape",
            unicode_degree_c_pattern: "escaped degree-Celsius unit instead of literal °C",
            **{re.escape(marker): "common UTF-8 mojibake marker" for marker in mojibake_markers},
            re.escape(replacement_character): "Unicode replacement character",
        }
        for pattern, description in forbidden_patterns.items():
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, raw_text),
                    f"notebook contains {description}",
                )

        def iter_strings(value, path="notebook"):
            if isinstance(value, str):
                yield path, value
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    yield from iter_strings(item, f"{path}[{index}]")
            elif isinstance(value, dict):
                for key, item in value.items():
                    yield from iter_strings(item, f"{path}.{key}")

        parsed_forbidden = {
            byte_escape_pattern: "literal Python byte escape",
            **{re.escape(marker): "common UTF-8 mojibake marker" for marker in mojibake_markers},
            re.escape(replacement_character): "Unicode replacement character",
        }
        for path, value in iter_strings(notebook):
            for pattern, description in parsed_forbidden.items():
                self.assertIsNone(
                    re.search(pattern, value),
                    f"{path} contains {description}: {value[:120]!r}",
                )

        self.assertIn("°C", raw_text)

    def test_notebook_has_no_secrets_or_concrete_delivery_targets(self):
        text = NOTEBOOK.read_text(encoding="utf-8")
        forbidden = [
            r"telegram:-?\d{6,}",
            r"weixin:[^\s,'\"`]+@im\.wechat",
            r"(?i)(api_key|secret|password|token|passwd)\s*=\s*['\"][^'\"]{6,}['\"]",
        ]
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, text), f"forbidden pattern found: {pattern}")

    def test_notebook_code_cells_smoke_execute(self):
        notebook = read_notebook()
        code_cells = []
        for cell in notebook["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell.get("source", []))
            if source.lstrip().startswith(("%", "!")):
                continue
            code_cells.append(source)

        script = "\n\n# ---- next notebook cell ----\n\n".join(code_cells)
        env = os.environ.copy()
        env.setdefault("MPLBACKEND", "Agg")
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
            env=env,
        )
        self.assertEqual(
            result.returncode,
            0,
            "notebook code cells failed\nSTDOUT:\n"
            + result.stdout[-3000:]
            + "\nSTDERR:\n"
            + result.stderr[-3000:],
        )


if __name__ == "__main__":
    unittest.main()
