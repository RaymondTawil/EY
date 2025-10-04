from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.db import crud
from backend.db.schemas import ApplicationIn, ApplicationOut
from backend.services.improvement_tips import recommend_improvements, format_client_message_llm
from backend.services.policy_core import score_payload

router = APIRouter(tags=["scoring"])

@router.post("/score", response_model=ApplicationOut)
def score_and_store(app_in: ApplicationIn, db: Session = Depends(get_db)):
    payload = app_in.dict()
    scored = score_payload(payload)

    system_decision = scored["decision"]          # APPROVE / REVIEW / REJECT (model)
    final_decision = system_decision if system_decision != "REVIEW" else None
    status = "CLOSED" if final_decision in ("APPROVE","REJECT") else "OPEN"

    client_message = None
    # If model auto-rejects, generate LLM client message *here*
    if system_decision == "REJECT":
        tips = recommend_improvements(payload, top_k=3)
        client_message = format_client_message_llm(payload, tips, max_lines=3)

    rec = crud.create_application(
        db,
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
        payload=payload,
        prob_default=scored["prob_default"],
        system_decision=system_decision,
        final_decision=final_decision,
        policy_source=scored.get("policy_source"),
        thresholds=scored.get("thresholds"),
        status=status,
        client_message=client_message
    )
    return ApplicationOut.model_validate(rec)

