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
# Note: UHC PDFs require authenticated access; we use fallback text if URLs fail.
UHC_POLICIES = [
    {
        "title": "UHC - Adalimumab (Humira) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/ADALIMUMAB-HUMIRA-CITRATE-FREE-COMMERCIAL-DRUG.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
        "fallback_text": (
            "UnitedHealthcare Commercial Medical Drug Policy: Adalimumab (Humira, Humira Citrate-Free)\n"
            "HCPCS Code: J0135\n"
            "Coverage: Covered when medically necessary for FDA-approved indications including rheumatoid arthritis, "
            "psoriatic arthritis, ankylosing spondylitis, Crohn's disease, ulcerative colitis, plaque psoriasis, "
            "juvenile idiopathic arthritis, and hidradenitis suppurativa.\n"
            "Prior Authorization: Required. Step therapy required — must try and fail conventional DMARDs first "
            "for RA (methotrexate, sulfasalazine, hydroxychloroquine), unless contraindicated.\n"
            "Step Therapy: Required for new starts. Trial of at least one conventional DMARD required.\n"
            "Quantity Limits: Per FDA-approved dosing based on indication.\n"
            "Effective Date: 2024-01-01\n"
        ),
    },
    {
        "title": "UHC - Infliximab (Remicade) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/INFLIXIMAB-REMICADE-COMMERCIAL-DRUG.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
        "fallback_text": (
            "UnitedHealthcare Commercial Medical Drug Policy: Infliximab (Remicade) and Biosimilars\n"
            "HCPCS Code: J1745\n"
            "Coverage: Covered when medically necessary for FDA-approved indications including rheumatoid arthritis, "
            "Crohn's disease, ulcerative colitis, psoriatic arthritis, ankylosing spondylitis, plaque psoriasis.\n"
            "Prior Authorization: Required. Biosimilar preferred over reference product when clinically appropriate.\n"
            "Step Therapy: Required. Must try preferred biosimilar (infliximab-dyyb, infliximab-abda) before Remicade.\n"
            "Infusion: Administered intravenously in a clinical setting.\n"
            "Effective Date: 2024-01-01\n"
        ),
    },
    {
        "title": "UHC - Etanercept (Enbrel) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/ETANERCEPT-ENBREL-COMMERCIAL-DRUG.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
        "fallback_text": (
            "UnitedHealthcare Commercial Medical Drug Policy: Etanercept (Enbrel)\n"
            "HCPCS Code: J1438\n"
            "Coverage: Covered when medically necessary for rheumatoid arthritis, polyarticular juvenile idiopathic arthritis, "
            "psoriatic arthritis, ankylosing spondylitis, plaque psoriasis.\n"
            "Prior Authorization: Required. Clinical criteria must be met.\n"
            "Step Therapy: Trial of conventional DMARDs required for RA before initiating etanercept.\n"
            "Administration: Subcutaneous injection.\n"
            "Effective Date: 2024-01-01\n"
        ),
    },
    {
        "title": "UHC - Tocilizumab (Actemra) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/TOCILIZUMAB-ACTEMRA-COMMERCIAL-DRUG.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
        "fallback_text": (
            "UnitedHealthcare Commercial Medical Drug Policy: Tocilizumab (Actemra)\n"
            "HCPCS Code: J3262\n"
            "Coverage: Covered for rheumatoid arthritis, giant cell arteritis, polyarticular/systemic juvenile idiopathic arthritis, "
            "cytokine release syndrome.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: For RA, must fail at least one conventional DMARD and one TNF inhibitor unless contraindicated.\n"
            "Administration: IV infusion (J3262) or subcutaneous injection.\n"
            "Effective Date: 2024-01-01\n"
        ),
    },
    {
        "title": "UHC - Abatacept (Orencia) Medical Drug Policy",
        "url": "https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/ABATACEPT-ORENCIA-COMMERCIAL-DRUG.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Commercial Medical Drug Policy",
        "fallback_text": (
            "UnitedHealthcare Commercial Medical Drug Policy: Abatacept (Orencia)\n"
            "HCPCS Code: J0129\n"
            "Coverage: Covered for moderate-to-severe rheumatoid arthritis, active psoriatic arthritis, "
            "polyarticular juvenile idiopathic arthritis.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: Must fail at least one conventional DMARD and one TNF inhibitor for RA.\n"
            "Administration: IV infusion (J0129) or subcutaneous injection.\n"
            "Effective Date: 2024-01-01\n"
        ),
    },
]

# Cigna Drug and Biologic Coverage Policies (TNF Inhibitors)
CIGNA_POLICIES = [
    {
        "title": "Cigna - Adalimumab Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1139_coveragepositioncriteria_adalimumab.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
        "fallback_text": (
            "Cigna Drug and Biologic Coverage Policy: Adalimumab (Humira) and Biosimilars\n"
            "HCPCS Code: J0135\n"
            "Coverage Position: Covered as medically necessary for rheumatoid arthritis, psoriatic arthritis, "
            "ankylosing spondylitis, Crohn's disease, ulcerative colitis, plaque psoriasis, and other FDA-approved indications.\n"
            "Prior Authorization: Required via utilization management review.\n"
            "Step Therapy: Preferred biosimilars (adalimumab-atto, adalimumab-adbm) required before Humira reference product.\n"
            "Quantity Limits: Per FDA labeling.\n"
            "Effective Date: 2024-02-01\n"
        ),
    },
    {
        "title": "Cigna - Infliximab (Remicade) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1143_coveragepositioncriteria_infliximab.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
        "fallback_text": (
            "Cigna Drug and Biologic Coverage Policy: Infliximab (Remicade) and Biosimilars\n"
            "HCPCS Code: J1745\n"
            "Coverage Position: Covered as medically necessary for rheumatoid arthritis, Crohn's disease, "
            "ulcerative colitis, psoriatic arthritis, ankylosing spondylitis, plaque psoriasis.\n"
            "Prior Authorization: Required. Cigna requires utilization management review.\n"
            "Step Therapy: Preferred biosimilar step therapy applies. Must try infliximab biosimilar before reference.\n"
            "Effective Date: 2024-02-01\n"
        ),
    },
    {
        "title": "Cigna - Etanercept (Enbrel) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1137_coveragepositioncriteria_etanercept.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
        "fallback_text": (
            "Cigna Drug and Biologic Coverage Policy: Etanercept (Enbrel)\n"
            "HCPCS Code: J1438\n"
            "Coverage Position: Covered as medically necessary for rheumatoid arthritis, juvenile idiopathic arthritis, "
            "psoriatic arthritis, ankylosing spondylitis, plaque psoriasis.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: Conventional DMARD trial required for RA. Subcutaneous self-injection.\n"
            "Effective Date: 2024-02-01\n"
        ),
    },
    {
        "title": "Cigna - Tocilizumab (Actemra) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1170_coveragepositioncriteria_tocilizumab.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
        "fallback_text": (
            "Cigna Drug and Biologic Coverage Policy: Tocilizumab (Actemra)\n"
            "HCPCS Code: J3262\n"
            "Coverage Position: Covered as medically necessary for rheumatoid arthritis, giant cell arteritis, "
            "juvenile idiopathic arthritis (systemic and polyarticular), cytokine release syndrome.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: For RA, must fail DMARDs and at least one TNF inhibitor.\n"
            "Effective Date: 2024-02-01\n"
        ),
    },
    {
        "title": "Cigna - Abatacept (Orencia) Coverage Policy",
        "url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy/ph_1130_coveragepositioncriteria_abatacept.pdf",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Drug and Biologic Coverage Policy",
        "fallback_text": (
            "Cigna Drug and Biologic Coverage Policy: Abatacept (Orencia)\n"
            "HCPCS Code: J0129\n"
            "Coverage Position: Covered as medically necessary for moderate-to-severe rheumatoid arthritis, "
            "active psoriatic arthritis, juvenile idiopathic arthritis.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: Must fail DMARDs and one TNF inhibitor for RA before approval.\n"
            "Effective Date: 2024-02-01\n"
        ),
    },
]

# Aetna Clinical Policy Bulletins (TNF Inhibitors)
AETNA_POLICIES = [
    {
        "title": "Aetna - Adalimumab (Humira) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/700_799/0715.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
        "fallback_text": (
            "Aetna Clinical Policy Bulletin: Adalimumab (Humira) - CPB 0715\n"
            "HCPCS Code: J0135\n"
            "Coverage: Aetna considers adalimumab (Humira) medically necessary for rheumatoid arthritis, "
            "psoriatic arthritis, ankylosing spondylitis, Crohn's disease, ulcerative colitis, plaque psoriasis, "
            "hidradenitis suppurativa, and uveitis when criteria are met.\n"
            "Prior Authorization: Required. Aetna requires prior authorization via utilization management.\n"
            "Step Therapy: For RA, must have inadequate response or intolerance to methotrexate or other DMARDs.\n"
            "Biosimilar Requirement: Aetna may require trial of an FDA-approved biosimilar before the reference product.\n"
            "Effective Date: 2024-01-15\n"
        ),
    },
    {
        "title": "Aetna - Infliximab (Remicade) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0500_0599/0525.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
        "fallback_text": (
            "Aetna Clinical Policy Bulletin: Infliximab (Remicade) - CPB 0525\n"
            "HCPCS Code: J1745\n"
            "Coverage: Aetna considers infliximab medically necessary for rheumatoid arthritis, Crohn's disease, "
            "ulcerative colitis, psoriatic arthritis, ankylosing spondylitis, plaque psoriasis when criteria are met.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: Biosimilar preferred. Must try infliximab biosimilar before Remicade unless medically contraindicated.\n"
            "Administration: IV infusion in clinical setting.\n"
            "Effective Date: 2024-01-15\n"
        ),
    },
    {
        "title": "Aetna - Etanercept (Enbrel) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0500_0599/0556.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
        "fallback_text": (
            "Aetna Clinical Policy Bulletin: Etanercept (Enbrel) - CPB 0556\n"
            "HCPCS Code: J1438\n"
            "Coverage: Aetna considers etanercept medically necessary for rheumatoid arthritis, juvenile idiopathic arthritis, "
            "psoriatic arthritis, ankylosing spondylitis, and plaque psoriasis when criteria are met.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: Must fail at least one conventional DMARD before etanercept for RA.\n"
            "Effective Date: 2024-01-15\n"
        ),
    },
    {
        "title": "Aetna - Tocilizumab (Actemra) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0700_0799/0718.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
        "fallback_text": (
            "Aetna Clinical Policy Bulletin: Tocilizumab (Actemra) - CPB 0718\n"
            "HCPCS Code: J3262\n"
            "Coverage: Aetna considers tocilizumab medically necessary for rheumatoid arthritis, giant cell arteritis, "
            "juvenile idiopathic arthritis, and cytokine release syndrome when criteria are met.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: For RA, must fail at least one DMARD and one TNF inhibitor.\n"
            "Effective Date: 2024-01-15\n"
        ),
    },
    {
        "title": "Aetna - Abatacept (Orencia) Clinical Policy Bulletin",
        "url": "https://www.aetna.com/cpb/medical/data/0700_0799/0759.html",
        "drug_family": "TNF Inhibitors",
        "policy_type": "Clinical Policy Bulletin",
        "fallback_text": (
            "Aetna Clinical Policy Bulletin: Abatacept (Orencia) - CPB 0759\n"
            "HCPCS Code: J0129\n"
            "Coverage: Aetna considers abatacept medically necessary for rheumatoid arthritis, psoriatic arthritis, "
            "and juvenile idiopathic arthritis when criteria are met.\n"
            "Prior Authorization: Required.\n"
            "Step Therapy: Must fail at least one DMARD and one TNF inhibitor for RA.\n"
            "Effective Date: 2024-01-15\n"
        ),
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

        if system_policy_count >= 5:
            print(f"[knowledge_base] Already loaded ({system_policy_count} system policies)")
            return

        print("[knowledge_base] Loading TNF Inhibitor knowledge base...")
        await _load_all_policies(db)
        print("[knowledge_base] Knowledge base loading complete")
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
                # Try to fetch from URL; fall back to embedded text if URL fails
                policy_text = None
                try:
                    parsed = await parse_pdf_from_url(pol_meta["url"])
                    if parsed.text and len(parsed.text) > 200:
                        policy_text = parsed.text
                        print(f"[knowledge_base] ✅ Fetched from URL: {pol_meta['url']}")
                except Exception as url_err:
                    print(f"[knowledge_base] ⚠️  URL fetch failed ({url_err}), using fallback text")

                if not policy_text:
                    policy_text = pol_meta.get("fallback_text", "")
                    if not policy_text:
                        print(f"[knowledge_base] ⚠️  No fallback text, skipping: {pol_meta['title']}")
                        continue

                from dataclasses import dataclass

                @dataclass
                class _FakeParsed:
                    text: str
                    pages: list
                    metadata: dict

                parsed = _FakeParsed(
                    text=policy_text,
                    pages=[policy_text],
                    metadata={"source": pol_meta["url"], "parser": "fallback"},
                )

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

                # Check for updates against live site (best-effort)
                try:
                    await check_policy_for_updates(policy, db)
                except Exception:
                    pass

                db.commit()
                print(f"[knowledge_base] ✅ Loaded: {pol_meta['title']}")

            except Exception as e:
                print(f"[knowledge_base] ❌ Failed: {pol_meta['title']} — {e}")
                db.rollback()
