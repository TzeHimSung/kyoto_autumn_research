# Notebook Workflow Presentation Implementation Plan

> **For Hermes:** Implement directly in this small documentation-focused change; use validator-style checks rather than full TDD because the main artifact is a notebook presentation.

**Goal:** Make the Kyoto autumn research easier to read by adding a guided Jupyter notebook that walks through data acquisition, cleaning, analysis, and conclusions.

**Architecture:** Keep the reproducible pipeline in `scripts/fetch_and_analyze.py` as the source of truth. Add `notebooks/kyoto_autumn_research_workflow.ipynb` as a readable, executable presentation layer that imports the pipeline helpers and shows tables/mini-charts/results step by step. Add tests that validate notebook structure and smoke-execute it without requiring third-party packages.

**Tech Stack:** Python 3 standard library, Jupyter notebook JSON format, unittest.

---

### Task 1: Create notebook artifact

**Objective:** Add a readable notebook organized around the business process.

**Files:**
- Create: `notebooks/kyoto_autumn_research_workflow.ipynb`

**Steps:**
1. Include markdown sections: overview, data acquisition, data cleaning, calculation analysis, conclusion.
2. Include code cells using only the Python standard library.
3. Import `scripts/fetch_and_analyze.py` for reusable parsing/statistics functions instead of duplicating pipeline code.
4. Prefer reading existing generated CSVs for fast execution, while showing the exact command to re-fetch live JMA data.
5. Add compact text tables and an ASCII mini bar chart for terminal/GitHub readability.

### Task 2: Update tests

**Objective:** Make notebook validity part of the repository's regression checks.

**Files:**
- Modify: `tests/test_outputs.py`

**Steps:**
1. Verify the notebook file exists.
2. Verify it has markdown headings for 数据获取、数据清洗、计算分析、总结结论.
3. Verify it has no hardcoded secrets or concrete messaging delivery targets.
4. Smoke-execute code cells in order with `exec`, skipping only IPython magic/shell cells if any are later added.

### Task 3: Update README

**Objective:** Point readers to the notebook as the recommended entry point.

**Files:**
- Modify: `README.md`

**Steps:**
1. Add a “Recommended reading order” section.
2. Put the notebook before the raw report and CSVs.
3. Keep CLI reproduction commands unchanged.

### Task 4: Verify and publish

**Objective:** Prove the notebook works before pushing.

**Commands:**
```bash
python3 scripts/fetch_and_analyze.py
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/fetch_and_analyze.py tests/test_outputs.py
```

Also run static scans and independent review before commit/push.
