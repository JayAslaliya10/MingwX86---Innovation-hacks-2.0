"""
UnitedHealthcare policy scraper.
Fetches live policy content from uhcprovider.com for change detection.
"""
import re
import httpx
from bs4 import BeautifulSoup

UHC_POLICY_INDEX = "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html"


async def fetch_policy_text(pdf_url: str) -> str | None:
    """
    Fetch policy text from a UHC PDF URL.
    Returns the raw text content, or None on failure.
    """
    try:
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (research tool)"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "pdf" in content_type:
                # Parse PDF content
                from backend.ingestion.parser import parse_pdf
                import tempfile, os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                try:
                    parsed = await parse_pdf(tmp_path)
                    return parsed.text
                finally:
                    os.unlink(tmp_path)
            elif "html" in content_type:
                soup = BeautifulSoup(resp.text, "html.parser")
                return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"[uhc_scraper] Failed to fetch {pdf_url}: {e}")
    return None


async def get_policy_effective_date(text: str) -> str | None:
    """Extract effective date from UHC policy text."""
    patterns = [
        r"effective\s+(?:date[:\s]+)?(\w+\s+\d{1,2},?\s+\d{4})",
        r"(\w+\s+\d{1,2},?\s+\d{4})\s+effective",
        r"policy\s+date[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"last\s+(?:reviewed|updated|revised)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
