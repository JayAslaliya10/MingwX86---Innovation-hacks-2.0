from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ─── User ─────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    health_card_number: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    auth0_id: str
    full_name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    health_card_number: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Health Card Mapping ───────────────────────────────────────────────────────

class HealthCardLookupOut(BaseModel):
    health_card_number: str
    payer_name: str
    policy_type: str
    policy_ids: List[UUID]


# ─── Policy ───────────────────────────────────────────────────────────────────

class PolicyOut(BaseModel):
    id: UUID
    title: Optional[str]
    drug_family: Optional[str]
    policy_type: Optional[str]
    effective_date: Optional[datetime]
    pdf_url: Optional[str]
    source: str
    payer: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Drug ─────────────────────────────────────────────────────────────────────

class DrugOut(BaseModel):
    id: UUID
    name: str
    brand_name: Optional[str]
    drug_family: Optional[str]
    hcpcs_code: Optional[str]
    rxnorm_id: Optional[str]

    class Config:
        from_attributes = True


# ─── Prior Auth ───────────────────────────────────────────────────────────────

class PriorAuthOut(BaseModel):
    drug_id: UUID
    policy_id: UUID
    required: bool
    criteria_text: Optional[str]
    evidence_snippets: Optional[List[str]]

    class Config:
        from_attributes = True


# ─── Extraction Result (internal use) ─────────────────────────────────────────

class DrugExtractionResult(BaseModel):
    drugs: List[str]
    hcpcs_codes: List[str]
    source: str  # "pdf" | "bulletin"


class PAExtractionResult(BaseModel):
    prior_auth_required: bool
    drugs_requiring_pa: List[str]
    evidence_snippets: List[str]


class PolicyDateResult(BaseModel):
    effective_date: Optional[str]
    policy_version: Optional[str]


class PolicyUpdateResult(BaseModel):
    has_update: bool
    old_hash: Optional[str]
    new_hash: Optional[str]
    diff_summary: Optional[str]
    effective_from: Optional[str]
    change_class: Optional[str]


# ─── Policy Update Notification ───────────────────────────────────────────────

class PolicyUpdateNotificationOut(BaseModel):
    id: UUID
    update_id: UUID
    policy_id: UUID
    policy_title: Optional[str]
    payer_name: Optional[str]
    diff_summary: Optional[str]
    change_class: Optional[str]
    effective_from: Optional[datetime]
    detected_at: datetime
    seen: bool

    class Config:
        from_attributes = True


# ─── Comparison ───────────────────────────────────────────────────────────────

class ComparisonRequest(BaseModel):
    drug_name: str
    payer_names: Optional[List[str]] = None  # None = compare all available


class ComparisonRow(BaseModel):
    field: str
    values: dict  # { payer_name: value }


class ComparisonTableOut(BaseModel):
    drug_name: str
    rows: List[ComparisonRow]
    generated_at: datetime


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
