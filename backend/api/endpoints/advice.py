import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.config import settings
from backend.db import crud
from openai import OpenAI

router = APIRouter(tags=["advice"])

def _get_llm_advice(payload: dict, prob_default: float, thresholds: dict) -> str:
    if not settings.OPENAI_API_KEY:
        return "LLM advice unavailable (no OPENAI_API_KEY). Suggested manual checks: verify income/employment, review high DTI/utilization, confirm purpose, and affordability."
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = f"""
You are a senior credit officer. Application is in manual review.
PD: {prob_default:.3f}
Policy thresholds: {json.dumps(thresholds)}

Application (JSON):
{json.dumps(payload, indent=2)}

Give a concise recommendation (<= 180 words): approve or reject, and 3–5 checks or mitigants.
"""
        resp = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions="You are a prudent, fair, concise credit risk advisor.",
            input=prompt,
            temperature=0.2
        )
        return resp.output_text #resp.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM advice error: {e}"

@router.post("/applications/{app_id}/advice")
def request_advice(app_id: int, db: Session = Depends(get_db)):
    rec = crud.get_application(db, app_id)
    if not rec:
        raise HTTPException(404, "Not found")
    if rec.system_decision != "REVIEW":
        raise HTTPException(400, "Advice only available for REVIEW cases")
    advice = _get_llm_advice(rec.payload, rec.prob_default, rec.thresholds or {})
    rec = crud.set_advice(db, rec, advice)
    return {"id": rec.id, "advice": advice}
