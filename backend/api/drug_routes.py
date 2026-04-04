from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.auth.auth0 import get_current_user
from backend.database.connection import get_db
from backend.database.models import User, Drug, DrugPolicyMap, Policy, Payer, PriorAuth
from backend.database.schemas import DrugOut, PriorAuthOut

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("/", response_model=list[DrugOut])
async def list_drugs(
    family: str | None = Query(None, description="Filter by drug family"),
    search: str | None = Query(None, description="Search by name or HCPCS code"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Drug)
    if family:
        q = q.filter(Drug.drug_family.ilike(f"%{family}%"))
    if search:
        q = q.filter(
            (Drug.name.ilike(f"%{search}%")) |
            (Drug.brand_name.ilike(f"%{search}%")) |
            (Drug.hcpcs_code.ilike(f"%{search}%"))
        )
    return q.all()


@router.get("/{drug_id}/coverage")
async def get_drug_coverage(
    drug_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Which plans cover this drug, and under what criteria."""
    mappings = db.query(DrugPolicyMap).filter(DrugPolicyMap.drug_id == drug_id).all()
    result = []
    for m in mappings:
        policy = db.query(Policy).filter(Policy.id == m.policy_id).first()
        payer = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
        pa = db.query(PriorAuth).filter(
            PriorAuth.drug_id == drug_id,
            PriorAuth.policy_id == m.policy_id,
        ).first()
        result.append({
            "payer": payer.name if payer else "Unknown",
            "policy_title": policy.title if policy else None,
            "policy_id": str(m.policy_id),
            "covered": m.covered,
            "covered_indications": m.covered_indications,
            "step_therapy_required": m.step_therapy_required,
            "step_therapy_details": m.step_therapy_details,
            "site_of_care": m.site_of_care,
            "prior_auth_required": pa.required if pa else None,
            "prior_auth_criteria": pa.criteria_text if pa else None,
        })
    return result


@router.get("/{drug_id}/prior-auth", response_model=list[PriorAuthOut])
async def get_prior_auth(
    drug_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(PriorAuth).filter(PriorAuth.drug_id == drug_id).all()


@router.get("/search/which-plans-cover")
async def which_plans_cover(
    drug_name: str = Query(..., description="Drug name to search"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer: Which health plans cover Drug X?"""
    drugs = db.query(Drug).filter(
        (Drug.name.ilike(f"%{drug_name}%")) | (Drug.brand_name.ilike(f"%{drug_name}%"))
    ).all()

    if not drugs:
        return {"drug": drug_name, "plans": [], "message": "Drug not found in knowledge base"}

    plans = []
    for drug in drugs:
        mappings = db.query(DrugPolicyMap).filter(
            DrugPolicyMap.drug_id == drug.id,
            DrugPolicyMap.covered == True,
        ).all()
        for m in mappings:
            policy = db.query(Policy).filter(Policy.id == m.policy_id).first()
            payer = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
            plans.append({
                "payer": payer.name if payer else "Unknown",
                "policy_title": policy.title if policy else None,
                "drug_name": drug.name,
                "brand_name": drug.brand_name,
                "hcpcs_code": drug.hcpcs_code,
            })

    return {"drug": drug_name, "plans": plans}
