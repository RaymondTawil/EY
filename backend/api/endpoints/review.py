from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.db import crud
from backend.db.schemas import ApplicationOut, ReviewActionIn
from backend.services.improvement_tips import recommend_improvements, format_client_message_llm

router = APIRouter(tags=["review"])

@router.post("/applications/{app_id}/review", response_model=ApplicationOut)
def officer_decision(app_id: int, action: ReviewActionIn, db: Session = Depends(get_db)):
    rec = crud.get_application(db, app_id)
    if not rec:
        raise HTTPException(404, "Not found")
    if rec.system_decision != "REVIEW" or rec.status != "OPEN":
        raise HTTPException(400, "This application is not open for review")

    if action.action not in ("APPROVE", "REJECT"):
        raise HTTPException(422, "Action must be APPROVE or REJECT")

    # If officer REJECTS, create client message BEFORE closing
    client_msg = None
    if action.action == "REJECT":
        tips = recommend_improvements(rec.payload, top_k=3)
        client_msg = format_client_message_llm(rec.payload, tips, max_lines=3)

    # finalize (sets final_decision, status=CLOSED, review_notes, etc.)
    rec = crud.finalize_review(db, rec, action.action, action.notes)

    # persist client message if any
    if client_msg:
        rec.client_message = client_msg
        db.add(rec); db.commit(); db.refresh(rec)

    return ApplicationOut.model_validate(rec)

