"""
Aetna policy scraper.
Aetna publishes Clinical Policy Bulletins (CPBs) as HTML pages at aetna.com/cpb.
Index: https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html
"""
import re
import httpx
from bs4 import BeautifulSoup

AETNA_CPB_INDEX = "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html"
AETNA_CPB_BASE = "https://www.aetna.com/cpb/medical"


async def fetch_policy_text(policy_url: str) -> str | None:
    """
    Fetch Aetna CPB (HTML page) and extract policy text.
    Aetna CPBs are HTML, not PDFs.
    """
    try:
        async with httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(policy_url)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove navigation and non-policy content
            for tag in soup.find_all(["nav", "footer", "header", "script", "style", "aside"]):
                tag.decompose()

            # Try to get the main content area
            main = soup.find("main") or soup.find("div", class_=re.compile(r"content|policy|main"))
            if main:
                return main.get_text(separator="\n", strip=True)
            return soup.get_text(separator="\n", strip=True)

    except Exception as e:
        print(f"[aetna_scraper] Failed to fetch {policy_url}: {e}")
    return None


async def get_policy_effective_date(text: str) -> str | None:
    """Extract effective date from Aetna CPB text."""
    patterns = [
        r"effective\s+(?:date[:\s]+)?(\w+\s+\d{1,2},?\s+\d{4})",
        r"last\s+(?:reviewed|updated|revised)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})",
        r"(?:cpb\s+)?version[:\s]+[\w.]+\s+\((\w+\s+\d{4})\)",
        r"(\w+\s+\d{1,2},?\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:2000], re.IGNORECASE)
        if match:
            return match.group(1)
    return None


async def search_cpb_index(drug_name: str) -> str | None:
    """
    Search Aetna's CPB index for a drug and return the policy URL.
    """
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(AETNA_CPB_INDEX)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.find_all("a", href=True)
            drug_lower = drug_name.lower()
            for link in links:
                link_text = link.get_text().lower()
                if drug_lower in link_text or any(w in link_text for w in drug_lower.split()):
                    href = link["href"]
                    if not href.startswith("http"):
                        href = f"https://www.aetna.com{href}"
                    return href
    except Exception as e:
        print(f"[aetna_scraper] Index search failed: {e}")
    return None
