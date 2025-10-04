from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.deps import get_db
from backend.db import crud
from backend.db.schemas import ApplicationOut

router = APIRouter(tags=["applications"])

@router.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    rec = crud.get_application(db, app_id)
    if not rec:
        raise HTTPException(404, "Not found")
    return ApplicationOut(
        id=rec.id, created_at=rec.created_at,
        first_name=rec.first_name, last_name=rec.last_name,
        prob_default=rec.prob_default,
        system_decision=rec.system_decision, final_decision=rec.final_decision,
        policy_source=rec.policy_source, thresholds=rec.thresholds, status=rec.status
    )
