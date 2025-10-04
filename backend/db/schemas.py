import datetime as dt
from typing import Optional, Literal, Dict
from pydantic import BaseModel, ConfigDict, validator
class ApplicationIn(BaseModel):
    # NEW
    first_name: Optional[str] = None
    last_name:  Optional[str] = None

    # existing
    loan_amnt: float
    int_rate: str | float
    fico_range_low: float
    fico_range_high: float
    annual_inc: float
    dti: float | str
    revol_util: float | str
    emp_length: str
    term: str
    grade: str
    sub_grade: str
    home_ownership: str
    verification_status: str
    purpose: str

    @validator("int_rate", "dti", "revol_util", pre=True)
    def accept_percent_or_float(cls, v):
        return v


class ApplicationOut(BaseModel):
    id: int
    created_at: dt.datetime
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    prob_default: float
    system_decision: Literal["APPROVE","REVIEW","REJECT"]
    final_decision: Optional[Literal["APPROVE","REJECT"]] = None
    policy_source: Optional[str] = None
    thresholds: Dict[str, Optional[float]]
    status: Literal["OPEN","CLOSED"]

    # optional extras you might already have:
    advice: Optional[str] = None
    advice_source: Optional[str] = None
    review_notes: Optional[str] = None
    client_message: Optional[str] = None

    # NEW: enable attribute-based validation (ORM)
    model_config = ConfigDict(from_attributes=True)

class ReviewActionIn(BaseModel):
    action: Literal["APPROVE","REJECT"]
    notes: Optional[str] = None
