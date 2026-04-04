from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.auth0 import get_current_user
from backend.database.connection import get_db
from backend.database.models import User, Drug, PolicyComparison
from backend.database.schemas import ComparisonRequest, ComparisonTableOut

router = APIRouter(prefix="/compare", tags=["comparison"])


@router.post("/", response_model=ComparisonTableOut)
async def compare_drug_policies(
    body: ComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compare all policies covering a given drug across payers.
    Returns a structured table.
    """
    drugs = db.query(Drug).filter(
        (Drug.name.ilike(f"%{body.drug_name}%")) |
        (Drug.brand_name.ilike(f"%{body.drug_name}%"))
    ).all()

    if not drugs:
        raise HTTPException(status_code=404, detail=f"Drug '{body.drug_name}' not found")

    drug = drugs[0]

    # Check if comparison already cached
    cached = db.query(PolicyComparison).filter(
        PolicyComparison.drug_id == drug.id
    ).order_by(PolicyComparison.generated_at.desc()).first()

    if cached and cached.comparison_table:
        from datetime import datetime
        return ComparisonTableOut(
            drug_name=body.drug_name,
            rows=cached.comparison_table.get("rows", []),
            generated_at=cached.generated_at,
        )

    # Generate fresh comparison
    from backend.comparison.policy_comparator import compare_policies_for_drug
    result = await compare_policies_for_drug(drug, body.payer_names, db)
    return result


@router.get("/{drug_name}")
async def get_cached_comparison(
    drug_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    drugs = db.query(Drug).filter(
        (Drug.name.ilike(f"%{drug_name}%")) |
        (Drug.brand_name.ilike(f"%{drug_name}%"))
    ).all()
    if not drugs:
        raise HTTPException(status_code=404, detail="Drug not found")

    drug = drugs[0]
    cached = db.query(PolicyComparison).filter(
        PolicyComparison.drug_id == drug.id
    ).order_by(PolicyComparison.generated_at.desc()).first()

    if not cached:
        raise HTTPException(status_code=404, detail="No comparison available. POST to /compare/ to generate.")

    return cached.comparison_table
