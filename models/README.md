## Data & Assumptions (applies to all notebooks)

- Binary classification: predict **default / reject** vs **good / accept** (naming may differ by dataset).
- Input contains a mix of **numeric** and **categorical** fields.
- Train/validation/test split is used to avoid leakage and to estimate generalization.
- Class imbalance is expected; PR‑AUC is emphasized for evaluation.
- Notebooks expect standard Python DS stack (pandas, numpy, scikit‑learn, xgboost).

If your raw files differ in column names or encodings, update the preprocessing cells accordingly.

---

## 1) `baseline.ipynb` — Minimal working model

**Goal:** Establish a transparent, end‑to‑end baseline to quantify lift above a naive rule.

**What it does**

- Lightweight preprocessing:
  - Selects a small set of core features.
  - Encodes categoricals with `OneHotEncoder` (no heavy feature engineering).
- Trains a simple tree‑based classifier (`DecisionTreeClassifier`) inside a `Pipeline`.
- Handles train/test split and computes core metrics:
  - **ROC‑AUC**, **PR‑AUC**, **confusion matrix**, **precision/recall/F1**.
- Produces **score distributions** and a **threshold sweep** so you can see how precision/recall trade off.
- Documents limitations (variance, instability, underfitting/overfitting risks).

**Outputs & artifacts**

- Baseline metrics on the hold‑out set.
- Optional serialized artifacts (e.g., `.joblib`) for the fitted pipeline if you choose to add a `dump` cell.

**When to use**

- As a sanity check that the data pipeline is sound.
- To set expectations and a floor for future improvements.

---

## 2) `improved.ipynb` — Higher performing, production‑oriented model

**Goal:** Increase predictive performance and robustness while maintaining clarity.

**What it adds**

- **Stronger model:** uses **`XGBClassifier`** with imbalance‑aware settings (`scale_pos_weight`) and `RandomizedSearchCV` for hyperparameter tuning.
- **Cleaner pipeline:**
  - Proper handling of numeric/categorical features with a `ColumnTransformer` or equivalent.
  - Systematic train/valid/test split and **metric tracking on the test set only once**.
- **Evaluation for decisions:**
  - PR‑AUC and ROC‑AUC comparisons vs baseline.
  - Threshold analysis including **top‑K% strategy** (e.g., review the riskiest top 5/10/20%).
  - Confusion matrices at business‑relevant operating points.
- **Reproducibility:**
  - Fixed random seeds where applicable.
  - Clear cells to **save the best model** (pipeline + estimator) as `.joblib`.
  - (Optional) Export of a simple **`policy.json`** template capturing default thresholds.

**Outputs & artifacts**

- Tuned model (recommended): `models/best_model.joblib` (or similar path).
- Policy template: `policy.json` (default threshold(s), top‑K settings).

**When to use**

- As your primary scoring model in subsequent systems (batch or real‑time).
- As the reference for performance tracking over time.

---

## 3) `policy.ipynb` — Turning scores into actions

**Goal:** Define a **repeatable, auditable decision policy** that sits on top of model scores and supports credit officers.

**What it does**

- Loads the **best saved model** (e.g., `.joblib`) and applies it to new applications.
- Computes calibrated **probabilities** (`predict_proba`) and applies a **policy**:
  - **Fixed threshold**: e.g., reject if `p(default) ≥ τ`.
  - **Top‑K review queue**: flag the **riskiest K%** for manual review.
  - (Optional) **Dual‑threshold band**: auto‑approve low‑risk, auto‑reject high‑risk, manual‑review the gray zone.
- Encodes the chosen policy in a small, human‑readable **`policy.json`** (thresholds, top‑K, notes).
- Generates officer‑friendly outputs (lists of **REJECT / REVIEW / APPROVE**), with supporting score columns for transparency.
- Includes hooks to persist decisions and export CSV/JSON as needed.

**Outputs & artifacts**

- `policy.json` — canonical definition of current operating point(s).
- Decision tables (e.g., `decisions.csv`) suitable for workflows and audit.


## Reproducibility & Environment

- Python ≥ 3.9, packages: `pandas`, `numpy`, `scikit-learn`, `xgboost`, `joblib`, `matplotlib`.
- Set a consistent random seed where possible.
- Keep train/test splits stable when comparing models.
- Version control the following:
  - **Data schema** (feature list, dtypes).
  - **Model artifacts** (`.joblib`).
  - **Policy** (`policy.json`) and any **business-rule overrides**.

---

## TL;DR

- `baseline.ipynb`: clear, minimal benchmark (+ metrics & threshold sweep).
- `improved.ipynb`: tuned **XGBoost** pipeline (+ top‑K analysis, artifact export, policy template).
- `policy.ipynb`: deployable decision policy (thresholds / top‑K) that converts scores into **consistent actions**.


