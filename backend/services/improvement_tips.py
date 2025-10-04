# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import copy
from typing import Any, Dict, List, Tuple, Optional
from functools import lru_cache
import os

from backend.services.policy_core import score_payload, POLICY

USE_LLM = True
try:
    from openai import OpenAI
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

# ---------- utilities ----------
def _copy(d: Dict) -> Dict:
    return copy.deepcopy(d)

def _pct_to_float(x: Any) -> Optional[float]:
    if x is None: return None
    s = str(x).strip()
    if s.endswith("%"): s = s[:-1]
    try: return float(s)
    except: return None

def _fmt_pct(x: float) -> str:
    return f"{x:.1f}%"

def _to_float(x: Any) -> Optional[float]:
    try: return float(x)
    except: return None

def _thr_review() -> float:
    return float(POLICY.get("thr_review", 0.5))

def _freeze_payload_for_cache(p: Dict) -> str:
    """
    Make payload hashable & stable for caching. Keep only common fields that
    affect scoring (adjust to your feature set if needed).
    """
    keys = [
        "loan_amnt","int_rate","fico_range_low","fico_range_high",
        "annual_inc","dti","revol_util","emp_length","term",
        "grade","sub_grade","home_ownership","verification_status","purpose",
        # keep names too so the LLM message can be personalized,
        # but they don't affect PD so they could be omitted from cache key
        "first_name","last_name"
    ]
    slim = {k: p.get(k) for k in keys if k in p}
    return json.dumps(slim, sort_keys=True)

@lru_cache(maxsize=4096)
def _score_cached(payload_key: str) -> float:
    payload = json.loads(payload_key)
    return float(score_payload(payload)["prob_default"])

def _get_pd(payload: Dict) -> float:
    return _score_cached(_freeze_payload_for_cache(payload))

# ---------- fast candidate generation (small, discrete set) ----------
def _concrete_candidates(payload: Dict) -> List[Tuple[str, Dict]]:
    """
    Returns a compact list of realistic, concrete tweaks with numbers.
    This is intentionally small to keep latency low.
    """
    cands: List[Tuple[str, Dict]] = []

    # Amount cuts (10%, 20%, 30%)
    base_amt = _to_float(payload.get("loan_amnt")) or 0.0
    for frac in (0.9, 0.8, 0.7):
        if base_amt > 0:
            q = _copy(payload)
            tgt = max(1000, round(base_amt * frac, 0))
            q["loan_amnt"] = tgt
            cands.append((f"Reduce loan amount by ${int(base_amt - tgt):,} (target ${int(tgt):,})", q))

    # Term switch to 36m
    term = str(payload.get("term","")).lower()
    if term.startswith("60"):
        q = _copy(payload); q["term"] = "36 months"
        cands.append(("Switch to a 36-month term", q))

        # Combo: 36m + 10% cut (often powerful)
        if base_amt > 0:
            q2 = _copy(payload); q2["term"] = "36 months"
            tgt = max(1000, round(base_amt * 0.9, 0))
            q2["loan_amnt"] = tgt
            cands.append((f"Switch to 36 months and reduce amount by ${int(base_amt - tgt):,} (target ${int(tgt):,})", q2))

    # Utilization targets (70%, 60%, 50%)
    util = _pct_to_float(payload.get("revol_util"))
    if util is not None:
        for tgt in (70.0, 60.0, 50.0):
            if util > tgt:
                q = _copy(payload); q["revol_util"] = _fmt_pct(tgt)
                cands.append((f"Pay down credit cards to ~{tgt:.0f}% utilization", q))

    # DTI targets (35%, 30%, 25%)
    dti = _pct_to_float(payload.get("dti"))
    if dti is not None:
        for tgt in (35.0, 30.0, 25.0):
            if dti > tgt:
                q = _copy(payload); q["dti"] = _fmt_pct(tgt)
                # if we have income, estimate monthly cut (rough)
                ann = _to_float(payload.get("annual_inc"))
                if ann and ann > 0:
                    mi = ann/12.0
                    now = dti/100.0 * mi
                    new = tgt/100.0 * mi
                    est = max(0.0, now - new)
                    label = f"Lower DTI to ~{tgt:.0f}% (≈ ${est:.0f} less monthly debt payments)"
                else:
                    label = f"Lower DTI to ~{tgt:.0f}%"
                cands.append((label, q))

    # Deduplicate by label
    seen, out = set(), []
    for lab, qp in cands:
        if lab not in seen:
            seen.add(lab); out.append((lab, qp))

    # Keep it tight: at most ~12 candidates
    return out[:12]

# ---------- fast selection logic ----------
def recommend_improvements(payload: Dict, top_k: int = 3) -> Dict:
    """
    Fast version:
    - Evaluate a small, discrete set of candidates (<= 12)
    - Score with LRU-cached scorer
    - Return top_k by delta and a short greedy plan (<= 2 steps)
    """
    thr = _thr_review()
    current_pd = _get_pd(payload)

    cands = _concrete_candidates(payload)
    evaluated: List[Dict] = []
    for label, q in cands:
        new_pd = _get_pd(q)
        evaluated.append({
            "action": label,
            "new_pd": round(new_pd, 6),
            "delta_pd": round(current_pd - new_pd, 6),
            "payload": q
        })

    # rank by largest reduction, then lowest resulting PD
    evaluated.sort(key=lambda x: (-x["delta_pd"], x["new_pd"]))
    best_tips = evaluated[:max(1, top_k)]

    # Greedy plan (up to 2 steps) using the same discrete set, avoiding duplicate labels
    greedy: List[Dict] = []
    work_p = _copy(payload)
    work_pd = current_pd
    used_labels = set()
    for _ in range(2):
        step_best = None
        step_best_drop = 0.0
        for label, q in _concrete_candidates(work_p):
            if label in used_labels:  # avoid repeating the same action text
                continue
            npd = _get_pd(q)
            drop = work_pd - npd
            if drop > step_best_drop + 1e-9:
                step_best_drop = drop
                step_best = {
                    "action": label,
                    "new_pd": round(npd, 6),
                    "delta_pd": round(drop, 6),
                    "payload": q
                }
        if not step_best or step_best_drop <= 1e-6:
            break
        greedy.append(step_best)
        used_labels.add(step_best["action"])
        work_p = step_best["payload"]
        work_pd = step_best["new_pd"]
        if work_pd < thr:
            break

    return {
        "details": {"current_pd": round(current_pd, 6), "thr_review": thr},
        "best_tips": best_tips,
        "greedy_plan": greedy,
        "crosses_threshold": (len(greedy) > 0 and greedy[-1]["new_pd"] < thr),
    }

# ---------- Client message (LLM using concrete labels) ----------
def _client_name(payload: Dict) -> str:
    return (f"{(payload.get('first_name') or '').strip()} {(payload.get('last_name') or '').strip()}".strip() or "there")

def format_client_message_llm(payload: Dict, tips_obj: Dict, max_lines: int = 3) -> str:
    """
    LLM-rendered message from concrete actions (labels), without probabilities.
    If LLM unavailable, raise (since you want LLM-only).
    """
    if not (USE_LLM and _OPENAI_OK):
        raise RuntimeError("LLM client not available")

    # Prefer greedy plan (goal-directed), else best_tips
    steps = tips_obj.get("greedy_plan") or tips_obj.get("best_tips") or []
    labels = [s["action"] for s in steps[:max_lines]]
    if not labels:
        labels = ["Consider a smaller amount", "Shorten the term", "Pay down revolving balances"]

    sys = (
        "You are a lending specialist drafting a short message to an applicant.\n"
        "Constraints:\n"
        "- Professional, neutral, supportive tone.\n"
        "- 2–3 specific, actionable suggestions.\n"
        "- Do NOT mention probabilities, AI, risk scores, or internal thresholds.\n"
        "- Keep it under short.\n"
        "- Signed: Compliance Officer\n"
    )
    usr = (
        f"Applicant name: {_client_name(payload)}\n\n"
        "Use these concrete actions:\n" + "\n".join(f"- {a}" for a in labels) + "\n\n"
        "Write a brief message that:\n"
        "- Thanks the applicant\n"
        "- Lists the actions as bullets\n"
        "- Ends with an encouraging close"
    )

    client = OpenAI(timeout=LLM_TIMEOUT)
    '''resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.3,
    )'''
    #text = (resp.choices[0].message.content or "").strip()
    resp = client.responses.create(
            model=LLM_MODEL,
            instructions=sys,
            input=usr,
            temperature=0.2
        )
    text = resp.output_text
    if not text:
        raise RuntimeError("LLM returned empty client message")
    return text
