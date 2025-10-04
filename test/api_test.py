# run_api_tests.py
# -*- coding: utf-8 -*-
import os
import json
import traceback
import requests
from typing import Any, Dict

API = os.getenv("API_URL", "http://localhost:8000")
VER = "/v1"
BASE = f"{API}{VER}"
JSON_HEADERS = {"Content-Type": "application/json"}


def pretty(title: str, obj: Any):
    print(f"\n=== {title} ===")
    try:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except Exception:
        print(obj)


def post(path: str, payload: Dict, title: str, expect_ok: bool = True) -> Dict:
    url = f"{BASE}{path}"
    try:
        r = requests.post(url, headers=JSON_HEADERS, json=payload, timeout=45)
        if expect_ok and not r.ok:
            pretty(f"{title} (HTTP {r.status_code})", r.text)
            r.raise_for_status()
        try:
            data = r.json()
        except Exception:
            data = {"raw_text": r.text}
        pretty(title, data)
        return data
    except Exception as e:
        pretty(f"{title} ERROR", f"{e}\n{traceback.format_exc()}")
        return {}


def get(path: str, title: str, expect_ok: bool = True) -> Dict:
    url = f"{BASE}{path}"
    try:
        r = requests.get(url, timeout=30)
        if expect_ok and not r.ok:
            pretty(f"{title} (HTTP {r.status_code})", r.text)
            r.raise_for_status()
        try:
            data = r.json()
        except Exception:
            data = {"raw_text": r.text}
        pretty(title, data)
        return data
    except Exception as e:
        pretty(f"{title} ERROR", f"{e}\n{traceback.format_exc()}")
        return {}


def main():
    print(f"Target API: {BASE}")

    # ---------- 1) Score three applications (APPROVE / REVIEW / REJECT) ----------
    approve_payload = {
        "first_name": "Jamie",
        "last_name":  "Banks",
        "loan_amnt": 8000,
        "int_rate": "7.5%",
        "fico_range_low": 780, "fico_range_high": 784,
        "annual_inc": 120000,
        "dti": "6%",
        "revol_util": "5%",
        "emp_length": "10+ years",
        "term": "36 months",
        "grade": "A", "sub_grade": "A1",
        "home_ownership": "MORTGAGE",
        "verification_status": "Not Verified",
        "purpose": "credit_card"
    }
    review_payload = {
        "first_name": "Alex",
        "last_name":  "Carver",
        "loan_amnt": 150000,
        "int_rate": "20.8%",
        "fico_range_low": 690, "fico_range_high": 694,
        "annual_inc": 55000,
        "dti": 12.0,
        "revol_util": "55%",
        "emp_length": "3 years",
        "term": "60 months",
        "grade": "E", "sub_grade": "E3",
        "home_ownership": "RENT",
        "verification_status": "Source Verified",
        "purpose": "debt_consolidation"
    }
    reject_payload = {
        "first_name": "Chris",
        "last_name":  "Nolan",
        "loan_amnt": 35000,
        "int_rate": "26.5%",
        "fico_range_low": 660, "fico_range_high": 664,
        "annual_inc": 30000,
        "dti": "39%",
        "revol_util": "97%",
        "emp_length": "< 1 year",
        "term": "60 months",
        "grade": "G", "sub_grade": "G4",
        "home_ownership": "RENT",
        "verification_status": "Verified",
        "purpose": "small_business"
    }

    approve = post("/score", approve_payload, "Score APPROVE candidate")
    review  = post("/score", review_payload,  "Score REVIEW candidate")
    reject  = post("/score", reject_payload,  "Score REJECT candidate (auto)")

    approve_id = approve.get("id")
    review_id  = review.get("id")
    reject_id  = reject.get("id")

    # ---------- 2) Fetch each record ----------
    if approve_id:
        get(f"/applications/{approve_id}", "Fetch APPROVE record")
    if review_id:
        get(f"/applications/{review_id}", "Fetch REVIEW record")
    if reject_id:
        auto = get(f"/applications/{reject_id}", "Fetch REJECT record (auto)")
        # If your /score attaches client_message for auto-rejects, you should see it here:
        if not auto.get("client_message"):
            pretty("NOTE", "Auto-reject has no client_message; check /score implementation if expected.")

    # ---------- 3) Officer ADVICE for REVIEW case ----------
    if review_id:
        if review.get("system_decision") == "REVIEW" and review.get("status") == "OPEN":
            post(f"/applications/{review_id}/advice", {}, "Get LLM officer advice (REVIEW case)")
        else:
            pretty("Get LLM advice (skipped)", "Case is not in REVIEW or not OPEN")

    # ---------- 4) Officer decision for REVIEW case (reject to generate client_message) ----------
    if review_id and review.get("system_decision") == "REVIEW" and review.get("status") == "OPEN":
        # Reject path should attach client_message (LLM-based)
        rej = post(
            f"/applications/{review_id}/review",
            {"action": "REJECT", "notes": "Affordability concerns at current term/amount."},
            "Officer REJECT (generate client message)")
        if not rej.get("client_message"):
            pretty("WARNING", "Officer REJECT returned no client_message — check review endpoint.")
        # Fetch back to confirm persisted
        get(f"/applications/{review_id}", "Fetch REVIEW->REJECT record (should be CLOSED with client_message)")

    # ---------- 5) Negative-path tests ----------
    # 5a) Ask advice on non-REVIEW (approve or reject case) -> expect 400
    if approve_id:
        post(f"/applications/{approve_id}/advice", {}, "Advice on non-REVIEW (should 400)", expect_ok=False)
    if reject_id:
        post(f"/applications/{reject_id}/advice", {}, "Advice on REJECT/CLOSED (should 400)", expect_ok=False)

    # 5b) Officer decision on non-REVIEW case -> expect 400
    if approve_id:
        post(f"/applications/{approve_id}/review", {"action":"APPROVE"}, "Officer decision on non-REVIEW (should 400)", expect_ok=False)

    # 5c) Fetch non-existent record -> expect 404
    get("/applications/99999999", "Fetch non-existent (should 404)", expect_ok=False)

    print("\nAll tests finished.\n")


if __name__ == "__main__":
    main()
