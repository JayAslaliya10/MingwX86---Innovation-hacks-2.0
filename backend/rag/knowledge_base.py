"""
Pre-load the RAG knowledge base with TNF Inhibitor policies from UHC, Cigna, and Aetna.
This runs once at startup if policies are not already indexed.

TNF Inhibitor / Biologics for Inflammatory Conditions:
- Adalimumab (Humira) - J0135
- Infliximab (Remicade) - J1745
- Etanercept (Enbrel) - J1438
- Certolizumab (Cimzia) - J0717
- Golimumab (Simponi Aria) - J1602
- Tocilizumab (Actemra) - J3262
- Abatacept (Orencia) - J0129
"""
import os
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database.models import Policy, Payer, PolicySource

# ─── Policy PDF URLs ───────────────────────────────────────────────────────────
# UnitedHealthcare Commercial Medical Drug Policies (TNF Inhibitors)
UHC_POLICIES = [
    {
        "title": "UHC - Adalimumab (Humira) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/adalimumab-humira.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
    },
    {
        "title": "UHC - Infliximab (Remicade) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/infliximab-remicade.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
    },
    {
        "title": "UHC - Etanercept (Enbrel) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/etanercept-enbrel.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
    },
    {
        "title": "UHC - Tocilizumab (Actemra) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/tocilizumab-actemra.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
    },
    {
        "title": "UHC - Abatacept (Orencia) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/abatacept-orencia.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
    },
]

# Cigna Drug and Biologic Coverage Policies (TNF Inhibitors)
CIGNA_POLICIES = [
    {
        "title": "Cigna - Adalimumab Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1139_coveragepositioncriteria_adalimumab.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
    },
    {
        "title": "Cigna - Infliximab (Remicade) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1143_coveragepositioncriteria_infliximab.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
    },
    {
        "title": "Cigna - Etanercept (Enbrel) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1137_coveragepositioncriteria_etanercept.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
    },
    {
        "title": "Cigna - Tocilizumab (Actemra) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1170_coveragepositioncriteria_tocilizumab.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
    },
    {
        "title": "Cigna - Abatacept (Orencia) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1130_coveragepositioncriteria_abatacept.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
    },
]

# Aetna Clinical Policy Bulletins (TNF Inhibitors)
AETNA_POLICIES = [
    {
        "title": "Aetna - Adalimumab (Humira) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/700_799/0715.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
    },
    {
        "title": "Aetna - Infliximab (Remicade) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0500_0599/0525.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
    },
    {
        "title": "Aetna - Etanercept (Enbrel) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0500_0599/0556.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
    },
    {
        "title": "Aetna - Tocilizumab (Actemra) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0700_0799/0718.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
    },
    {
        "title": "Aetna - Abatacept (Orencia) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0700_0799/0759.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
    },
]

ALL_POLICIES = {
    "UnitedHealthcare": UHC_POLICIES,
    "Cigna": CIGNA_POLICIES,
    "Aetna": AETNA_POLICIES,
}


async def preload_knowledge_base():
    """
    Check if knowledge base is already loaded. If not, load all policies.
    Called once at startup.
    """
    db = SessionLocal()
    try:
        system_policy_count = db.query(Policy).filter(
            Policy.source == PolicySource.system
        ).count()

        if system_policy_count >= 10:
            print(f"[knowledge_base] Already loaded ({system_policy_count} system policies)")
            return

        print("[knowledge_base] Loading TNF Inhibitor knowledge base...")
        await _load_all_policies(db)
        print("[knowledge_base] Knowledge base loaded successfully")
    finally:
        db.close()


async def _load_all_policies(db: Session):
    from backend.ingestion.parser import parse_pdf_from_url
    from backend.ingestion.drug_extractor import extract_drugs
    from backend.ingestion.pa_detector import detect_prior_auth
    from backend.ingestion.normalizer import normalize_drugs
    from backend.rag.indexer import index_policy
    from backend.scraping.change_detector import check_policy_for_updates
    import hashlib

    for payer_name, policies in ALL_POLICIES.items():
        payer = db.query(Payer).filter(Payer.name == payer_name).first()
        if not payer:
            print(f"[knowledge_base] Payer {payer_name} not found in DB, skipping")
            continue

        for pol_meta in policies:
            # Skip if already loaded
            existing = db.query(Policy).filter(
                Policy.title == pol_meta["title"],
                Policy.source == PolicySource.system,
            ).first()
            if existing:
                continue

            print(f"[knowledge_base] Loading: {pol_meta['title']}")
            try:
                # Parse the PDF/HTML
                parsed = await parse_pdf_from_url(pol_meta["url"])

                content_hash = hashlib.sha256(parsed.text.encode()).hexdigest()

                policy = Policy(
                    payer_id=payer.id,
                    title=pol_meta["title"],
                    drug_family=pol_meta["drug_family"],
                    policy_type=pol_meta["policy_type"],
                    pdf_url=pol_meta["url"],
                    raw_text=parsed.text,
                    content_hash=content_hash,
                    source=PolicySource.system,
                )
                db.add(policy)
                db.flush()

                # Extract drugs
                drug_result = await extract_drugs(parsed, policy, db)

                # PA detection
                pa_result = await detect_prior_auth(parsed.text, drug_result.drugs)

                # Normalize and store
                await normalize_drugs(drug_result, pa_result, policy, db)

                # Index into vector store
                await index_policy(policy, parsed.text, db)

                # Check for updates against live site
                await check_policy_for_updates(policy, db)

                db.commit()
                print(f"[knowledge_base] ✅ Loaded: {pol_meta['title']}")

            except Exception as e:
                print(f"[knowledge_base] ❌ Failed: {pol_meta['title']} — {e}")
                db.rollback()
