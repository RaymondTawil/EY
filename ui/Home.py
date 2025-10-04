# -*- coding: utf-8 -*-
import os
import json
import requests
import streamlit as st
from pathlib import Path

API_URL = os.getenv("API_URL", "http://api:8000")
VER = "/v1"
BASE = f"{API_URL}{VER}"
JSON = {"Content-Type": "application/json"}

st.set_page_config(page_title="AI Credit Risk – UI", layout="centered")

# ---------------------------
# Small UI helpers
# ---------------------------
def show_logo_local(rel_path: str = "data/ey.jpg", width: int = 96):
    here = Path(__file__).parent
    logo_path = (here / rel_path).resolve()
    if logo_path.exists():
        st.image(str(logo_path), width=width)
    else:
        st.warning(f"Logo not found at {logo_path}")

def decision_badge(text: str):
    color = {"APPROVE": "#16a34a", "REVIEW": "#f59e0b", "REJECT": "#dc2626", "—": "#6b7280"}.get(text, "#6b7280")
    st.markdown(
        f"""
        <span style="
            display:inline-block;
            padding:4px 10px;
            border-radius:999px;
            background:{color}20;
            color:{color};
            font-weight:600;
            font-size:0.9rem;">
            {text}
        </span>
        """,
        unsafe_allow_html=True
    )

def section_header(txt: str):
    st.markdown(f"### {txt}")

# ---------------------------
# HTTP helpers
# ---------------------------
def post(path: str, payload: dict, timeout=45):
    try:
        r = requests.post(f"{BASE}{path}", headers=JSON, json=payload, timeout=timeout)
        if r.ok:
            return r.json(), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)

def get(path: str, timeout=30):
    try:
        r = requests.get(f"{BASE}{path}", timeout=timeout)
        if r.ok:
            return r.json(), None
        return None, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)

# ---------------------------
# Header with logo + title
# ---------------------------
logo_col, title_col = st.columns([1, 3])
with logo_col:
    # Adjust path if needed (relative to this file)
    show_logo_local("data/ey.jpg", width=96)
with title_col:
    st.title("AI Credit Risk – MVP UI")

# ---------------------------
# Presets
# ---------------------------
def preset_payload(kind: str) -> dict:
    base = {
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
    if kind == "APPROVE":
        base.update({
            "first_name":"Jamie","last_name":"Banks",
            "loan_amnt": 8000, "int_rate":"7.5%", "term":"36 months",
            "fico_range_low":780, "fico_range_high":784,
            "annual_inc": 120000, "dti":"6%", "revol_util":"5%",
            "grade":"A","sub_grade":"A1","home_ownership":"MORTGAGE",
            "verification_status":"Not Verified","purpose":"credit_card"
        })
    elif kind == "REJECT":
        base.update({
            "first_name":"Chris","last_name":"Nolan",
            "loan_amnt": 35000, "int_rate":"26.5%", "term":"60 months",
            "fico_range_low":660, "fico_range_high":664,
            "annual_inc": 30000, "dti":"39%", "revol_util":"97%",
            "grade":"G","sub_grade":"G4","home_ownership":"RENT",
            "verification_status":"Verified","purpose":"small_business"
        })
    return base

st.sidebar.header("Presets")
preset = st.sidebar.selectbox("Quick payload", ["None", "APPROVE", "REVIEW", "REJECT"], index=0)
if st.sidebar.button("Load preset") and preset != "None":
    st.session_state["payload"] = preset_payload(preset)

# ---------------------------
# Auto-load advice when a case is REVIEW & OPEN
# ---------------------------
def ensure_advice_loaded(view: dict):
    """If the application is in REVIEW/OPEN and no advice is present, call the advice endpoint once."""
    if not view or not isinstance(view.get("id"), int):
        return
    if not (view.get("system_decision") == "REVIEW" and view.get("status") == "OPEN"):
        return
    already = st.session_state.get("advice_loaded_for_id")
    if already == view["id"]:
        return
    if view.get("advice"):
        st.session_state["advice_loaded_for_id"] = view["id"]
        return
    adv_resp, err = post(f"/applications/{view['id']}/advice", {})
    if not err and adv_resp and adv_resp.get("advice"):
        view["advice"] = adv_resp["advice"]
        st.session_state["last_result"] = view
        st.session_state["advice_loaded_for_id"] = view["id"]
        
def ensure_advice_loaded(view: dict):
    """
    If the application is in REVIEW/OPEN and advice is missing, call the advice endpoint ONCE.
    Stores the result back into st.session_state['last_result'] so the panel shows it.
    """
    if not view or not isinstance(view.get("id"), int):
        return
    if not (view.get("system_decision") == "REVIEW" and view.get("status") == "OPEN"):
        return

    # Don't re-call for the same case id
    if st.session_state.get("advice_loaded_for_id") == view["id"]:
        return

    # Already present? mark as loaded and skip
    if view.get("advice"):
        st.session_state["advice_loaded_for_id"] = view["id"]
        return

    adv_resp, err = post(f"/applications/{view['id']}/advice", {})
    if err:
        # Silent fail: keep UI working even if LLM/fallback is down
        return
    if adv_resp and adv_resp.get("advice"):
        view["advice"] = adv_resp["advice"]
        view["advice_source"] = adv_resp.get("source")  # if your API returns it
        st.session_state["last_result"] = view
        st.session_state["advice_loaded_for_id"] = view["id"]

# ---------------------------
# Submit Application
# ---------------------------
section_header("Submit Application")
payload = st.session_state.get("payload", preset_payload("REVIEW"))

with st.form("app_form"):
    # Applicant
    st.subheader("Applicant")
    n1, n2 = st.columns(2)
    with n1:
        first_name = st.text_input("First Name", value=payload.get("first_name",""))
    with n2:
        last_name  = st.text_input("Last Name", value=payload.get("last_name",""))

    # Details
    st.subheader("Loan details")
    col1, col2 = st.columns(2)
    with col1:
        loan_amnt = st.number_input("Loan Amount", min_value=500.0, value=float(payload["loan_amnt"]), step=500.0)
        int_rate   = st.text_input("Interest Rate", value=str(payload["int_rate"]))
        term       = st.selectbox("Term", ["36 months","60 months"], index=(0 if "36" in payload["term"] else 1))
        annual_inc = st.number_input("Annual Income", min_value=0.0, value=float(payload["annual_inc"]), step=1000.0)
        dti        = st.text_input("DTI", value=str(payload["dti"]))
        revol_util = st.text_input("Revolving Util", value=str(payload["revol_util"]))
        emp_length = st.selectbox(
            "Employment Length",
            ["< 1 year","1 year","2 years","3 years","4 years","5 years","6 years","7 years","8 years","9 years","10+ years"],
            index=(10 if payload["emp_length"]=="10+ years" else 3)
        )
    with col2:
        fico_low  = st.number_input("FICO Low", min_value=300, max_value=900, value=int(payload["fico_range_low"]), step=1)
        fico_high = st.number_input("FICO High", min_value=300, max_value=900, value=int(payload["fico_range_high"]), step=1)
        grade     = st.selectbox("Grade", list("ABCDEFG"), index=list("ABCDEFG").index(payload["grade"]))
        sub_grade = st.text_input("Sub-Grade", value=str(payload["sub_grade"]))
        home_own  = st.selectbox("Home Ownership", ["MORTGAGE","RENT","OWN","OTHER"], index=["MORTGAGE","RENT","OWN","OTHER"].index(payload["home_ownership"]))
        verif     = st.selectbox("Verification Status", ["Not Verified","Source Verified","Verified"],
                                 index=["Not Verified","Source Verified","Verified"].index(payload["verification_status"]))
        purpose   = st.selectbox("Purpose", [
            "debt_consolidation","credit_card","other","home_improvement","major_purchase",
            "medical","car","small_business","vacation","house","moving","renewable_energy"
        ], index=[
            "debt_consolidation","credit_card","other","home_improvement","major_purchase",
            "medical","car","small_business","vacation","house","moving","renewable_energy"
        ].index(payload["purpose"]))

    submitted = st.form_submit_button("Score Application")

if submitted:
    req = {
        "first_name": first_name,
        "last_name":  last_name,
        "loan_amnt": loan_amnt,
        "int_rate": int_rate,
        "fico_range_low": fico_low,
        "fico_range_high": fico_high,
        "annual_inc": annual_inc,
        "dti": dti,
        "revol_util": revol_util,
        "emp_length": emp_length,
        "term": term,
        "grade": grade,
        "sub_grade": sub_grade,
        "home_ownership": home_own,
        "verification_status": verif,
        "purpose": purpose,
    }
    res, err = post("/score", req)
    if err:
        st.error(err)
    else:
        st.success(f"Scored application #{res['id']}")
        st.session_state["last_result"] = res
        # Auto-advice if this landed in REVIEW
        ensure_advice_loaded(st.session_state["last_result"])

# ---------------------------
# Lookup panel (updates Latest Result)
# ---------------------------
st.divider()
section_header("Lookup an Existing Application")

res_now = st.session_state.get("last_result")
if "lookup_id" not in st.session_state:
    st.session_state["lookup_id"] = int(res_now["id"]) if res_now and isinstance(res_now.get("id"), int) else 1

ctrlM, fetch_col = st.columns([0.8, 0.2])
with ctrlM:
    st.session_state["lookup_id"] = st.number_input(
        "Application ID",
        min_value=1,
        step=1,
        value=st.session_state["lookup_id"],
        label_visibility="collapsed"
    )
with fetch_col:
    if st.button("Fetch"):
        data, err = get(f"/applications/{st.session_state['lookup_id']}")
        if err:
            st.error(err)
        else:
            st.session_state["last_result"] = data
            st.success(f"Loaded #{st.session_state['lookup_id']} into Latest Result above")
            ensure_advice_loaded(st.session_state["last_result"])

# ---------------------------
# Latest Result (always visible)
# ---------------------------
section_header("Latest Result")

res = st.session_state.get("last_result")
placeholder = {
    "id": "—",
    "first_name": "—",
    "last_name": "—",
    "system_decision": "—",
    "final_decision": None,
    "prob_default": 0.0,
    "status": "—",
    "thresholds": {},
}
view = (res or placeholder)

# Auto-fetch advice if this is a live REVIEW/OPEN case (covers refresh)
if res:
    ensure_advice_loaded(view)


# Header with client + ID + badge
top = st.container()
with top:
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    with c1:
        full_name = f"{(view.get('first_name') or '—').strip()} {(view.get('last_name') or '').strip()}".strip()
        st.markdown(f"#### {full_name}")
        st.caption(f"Application ID: **{view.get('id','—')}**")
    with c2:
        st.write("**System Decision**")
        decision_badge(view.get("system_decision", "—"))

st.divider()

# Metrics + thresholds
m1, m2, m3 = st.columns([1, 1, 1.4])
with m1:
    pd_val = view.get("prob_default")
    st.metric("Probability of Default", f"{pd_val:.3f}" if res else "—")
with m2:
    st.metric("Final Decision", view.get("final_decision") or "—")
    st.caption(f"Status: **{view.get('status','—')}**")
with m3:
    st.caption("Thresholds used")
    thr = view.get("thresholds") or {}
    st.code(json.dumps(thr if res else {"thr_reject": "—", "thr_review": "—"}, indent=2))

# Advice / Notes (auto-populated via ensure_advice_loaded)
adv = view.get("advice")
notes = view.get("review_notes")
if adv or notes:
    st.divider()
    info_col = st.columns(1)[0]
    if adv:
        with info_col:
            st.markdown("**LLM Advice**")
            st.info(adv)

# Manual review controls (only when REVIEW is open)
if res and view["system_decision"] == "REVIEW" and view.get("status") == "OPEN":
    st.divider()
    section_header("Manual Review (Officer)")

    notes_input = st.text_area(
        "Officer Notes (optional)",
        value="",
        height=120,
        placeholder="Evidence reviewed, mitigants, rationale, etc."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Approve"):
            upd, err = post(f"/applications/{view['id']}/review", {"action": "APPROVE", "notes": notes_input})
            if err:
                st.error(err)
            else:
                st.success("Final decision recorded: APPROVE")
                st.session_state["last_result"] = upd
    with c2:
        if st.button("Reject"):
            upd, err = post(f"/applications/{view['id']}/review", {"action": "REJECT", "notes": notes_input})
            if err:
                st.error(err)
            else:
                st.success("Final decision recorded: REJECT")
                st.session_state["last_result"] = upd

                # immediate inline display if present
                if upd.get("client_message"):
                    st.subheader("Client Guidance")
                    st.write(upd["client_message"])

                st.rerun()   # still rerun so the main “Latest Result” panel updates


# Client-facing guidance when rejected (model auto-reject or officer reject)
is_rejected = (
    (res and view.get("final_decision") == "REJECT") or
    (res and view.get("system_decision") == "REJECT" and view.get("status") == "CLOSED")
)
if is_rejected and view.get("client_message"):
    st.divider()
    st.subheader("Client Guidance")
    st.write(view["client_message"])
    st.download_button(
        label="Download client message",
        data=view["client_message"],
        file_name=f"client_guidance_application_{view.get('id','')}.txt",
        mime="text/plain",
        use_container_width=True
    )

# Footer
st.divider()
