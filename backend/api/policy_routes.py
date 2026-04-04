import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from backend.auth.auth0 import get_current_user
from backend.database.connection import get_db
from backend.database.models import User, Policy, Payer
from backend.database.schemas import PolicyOut

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("/upload", response_model=list[PolicyOut])
async def upload_policies(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload one or more policy PDFs. Only available for users without a health card number."""
    if current_user.health_card_number:
        raise HTTPException(
            status_code=403,
            detail="Upload is only available for users without a health card number.",
        )

    created_policies = []
    for upload in files:
        if not upload.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{upload.filename} is not a PDF")

        content = await upload.read()

        # Save temp file for LlamaParse
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Create policy record (title/details filled after async extraction)
        policy = Policy(
            payer_id=None,      # determined during extraction
            uploaded_by=current_user.id,
            title=upload.filename,
            source="user_upload",
            raw_text=None,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        # Run full extraction pipeline in background
        background_tasks.add_task(
            _run_extraction_pipeline,
            policy_id=str(policy.id),
            pdf_path=tmp_path,
            db=db,
        )
        created_policies.append(policy)

    return created_policies


@router.get("/", response_model=list[PolicyOut])
async def list_my_policies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.health_card_number:
        from backend.database.models import HealthCardPolicyMap
        mapping = db.query(HealthCardPolicyMap).filter(
            HealthCardPolicyMap.health_card_number == current_user.health_card_number
        ).first()
        if not mapping:
            return []
        policies = db.query(Policy).filter(Policy.id.in_(mapping.policy_ids)).all()
    else:
        policies = db.query(Policy).filter(Policy.uploaded_by == current_user.id).all()

    result = []
    for p in policies:
        payer = db.query(Payer).filter(Payer.id == p.payer_id).first()
        out = PolicyOut(
            id=p.id,
            title=p.title,
            drug_family=p.drug_family,
            policy_type=p.policy_type,
            effective_date=p.effective_date,
            pdf_url=p.pdf_url,
            source=p.source,
            payer=payer.name if payer else None,
            created_at=p.created_at,
        )
        result.append(out)
    return result


@router.get("/{policy_id}", response_model=PolicyOut)
async def get_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    payer = db.query(Payer).filter(Payer.id == policy.payer_id).first()
    return PolicyOut(
        id=policy.id,
        title=policy.title,
        drug_family=policy.drug_family,
        policy_type=policy.policy_type,
        effective_date=policy.effective_date,
        pdf_url=policy.pdf_url,
        source=policy.source,
        payer=payer.name if payer else None,
        created_at=policy.created_at,
    )


async def _run_extraction_pipeline(policy_id: str, pdf_path: str, db: Session):
    """Full extraction: parse → drugs → PA → date → update check → index."""
    try:
        from backend.ingestion.parser import parse_pdf
        from backend.ingestion.drug_extractor import extract_drugs
        from backend.ingestion.pa_detector import detect_prior_auth
        from backend.ingestion.normalizer import normalize_drugs
        from backend.rag.indexer import index_policy

        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            return

        # 1. Parse PDF
        parsed = await parse_pdf(pdf_path)
        policy.raw_text = parsed.text
        db.commit()

        # 2. Determine payer from text
        payer = _detect_payer(parsed.text, db)
        if payer:
            policy.payer_id = payer.id

        # 3. Extract drugs (Case A or B)
        drug_result = await extract_drugs(parsed, policy, db)

        # 4. PA detection
        pa_result = await detect_prior_auth(parsed.text, drug_result.drugs)

        # 5. Normalize drugs and store
        await normalize_drugs(drug_result, pa_result, policy, db)

        # 6. Index into vector store
        await index_policy(policy, parsed.text, db)

        # 7. Check for updates
        from backend.scraping.change_detector import check_policy_for_updates
        await check_policy_for_updates(policy, db)

        import os
        os.unlink(pdf_path)
    except Exception as e:
        print(f"[extraction_pipeline] Error for policy {policy_id}: {e}")


def _detect_payer(text: str, db: Session) -> Payer | None:
    text_lower = text.lower()
    payers = db.query(Payer).all()
    for payer in payers:
        if payer.name.lower() in text_lower:
            return payer
    return None
