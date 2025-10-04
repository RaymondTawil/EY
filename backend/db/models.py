from sqlalchemy import Column, Integer, Float, String, Text, DateTime
from sqlalchemy.dialects.sqlite import JSON as SAJSON
import datetime as dt
from backend.db.session import Base

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    # NEW: applicant identity
    first_name = Column(String(80), nullable=True, index=True)
    last_name  = Column(String(80), nullable=True, index=True)

    payload = Column(SAJSON, nullable=False)
    prob_default = Column(Float, nullable=False)
    system_decision = Column(String(16), nullable=False)  # APPROVE/REVIEW/REJECT
    final_decision = Column(String(16), nullable=True)    # officer decision for REVIEW
    policy_source = Column(String(64), nullable=True)
    thresholds = Column(SAJSON, nullable=True)

    review_notes = Column(Text, nullable=True)            # officer notes
    advice = Column(Text, nullable=True)                  # LLM suggestion
    status = Column(String(16), default="OPEN", nullable=False)  # OPEN/CLOSED

    client_message = Column(Text, nullable=True)   # client-facing "what to improve" message

