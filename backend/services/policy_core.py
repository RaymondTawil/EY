# -*- coding: utf-8 -*-
import json, joblib, numpy as np, pandas as pd
from pathlib import Path
from typing import Dict, Any

# -------------------------------
# Model & artifacts
# -------------------------------
MODEL_DIR = Path("models/saved_models")
MODEL_PATH = max(MODEL_DIR.glob("best_model_recall_focus_xgb_OptionA_recallAtK.joblib"), key=lambda p: p.stat().st_mtime)
META_PATH  = MODEL_DIR / "best_model_metadata.json"
POLICY_PATH = MODEL_DIR / "best_model_policy.json"  # optional standalone policy

best_model = joblib.load(MODEL_PATH)
with open(META_PATH, "r", encoding="utf-8") as f:
    META = json.load(f)

FEATURE_SET   = META["feature_set"]
NUM_COLS_META = META["numeric_columns"]
CAT_COLS_META = META["categorical_columns"]
REVIEW_K      = float(META.get("review_k", 0.20))
TOPK_THR_META = META.get("report", {}).get(f"Threshold@top_{int(REVIEW_K*100)}%")

def load_policy_thresholds() -> Dict[str, Any]:
    # 1) Prefer external policy.json
    if POLICY_PATH.exists():
        with POLICY_PATH.open("r", encoding="utf-8") as f:
            pol = json.load(f)
        thr_reject = pol.get("thresholds", {}).get("thr_reject")
        thr_review = pol.get("thresholds", {}).get("thr_review")
        if thr_reject is not None and thr_review is not None:
            return {"thr_reject": float(thr_reject), "thr_review": float(thr_review), "source": POLICY_PATH.name}
    # 2) Fallback to metadata thresholds
    pol_meta = META.get("policy", {}).get("thresholds", {})
    thr_reject = pol_meta.get("thr_reject")
    thr_review = pol_meta.get("thr_review")
    if thr_reject is not None and thr_review is not None:
        return {"thr_reject": float(thr_reject), "thr_review": float(thr_review), "source": "metadata"}
    # 3) Only a review cut → 2-band
    if TOPK_THR_META is not None:
        return {"thr_reject": None, "thr_review": float(TOPK_THR_META), "source": "meta_topk_only"}
    # 4) Last resort
    return {"thr_reject": None, "thr_review": 0.5, "source": "default_0.5"}

POLICY = load_policy_thresholds()

# -------------------------------
# Normalization (mirror training)
# -------------------------------
def parse_percent(x):
    import math
    if x is None or (isinstance(x, float) and math.isnan(x)): return np.nan
    s = str(x).strip().replace("%","")
    try: return float(s)
    except: return np.nan

def parse_term(x):
    if x is None: return np.nan
    s = str(x)
    try: return float("".join(ch for ch in s if ch.isdigit() or ch == "."))
    except: return np.nan

def parse_emp_length(x):
    if x is None: return np.nan
    s = str(x).strip().lower()
    if s in {"n/a","na","none",""}: return np.nan
    if s.startswith("<"): return 0.5
    if "10+" in s: return 10.0
    digits = "".join(ch for ch in s if ch.isdigit() or ch == ".")
    try: return float(digits)
    except: return np.nan

def normalize_payload(payload: dict) -> pd.DataFrame:
    row = {}
    # numeric
    row["loan_amnt"]       = payload.get("loan_amnt")
    row["int_rate"]        = parse_percent(payload.get("int_rate"))
    row["fico_range_low"]  = payload.get("fico_range_low")
    row["fico_range_high"] = payload.get("fico_range_high")
    row["annual_inc"]      = payload.get("annual_inc")
    dti_val = payload.get("dti")
    row["dti"]             = parse_percent(dti_val) if isinstance(dti_val, str) and "%" in str(dti_val) else dti_val
    row["revol_util"]      = parse_percent(payload.get("revol_util"))
    row["emp_length_num"]  = parse_emp_length(payload.get("emp_length"))
    row["term_num"]        = parse_term(payload.get("term"))
    # categoricals
    row["grade"]               = payload.get("grade")
    row["sub_grade"]           = payload.get("sub_grade")
    row["home_ownership"]      = payload.get("home_ownership")
    row["verification_status"] = payload.get("verification_status")
    row["purpose"]             = payload.get("purpose")

    prepared = {f: row.get(f, np.nan) for f in FEATURE_SET}
    for extra in ["emp_length_num","term_num"]:
        if extra in (NUM_COLS_META or []) and extra not in prepared:
            prepared[extra] = row.get(extra, np.nan)

    model_feats = FEATURE_SET.copy()
    for extra in ["emp_length_num","term_num"]:
        if extra in (NUM_COLS_META or []) and extra not in model_feats:
            model_feats.append(extra)

    df = pd.DataFrame([prepared], columns=model_feats)
    for c in NUM_COLS_META:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if NUM_COLS_META:
        df[NUM_COLS_META] = df[NUM_COLS_META].fillna(
            pd.Series({c: df[c].median() for c in NUM_COLS_META if c in df.columns})
        )
    for c in CAT_COLS_META:
        if c in df.columns:
            df[c] = df[c].astype("object").fillna("Unknown")
    return df

# -------------------------------
# Policy decision
# -------------------------------
def three_band_decision(prob: float, policy: dict) -> str:
    thr_reject = policy.get("thr_reject")
    thr_review = policy.get("thr_review")
    if thr_reject is not None and thr_review is not None:
        if prob >= thr_reject: return "REJECT"
        if prob >= thr_review: return "REVIEW"
        return "APPROVE"
    # 2-band fallback
    return "REVIEW" if prob >= float(thr_review) else "APPROVE"

def score_payload(payload: dict) -> Dict[str, Any]:
    x = normalize_payload(payload)
    prob = float(best_model.predict_proba(x)[:, 1][0])
    decision = three_band_decision(prob, POLICY)
    return {
        "prob_default": round(prob, 6),
        "decision": decision,
        "policy_source": POLICY.get("source"),
        "thresholds": {
            "thr_reject": None if POLICY.get("thr_reject") is None else float(POLICY["thr_reject"]),
            "thr_review": float(POLICY["thr_review"]) if POLICY.get("thr_review") is not None else None
        }
    }
