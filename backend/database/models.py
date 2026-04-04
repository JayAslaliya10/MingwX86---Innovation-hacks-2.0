from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Text, DateTime, ForeignKey,
    Integer, Float, Enum, ARRAY, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid
import enum

from backend.database.connection import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class PolicySource(str, enum.Enum):
    system = "system"
    user_upload = "user_upload"


class PayerName(str, enum.Enum):
    uhc = "UnitedHealthcare"
    cigna = "Cigna"
    aetna = "Aetna"


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth0_id = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    health_card_number = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    uploaded_policies = relationship("Policy", back_populates="uploaded_by_user")
    policy_update_notifications = relationship("PolicyUpdateNotification", back_populates="user")


# ─── Health Card → Policy Mapping ─────────────────────────────────────────────

class HealthCardPolicyMap(Base):
    __tablename__ = "health_card_policy_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    health_card_number = Column(String, nullable=False, index=True)
    payer_name = Column(String, nullable=False)
    policy_type = Column(String, nullable=False)
    policy_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)


# ─── Payers ───────────────────────────────────────────────────────────────────

class Payer(Base):
    __tablename__ = "payers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    bulletin_url = Column(String, nullable=True)
    policy_index_url = Column(String, nullable=True)

    policies = relationship("Policy", back_populates="payer")


# ─── Policies ─────────────────────────────────────────────────────────────────

class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payer_id = Column(UUID(as_uuid=True), ForeignKey("payers.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=True)
    drug_family = Column(String, nullable=True)
    policy_type = Column(String, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    pdf_url = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)  # for change detection
    source = Column(String, default=PolicySource.system)
    is_drug_coverage_policy = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payer = relationship("Payer", back_populates="policies")
    uploaded_by_user = relationship("User", back_populates="uploaded_policies")
    drug_mappings = relationship("DrugPolicyMap", back_populates="policy")
    prior_auths = relationship("PriorAuth", back_populates="policy")
    updates = relationship("PolicyUpdate", back_populates="policy")
    embeddings = relationship("PolicyEmbedding", back_populates="policy")


# ─── Drugs ────────────────────────────────────────────────────────────────────

class Drug(Base):
    __tablename__ = "drugs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    brand_name = Column(String, nullable=True)
    drug_family = Column(String, nullable=True)
    hcpcs_code = Column(String, nullable=True, index=True)
    rxnorm_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("name", "hcpcs_code", name="uq_drug_name_hcpcs"),)

    policy_mappings = relationship("DrugPolicyMap", back_populates="drug")
    prior_auths = relationship("PriorAuth", back_populates="drug")


# ─── Drug ↔ Policy (Many-to-Many) ─────────────────────────────────────────────

class DrugPolicyMap(Base):
    __tablename__ = "drug_policy_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("drugs.id"), nullable=False)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    covered = Column(Boolean, default=True)
    covered_indications = Column(ARRAY(Text), nullable=True)
    step_therapy_required = Column(Boolean, default=False)
    step_therapy_details = Column(Text, nullable=True)
    site_of_care = Column(ARRAY(String), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("drug_id", "policy_id", name="uq_drug_policy"),)

    drug = relationship("Drug", back_populates="policy_mappings")
    policy = relationship("Policy", back_populates="drug_mappings")


# ─── Prior Authorization ───────────────────────────────────────────────────────

class PriorAuth(Base):
    __tablename__ = "prior_auth"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("drugs.id"), nullable=False)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    required = Column(Boolean, nullable=False)
    criteria_text = Column(Text, nullable=True)
    evidence_snippets = Column(ARRAY(Text), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    drug = relationship("Drug", back_populates="prior_auths")
    policy = relationship("Policy", back_populates="prior_auths")


# ─── Policy Updates (Change Detection) ────────────────────────────────────────

class PolicyUpdate(Base):
    __tablename__ = "policy_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    effective_from = Column(DateTime, nullable=True)
    old_hash = Column(String, nullable=True)
    new_hash = Column(String, nullable=True)
    old_text_snippet = Column(Text, nullable=True)
    new_text_snippet = Column(Text, nullable=True)
    diff_summary = Column(Text, nullable=True)
    change_class = Column(String, nullable=True)  # e.g. "coverage", "pa", "step_therapy"

    policy = relationship("Policy", back_populates="updates")
    notifications = relationship("PolicyUpdateNotification", back_populates="update")


# ─── Policy Update Notifications (per user) ───────────────────────────────────

class PolicyUpdateNotification(Base):
    __tablename__ = "policy_update_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    update_id = Column(UUID(as_uuid=True), ForeignKey("policy_updates.id"), nullable=False)
    seen = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="policy_update_notifications")
    update = relationship("PolicyUpdate", back_populates="notifications")


# ─── Policy Embeddings (pgvector) ─────────────────────────────────────────────

class PolicyEmbedding(Base):
    __tablename__ = "policy_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(768), nullable=True)  # Gemini text-embedding-004 = 768 dims
    source = Column(String, default=PolicySource.system)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy = relationship("Policy", back_populates="embeddings")


# ─── Policy Comparisons ───────────────────────────────────────────────────────

class PolicyComparison(Base):
    __tablename__ = "policy_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("drugs.id"), nullable=False)
    policy_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    comparison_table = Column(JSONB, nullable=True)  # structured comparison output
    generated_at = Column(DateTime, default=datetime.utcnow)
