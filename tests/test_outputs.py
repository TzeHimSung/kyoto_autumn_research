import csv
import importlib
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
            ("表 1：年度观测与气温指标", "表格说明"),
            ("表 2：日别气温覆盖检查", "表格说明"),
            ("表 3：缺测处理规则", "表格说明"),
            ("表 4：温度指标与红叶延迟的统计关系", "表格说明"),
            ("图 1：年度红叶偏移与 11 月均温", "图表说明"),
            ("图 2：11 月均温与红叶延迟的回归关系", "图表说明"),
            ("图 3：温度指标相关性排序", "图表说明"),
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
