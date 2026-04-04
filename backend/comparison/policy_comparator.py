"""
Cross-policy comparison engine.
For a given drug, compares all payer policies covering it side-by-side.
Uses Gemini 1.5 Pro's large context window to process multiple policies at once.
Output: structured comparison table stored in PolicyComparison table.
"""
import json
import re
from datetime import datetime

import google.generativeai as genai
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.models import Drug, DrugPolicyMap, Policy, Payer, PolicyComparison
from backend.database.schemas import ComparisonTableOut, ComparisonRow

settings = get_settings()

COMPARISON_FIELDS = [
    "Covered Indications / Diagnoses",
    "Prior Authorization Required",
    "Prior Authorization Criteria",
    "Step Therapy Required",
    "Step Therapy Details",
    "Site of Care Restrictions",
    "Quantity Limits",
    "Effective Date",
    "Coverage Notes",
]


async def compare_policies_for_drug(
    drug: Drug,
    payer_names: list[str] | None,
    db: Session,
) -> ComparisonTableOut:
    """
    Compare all policies covering a drug across payers.
    Returns a structured ComparisonTableOut with rows per field.
    """
    genai.configure(api_key=settings.gemini_api_key)

    # Get all drug→policy mappings
    mappings = db.query(DrugPolicyMap).filter(DrugPolicyMap.drug_id == drug.id).all()

    policies_data = []
    for m in mappings:
        policy = db.query(Policy).filter(Policy.id == m.policy_id).first()
        payer = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None

        if payer_names and payer and payer.name not in payer_names:
            continue

        if policy and payer:
            policies_data.append({
                "payer": payer.name,
                "policy_title": policy.title,
                "policy_id": str(policy.id),
                "text": (policy.raw_text or "")[:8000],  # limit per policy for context
            })

    if not policies_data:
        return ComparisonTableOut(
            drug_name=drug.name,
            rows=[],
            generated_at=datetime.utcnow(),
        )

    # Build prompt with all policy texts
    policies_prompt = ""
    payer_list = []
    for pd in policies_data:
        payer_list.append(pd["payer"])
        policies_prompt += f"\n\n=== {pd['payer']} - {pd['policy_title']} ===\n{pd['text']}"

    model = genai.GenerativeModel("gemini-1.5-pro")

    prompt = f"""You are a medical policy analyst. Compare the following medical benefit drug policies
for {drug.name} ({drug.brand_name or ''}) across these health plans: {', '.join(payer_list)}.

For each of the following criteria, extract the relevant information from each payer's policy.
If a payer's policy does not address a criterion, use "Not specified".

Criteria to compare:
{chr(10).join(f'- {f}' for f in COMPARISON_FIELDS)}

Return ONLY valid JSON in this exact structure:
{{
  "rows": [
    {{
      "field": "Covered Indications / Diagnoses",
      "values": {{
        "{payer_list[0] if payer_list else 'Payer1'}": "...",
        "{payer_list[1] if len(payer_list) > 1 else 'Payer2'}": "..."
      }}
    }},
    ...
  ]
}}

POLICIES:
{policies_prompt[:40000]}
"""

    rows = []
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            rows = data.get("rows", [])
    except Exception as e:
        print(f"[comparator] Gemini comparison failed: {e}")
        # Fallback: build basic rows from DB data
        rows = _build_basic_rows(drug, mappings, policies_data, db)

    # Store in DB
    comparison = PolicyComparison(
        drug_id=drug.id,
        policy_ids=[m.policy_id for m in mappings],
        comparison_table={"rows": rows},
        generated_at=datetime.utcnow(),
    )
    db.add(comparison)
    db.commit()

    return ComparisonTableOut(
        drug_name=drug.name,
        rows=[ComparisonRow(**r) for r in rows],
        generated_at=comparison.generated_at,
    )


def _build_basic_rows(drug, mappings, policies_data, db: Session) -> list[dict]:
    """Fallback: build comparison rows from structured DB fields."""
    from backend.database.models import PriorAuth
    rows = []
    payers = {pd["payer"]: pd for pd in policies_data}

    for field in COMPARISON_FIELDS:
        values = {}
        for m in mappings:
            policy = db.query(Policy).filter(Policy.id == m.policy_id).first()
            payer = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
            if not payer:
                continue
            pa = db.query(PriorAuth).filter(
                PriorAuth.drug_id == drug.id,
                PriorAuth.policy_id == m.policy_id,
            ).first()

            if field == "Prior Authorization Required":
                values[payer.name] = "Yes" if (pa and pa.required) else "No"
            elif field == "Prior Authorization Criteria":
                values[payer.name] = pa.criteria_text or "Not specified" if pa else "Not specified"
            elif field == "Step Therapy Required":
                values[payer.name] = "Yes" if m.step_therapy_required else "No"
            elif field == "Site of Care Restrictions":
                values[payer.name] = ", ".join(m.site_of_care) if m.site_of_care else "Not specified"
            elif field == "Effective Date":
                values[payer.name] = policy.effective_date.strftime("%B %d, %Y") if policy.effective_date else "Not specified"
            else:
                values[payer.name] = "See policy document"

        rows.append({"field": field, "values": values})
    return rows
