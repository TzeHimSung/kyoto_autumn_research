# Initial Kyoto Autumn Temperature Analysis Implementation Plan

> **For Hermes:** Use this as the repository bootstrap plan for the Kyoto autumn foliage / temperature correlation research.

**Goal:** Preserve the 2010-2025 Kyoto autumn foliage analysis in a reproducible GitHub repository with data, scripts, tests, and a human-readable report.

**Architecture:** Use a small standard-library Python pipeline. The pipeline downloads official JMA phenology and daily weather data, computes annual aggregates and correlations, and writes deterministic CSV/Markdown outputs. Tests validate key invariants against known official values and computed correlations.

**Tech Stack:** Python 3 standard library, Git, GitHub SSH remote.

---

### Task 1: Establish validation tests first

**Objective:** Add tests that define the expected repository outputs and core numeric invariants before implementation.

**Files:**
- Create: `tests/test_outputs.py`

**Steps:**
1. Write tests for expected CSV/report existence, 2024/2025 official red-leaf dates, 2021 missing red-leaf observation, and 11月均温 correlation being strongly positive.
2. Run `python3 -m unittest discover -s tests -v` and confirm failure because files do not exist yet.

### Task 2: Add reproducible analysis pipeline

**Objective:** Add a standard-library Python script that fetches JMA data, computes summaries, correlations, and reports.

**Files:**
- Create: `scripts/fetch_and_analyze.py`
- Create generated outputs under `data/processed/`, `data/raw/`, and `reports/`

**Steps:**
1. Implement fetchers for JMA phenology CSV and daily weather HTML pages.
2. Parse Kyoto station daily mean/max/min temperatures for Oct-Dec 2010-2025.
3. Parse Kyoto official `かえでの紅葉` cumulative values for 2010-2025.
4. Compute annual mean temperatures, cold-day counts, red-leaf delays, Pearson/Spearman correlations, and simple linear slopes.
5. Write deterministic CSV and Markdown outputs.
6. Run the script and inspect generated artifacts.

### Task 3: Document method and results

**Objective:** Replace placeholder README with enough context for future maintenance.

**Files:**
- Modify: `README.md`
- Create: `docs/methodology.md`

**Steps:**
1. State data sources, definitions, caveats, and reproduction command.
2. Include headline findings and practical travel interpretation.
3. Link to data and report files.

### Task 4: Verify, review, commit, and push

**Objective:** Ensure the repo is clean, reproducible, and safe to publish.

**Files:**
- All changed files

**Steps:**
1. Run `python3 scripts/fetch_and_analyze.py`.
2. Run `python3 -m unittest discover -s tests -v`.
3. Run static scans for tokens/secrets and public delivery targets.
4. Review `git diff`.
5. Commit with a conventional message and push.
