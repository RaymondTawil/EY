# LendingClub EDA — Accepted vs Rejected (2017–2018, 50k sample)

This repository contains two Jupyter notebooks:

* `accepted_eda.ipynb` — Exploratory Data Analysis (EDA) on **accepted** LendingClub loans.
* `rejected_eda.ipynb` — EDA on **rejected** LendingClub applications.

Both notebooks focus **only** on applications from **2017–2018**, down-sampled to **50,000** rows, and restrict themselves to **descriptive analysis** (no ML modeling). The goal is to understand the data shape, quality, and the patterns that could inform **credit policy** and **pricing playbooks**.

---

## 1) `rejected_eda.ipynb` — Rejected Applications

### What this notebook does

1. **Loads & cleans** the Kaggle *RejectStats* file:

   * Parses numeric fields: `Amount Requested`, `Debt-To-Income Ratio` (DTI), `Risk_Score`.
   * Normalizes text/categorical fields: `Employment Length`, `State`, `Zip Code` (ZIP3).
2. **Filters** to years **2017–2018** and **samples** to **n=50,000**.
3. **Engineers policy-friendly bands** for fast diagnostics:

   * DTI bands (≤15, 15–25, 25–35, 35–40, 40–45, ≥45).
   * Risk score bands (e.g., <580, 580–619, 620–659, 660–699, ≥700, and **NaN**).
   * Amount bands (≤$2.5k, $2.5–5k, $5–10k, $10–20k, $20–40k, >$40k).
   * Employment length buckets (`<1y`, `1–2y`, `3–5y`, `6–9y`, `10+y`, `n/a`).
4. **Visualizes**:

   * Distributions (DTI, Risk_Score, Amount).
   * **Share of rejections** by each band.
   * **Concentration heatmaps** (e.g., DTI × Risk_Score, Amount × Risk_Score).
   * **Seasonality** of rejections (monthly counts).

### Key results

* **Massive score missingness.** A dominant share of rejected rows have **`Risk_Score = NaN`**. Among non-missing, scores are roughly bell-shaped ~**580–720** with a hump around **620–680**.
  → **Implication:** Policies must define a **fallback path** when score is absent (e.g., tighter DTI caps, smaller ticket sizes, or enhanced verification).

* **DTI alone doesn’t explain declines.** Rejections occur across the spectrum; notable volume at **≤25% DTI**, another bump **>50%**.
  → **Implication:** Many declines are driven by **multi-factor** rules (score, tenure, amount, manual flags), not DTI alone.

* **Short employment tenure is common.** `<1y` (and `<2y`) buckets are **over-represented** among rejections.
  → **Implication:** Tenure should be an explicit overlay—e.g., stricter treatment for **emp_len < 2y** in borderline score bands.

* **Ticket size pressure.** Concentration of rejections in **$2.5–10k** and **$10–20k** bands, with visible interplay with mid-score bands (620–699).
  → **Implication:** Counter-offers (reduced amounts) could convert borderline declines in these bands.

* **Capacity/seasonality.** Monthly plots show **peaks and troughs** in rejection volume.
  → **Implication:** Staff & **pre-tune thresholds** ahead of peak months; consider **geo-aware** verification pilots in top-ZIP3s by rejection concentration.

> **Policy-shaping takeaways:**
>
> * Define **no-score** playbooks (tighter DTI & amount caps; stronger verification).
> * Keep/clarify **hard DTI caps** (e.g., decline at ≥45–50%; enhanced review at 40–45%).
> * Overlay **employment tenure** rules (stricter for `<2y`, especially with mid-scores).
> * Use **counter-offer** logic in **$2.5–10k** (and up to $20k) for **620–699** bands.
> * Plan **ops capacity** with seasonality; pilot **ZIP3-targeted** verifications.

---

## 2) `accepted_eda.ipynb` — Accepted Loans

### What this notebook does

1. **Loads & cleans** the Kaggle *Accepted* file:

   * Keeps core pricing & risk fields: `loan_amnt`, `term`, `int_rate`, `grade`, `sub_grade`, `fico_range_low/high`, `annual_inc`, `dti`, `revol_util`, `emp_length`, `home_ownership`, `verification_status`, `purpose`, `issue_d`.
2. **Filters** to **2017–2018** and **samples** to **n=50,000**.
3. **Quality checks & summaries** (descriptives, distributions).
4. **Explores pricing structure**:

   * Interest rate distributions and **grade/term** interactions.
   * **Boxplots** of `int_rate` by `grade` and by `term`.
   * Purpose mix and verification cohorts.
   * Pairwise correlations among key numerics.
5. **Outputs** clean, publication-ready charts.

### Key results

* **Pricing bands are clear.** `int_rate` centers around **~12.9%** (IQR ~**9.4–16.0%**), with a capped tail near **~26–27%**.
  → **Implication:** The book exhibits **tiered, discrete pricing** consistent with risk segmentation.

* **Grade drives price cleanly.** **Monotonic A→G** increase in rates; spread widens for **E–G**, indicating more heterogeneous risk in lower grades.

* **Term risk priced in.** **60-month** loans carry **higher** and **wider-spread** rates than **36-month** loans—reflecting longer exposure and/or selection effects.

* **Borrower risk mix.** FICO midpoint around **~705**; DTI is bell-shaped (roughly **10–25%**), with a **pile-up near cap (~40–43%)** and a small spike near **0%** (possible data/behavioral anomalies).

* **Leverage stress visible.** `revol_util` mean around **~40–50%**, with spikes at **~0%** and **~100%** (thin files vs maxed lines).

* **Purpose concentration.** **Debt consolidation + credit card ≈ ~77%** of volume (rest are small tails like home improvement, major purchase, etc.).
  → **Implication:** Operational playbooks should prioritize these two use-cases.

* **Verification cohorts differ.** “Verified” groups tend to show **higher median/mean rates** (selection into verification).

* **Correlations (directionally):**

  * `int_rate` **negatively** correlated with FICO (higher FICO → lower rate).
  * `dti` **positively** with `revol_util`.
  * `annual_inc` **negatively** with `dti`; **positively** with `loan_amnt`.
  * `fico_range_low` ≈ `fico_range_high` → duplicate signal; using one (or their mean) is sufficient for EDA.

> **Policy-shaping takeaways:**
>
> * **Segment by grade & term:** Stricter rules for **E–G** and **60-month** loans; lighter touch for **A–B / 36-month**.
> * **Codify DTI checks:** Maintain cap (~**40–43%**); **flag DTI≈0%** and extremely high `revol_util` (≥90–100%) for manual review.
> * **Focus ops where volume is:** Tailor **verification & counter-offers** to **debt consolidation** and **credit card** segments.
> * **Reduce redundancy:** Treat `fico_range_low/high` as near-duplicates in reporting.

---

## Data & Scope

* **Source:** Kaggle — *Lending Club Loan Data (Accepted & Rejected)*.
* **Temporal scope:** **2017–2018** only.
* **Sample size:** **50,000** rows per notebook.
* **Analysis type:** **Exploratory** (descriptive statistics & plots); **no machine learning** or outcome modeling used in conclusions here.

> **Note:** The notebooks assume the raw CSVs are available under `../data/accepted_2007_to_2018Q4.csv` and `../data/rejected_2007_to_2018Q4.csv` relative to the notebooks’ folder. Adjust paths as needed.

---

## How to Run

1. Create a Python environment with the usual scientific stack:

   ```bash
   pip install -r requirements.txt
   ```
2. Place the Kaggle CSVs under `data/` (or update the paths at the top of each notebook).
3. Open and execute:

   * `accepted_eda.ipynb`
   * `rejected_eda.ipynb`

The notebooks will:

* Filter to 2017–2018,
* Sample to 50k rows,
* Produce all charts inline.
