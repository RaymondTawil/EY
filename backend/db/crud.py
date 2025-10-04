from sqlalchemy.orm import Session
from backend.db.models import Application

def create_application(db: Session, **kwargs) -> Application:
    rec = Application(**kwargs)
    db.add(rec); db.commit(); db.refresh(rec)
    return rec

def get_application(db: Session, app_id: int) -> Application | None:
    return db.get(Application, app_id)

def set_advice(db: Session, rec: Application, advice: str) -> Application:
    rec.advice = advice
    db.add(rec); db.commit(); db.refresh(rec)
    return rec

def finalize_review(db: Session, rec: Application, action: str, notes: str | None) -> Application:
    rec.final_decision = action
    if notes:
        import datetime as dt
        stamp = f"[{dt.datetime.utcnow().isoformat()}] {notes}"
        rec.review_notes = (rec.review_notes + "\n" if rec.review_notes else "") + stamp
    rec.status = "CLOSED"
    db.add(rec); db.commit(); db.refresh(rec)
    return rec
