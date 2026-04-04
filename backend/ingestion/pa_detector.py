"""
Prior Authorization (PA) detection from policy text.

Step 1: Regex scan for PA trigger keywords.
Step 2: Gemini LLM to extract structured PA info and flag specific drugs.
"""
import re
import json

import google.generativeai as genai

from backend.config import get_settings
from backend.database.schemas import PAExtractionResult

settings = get_settings()

# Keywords that indicate a prior authorization requirement
PA_KEYWORDS = [
    r"prior\s+authorization",
    r"prior\s+auth(?:orization)?",
    r"precertification",
    r"pre-?certification",
    r"utilization\s+management\s+rule",
    r"utilization\s+management",
    r"medical\s+necessity",
    r"step\s+therapy",
    r"pre-?approval",
    r"coverage\s+criteria",
    r"clinical\s+criteria",
]

PA_PATTERN = re.compile("|".join(PA_KEYWORDS), re.IGNORECASE)


def _has_pa_keywords(text: str) -> bool:
    return bool(PA_PATTERN.search(text))


async def detect_prior_auth(text: str, drug_names: list[str]) -> PAExtractionResult:
    """
    Detect prior authorization requirements in policy text.

    Returns:
        PAExtractionResult with:
        - prior_auth_required: bool
        - drugs_requiring_pa: list of drug names that need PA
        - evidence_snippets: relevant text excerpts
    """
    genai.configure(api_key=settings.gemini_api_key)

    # Quick regex pre-check
    has_pa = _has_pa_keywords(text)

    if not has_pa:
        return PAExtractionResult(
            prior_auth_required=False,
            drugs_requiring_pa=[],
            evidence_snippets=[],
        )

    # Extract PA snippets via regex for evidence
    evidence_snippets = _extract_pa_snippets(text)

    # Use Gemini to precisely determine which drugs require PA
    model = genai.GenerativeModel("gemini-1.5-pro")

    drugs_str = ", ".join(drug_names) if drug_names else "any drug mentioned"

    prompt = f"""You are a medical policy analyst. Analyze this medical benefit drug policy document
and determine prior authorization requirements.

Drugs in this policy: {drugs_str}

Return ONLY a valid JSON object:
{{
  "prior_auth_required": true/false,
  "drugs_requiring_pa": ["drug1", "drug2"],
  "evidence_snippets": ["exact quote from document showing PA requirement", ...],
  "pa_criteria_summary": "brief summary of the PA criteria if any"
}}

Rules:
- Only include drugs in drugs_requiring_pa if the document EXPLICITLY states they need PA
- evidence_snippets should be direct quotes from the document (max 3, max 200 chars each)
- If the document says all drugs require PA, list all drug names
- If no specific drugs are called out for PA, return empty list

DOCUMENT (relevant sections):
{_extract_pa_sections(text)}
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return PAExtractionResult(
                prior_auth_required=data.get("prior_auth_required", True),
                drugs_requiring_pa=data.get("drugs_requiring_pa", []),
                evidence_snippets=data.get("evidence_snippets", evidence_snippets[:3]),
            )
    except Exception as e:
        print(f"[pa_detector] Gemini PA extraction failed: {e}")

    # Fallback: PA exists but we couldn't parse which drugs
    return PAExtractionResult(
        prior_auth_required=True,
        drugs_requiring_pa=drug_names,  # conservative: flag all
        evidence_snippets=evidence_snippets[:3],
    )


def _extract_pa_snippets(text: str, context_chars: int = 200) -> list[str]:
    """Extract text snippets around PA keyword matches."""
    snippets = []
    for match in PA_PATTERN.finditer(text):
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + context_chars)
        snippet = text[start:end].strip().replace("\n", " ")
        snippets.append(snippet)
    return snippets[:5]  # limit to 5 snippets


def _extract_pa_sections(text: str) -> str:
    """
    Extract the most relevant sections of the document for PA analysis.
    Focuses on sections that contain PA keywords (with surrounding context).
    """
    lines = text.split("\n")
    relevant_lines = []
    window = 10  # lines of context around each PA match

    for i, line in enumerate(lines):
        if PA_PATTERN.search(line):
            start = max(0, i - window)
            end = min(len(lines), i + window)
            relevant_lines.extend(lines[start:end])

    if not relevant_lines:
        return text[:8000]  # fallback to first 8k chars

    return "\n".join(relevant_lines)[:8000]
