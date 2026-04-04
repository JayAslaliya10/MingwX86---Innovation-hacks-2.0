"""
Drug normalization using RxNorm API and storing results to database.
"""
import re
import httpx
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.models import Drug, DrugPolicyMap, PriorAuth, Policy
from backend.database.schemas import DrugExtractionResult, PAExtractionResult

settings = get_settings()

# TNF Inhibitor HCPCS reference (offline fallback)
HCPCS_TO_RXNORM = {
    "J0129": "151",      # abatacept
    "J0135": "327361",   # adalimumab
    "J0717": "358431",   # certolizumab
    "J1438": "214555",   # etanercept
    "J1602": "475230",   # golimumab
    "J1745": "121191",   # infliximab
    "J3262": "542831",   # tocilizumab
}


async def lookup_rxnorm_by_name(drug_name: str) -> dict | None:
    """Look up drug in RxNorm by name. Returns {rxnorm_id, name} or None."""
    try:
        url = f"{settings.rxnorm_api_base}/rxcui.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"name": drug_name, "search": 2})
            resp.raise_for_status()
            data = resp.json()
            rxcui = data.get("idGroup", {}).get("rxnormId", [])
            if rxcui:
                return {"rxnorm_id": rxcui[0], "name": drug_name}
    except Exception as e:
        print(f"[normalizer] RxNorm lookup failed for {drug_name}: {e}")
    return None


async def lookup_rxnorm_by_hcpcs(hcpcs_code: str) -> str | None:
    """Look up drug name by HCPCS code. Uses offline table first, then RxNorm."""
    if hcpcs_code in HCPCS_TO_RXNORM:
        rxnorm_id = HCPCS_TO_RXNORM[hcpcs_code]
        try:
            url = f"{settings.rxnorm_api_base}/rxcui/{rxnorm_id}/properties.json"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return data.get("properties", {}).get("name")
        except Exception:
            pass
    return None


async def normalize_drugs(
    drug_result: DrugExtractionResult,
    pa_result: PAExtractionResult,
    policy: Policy,
    db: Session,
) -> list[Drug]:
    """
    Normalize extracted drug names via RxNorm, store in DB,
    create drug→policy mappings and PA records.
    """
    stored_drugs = []

    for drug_name in drug_result.drugs:
        if not drug_name or len(drug_name) < 2:
            continue

        drug_name_clean = drug_name.strip().lower()

        # Check if drug already exists in DB
        existing = db.query(Drug).filter(
            Drug.name.ilike(drug_name_clean)
        ).first()

        if existing:
            drug = existing
        else:
            # Look up in RxNorm
            rxnorm_info = await lookup_rxnorm_by_name(drug_name_clean)
            rxnorm_id = rxnorm_info["rxnorm_id"] if rxnorm_info else None

            # Find HCPCS code from our extraction
            hcpcs_code = _find_hcpcs_for_drug(drug_name_clean, drug_result.hcpcs_codes)

            drug = Drug(
                name=drug_name_clean,
                brand_name=_find_brand_name(drug_name_clean),
                drug_family="TNF Inhibitors / Biologics",
                hcpcs_code=hcpcs_code,
                rxnorm_id=rxnorm_id,
            )
            db.add(drug)
            db.flush()

        # Create drug → policy mapping (avoid duplicates)
        existing_map = db.query(DrugPolicyMap).filter(
            DrugPolicyMap.drug_id == drug.id,
            DrugPolicyMap.policy_id == policy.id,
        ).first()

        if not existing_map:
            mapping = DrugPolicyMap(
                drug_id=drug.id,
                policy_id=policy.id,
                covered=True,
            )
            db.add(mapping)

        # Create PA record if this drug requires PA
        pa_required = (
            pa_result.prior_auth_required and
            (
                drug_name_clean in [d.lower() for d in pa_result.drugs_requiring_pa] or
                not pa_result.drugs_requiring_pa  # if list is empty but PA required, flag all
            )
        )

        existing_pa = db.query(PriorAuth).filter(
            PriorAuth.drug_id == drug.id,
            PriorAuth.policy_id == policy.id,
        ).first()

        if not existing_pa:
            pa = PriorAuth(
                drug_id=drug.id,
                policy_id=policy.id,
                required=pa_required,
                evidence_snippets=pa_result.evidence_snippets,
            )
            db.add(pa)

        stored_drugs.append(drug)

    db.commit()
    return stored_drugs


def _find_hcpcs_for_drug(drug_name: str, hcpcs_codes: list[str]) -> str | None:
    """Match drug name to HCPCS code using our reference table."""
    from backend.ingestion.drug_extractor import TNF_INHIBITOR_DRUGS
    for code, info in TNF_INHIBITOR_DRUGS.items():
        if info["name"].lower() in drug_name or drug_name in info["name"].lower():
            if code in hcpcs_codes or not hcpcs_codes:
                return code
    return hcpcs_codes[0] if hcpcs_codes else None


def _find_brand_name(generic_name: str) -> str | None:
    """Look up brand name from our reference table."""
    from backend.ingestion.drug_extractor import TNF_INHIBITOR_DRUGS
    for code, info in TNF_INHIBITOR_DRUGS.items():
        if info["name"].lower() in generic_name.lower():
            return info["brand"]
    return None
