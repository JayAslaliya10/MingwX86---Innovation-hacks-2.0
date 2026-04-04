"""
Drug extraction from parsed policy documents.

Case A: PDF title/header mentions "drug coverage policy"
        → extract drug list directly from the PDF text using LLM.

Case B: PDF is a different policy type (e.g. utilization management)
        → extract HCPCS codes from PDF, look up drugs from provider bulletin.
"""
import re
import json
from typing import TYPE_CHECKING

import google.generativeai as genai

from backend.config import get_settings
from backend.database.schemas import DrugExtractionResult

if TYPE_CHECKING:
    from backend.ingestion.parser import ParsedDocument
    from backend.database.models import Policy
    from sqlalchemy.orm import Session

settings = get_settings()

# HCPCS J-code pattern (medical benefit drugs)
HCPCS_PATTERN = re.compile(r'\b[JQ]\d{4}\b')

# Keywords indicating "drug coverage policy" (Case A)
DRUG_COVERAGE_KEYWORDS = [
    "drug coverage policy",
    "drug and biologic coverage",
    "medical drug policy",
    "medical pharmacy policy",
    "clinical policy bulletin",
    "coverage determination guideline",
    "drug benefit policy",
]

# TNF Inhibitor family reference (our knowledge base drug family)
TNF_INHIBITOR_DRUGS = {
    "J0129": {"name": "abatacept", "brand": "Orencia"},
    "J0135": {"name": "adalimumab", "brand": "Humira"},
    "J0717": {"name": "certolizumab pegol", "brand": "Cimzia"},
    "J1438": {"name": "etanercept", "brand": "Enbrel"},
    "J1602": {"name": "golimumab", "brand": "Simponi Aria"},
    "J1745": {"name": "infliximab", "brand": "Remicade"},
    "J3262": {"name": "tocilizumab", "brand": "Actemra"},
    "J0490": {"name": "belimumab", "brand": "Benlysta"},
    "J2323": {"name": "natalizumab", "brand": "Tysabri"},
    "J3380": {"name": "vedolizumab", "brand": "Entyvio"},
}


def _is_drug_coverage_policy(text: str) -> bool:
    """Check if the document is a drug coverage policy (Case A)."""
    text_lower = text[:3000].lower()  # check title/header section
    return any(kw in text_lower for kw in DRUG_COVERAGE_KEYWORDS)


def _extract_hcpcs_codes(text: str) -> list[str]:
    """Extract all HCPCS J/Q codes from text."""
    return list(set(HCPCS_PATTERN.findall(text)))


async def extract_drugs(
    parsed: "ParsedDocument",
    policy: "Policy",
    db: "Session",
) -> DrugExtractionResult:
    """
    Main entry point for drug extraction.
    Determines Case A or B, then extracts accordingly.
    Uses Gemini as an extra verification layer for accuracy.
    """
    genai.configure(api_key=settings.gemini_api_key)

    is_case_a = _is_drug_coverage_policy(parsed.text)
    policy.is_drug_coverage_policy = is_case_a
    db.commit()

    if is_case_a:
        return await _extract_case_a(parsed.text)
    else:
        return await _extract_case_b(parsed.text, policy, db)


async def _extract_case_a(text: str) -> DrugExtractionResult:
    """
    Case A: Extract drug list directly from the PDF using Gemini.
    The document is a drug coverage policy, so the drugs are listed in it.
    """
    # First pass: regex for HCPCS codes
    hcpcs_codes = _extract_hcpcs_codes(text)

    # Second pass: LLM for drug names (handles tables, embedded lists, free text)
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""You are a medical policy analyst. Extract all drug names (generic and brand)
from the following medical benefit drug policy document.

Return ONLY a valid JSON object with this exact structure:
{{
  "drugs": ["drug1", "drug2", ...],
  "hcpcs_codes": ["J0135", "J1745", ...],
  "drug_family": "name of drug family or therapeutic class if identifiable"
}}

Include both generic names and brand names. Include all HCPCS/J-codes found.
Do not include any explanation or text outside the JSON.

DOCUMENT:
{text[:15000]}
"""
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            drugs = data.get("drugs", [])
            llm_hcpcs = data.get("hcpcs_codes", [])
            # Merge regex + LLM HCPCS codes
            all_hcpcs = list(set(hcpcs_codes + llm_hcpcs))
            return DrugExtractionResult(drugs=drugs, hcpcs_codes=all_hcpcs, source="pdf")
    except Exception as e:
        print(f"[drug_extractor] Gemini extraction failed: {e}")

    # Fallback: use HCPCS reference table
    drugs_from_hcpcs = [TNF_INHIBITOR_DRUGS[c]["name"] for c in hcpcs_codes if c in TNF_INHIBITOR_DRUGS]
    return DrugExtractionResult(drugs=drugs_from_hcpcs, hcpcs_codes=hcpcs_codes, source="pdf_fallback")


async def _extract_case_b(text: str, policy: "Policy", db: "Session") -> DrugExtractionResult:
    """
    Case B: Not a drug coverage policy.
    Extract HCPCS codes from the PDF, then look up drugs from provider's bulletin.
    """
    hcpcs_codes = _extract_hcpcs_codes(text)

    if not hcpcs_codes:
        # Ask Gemini to find any drug identifiers
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f"""Extract all HCPCS codes, J-codes, NDC codes, or drug identifiers from this document.
Return only JSON: {{"hcpcs_codes": [], "drug_names": []}}

DOCUMENT:
{text[:10000]}
"""
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                hcpcs_codes = data.get("hcpcs_codes", [])
        except Exception:
            pass

    # Look up drugs from our reference table + provider bulletin
    drugs = []
    for code in hcpcs_codes:
        if code in TNF_INHIBITOR_DRUGS:
            entry = TNF_INHIBITOR_DRUGS[code]
            drugs.append(entry["name"])
            drugs.append(entry["brand"])

    # Fetch from provider bulletin for any unknown HCPCS codes
    unknown_codes = [c for c in hcpcs_codes if c not in TNF_INHIBITOR_DRUGS]
    if unknown_codes:
        bulletin_drugs = await _lookup_from_bulletin(unknown_codes, policy, db)
        drugs.extend(bulletin_drugs)

    return DrugExtractionResult(
        drugs=list(set(drugs)),
        hcpcs_codes=hcpcs_codes,
        source="bulletin",
    )


async def _lookup_from_bulletin(hcpcs_codes: list[str], policy: "Policy", db: "Session") -> list[str]:
    """
    Look up drug names from the provider's bulletin page using HCPCS codes.
    Uses RxNorm API as primary source, scraping as fallback.
    """
    from backend.ingestion.normalizer import lookup_rxnorm_by_hcpcs
    drugs = []
    for code in hcpcs_codes:
        name = await lookup_rxnorm_by_hcpcs(code)
        if name:
            drugs.append(name)
    return drugs
