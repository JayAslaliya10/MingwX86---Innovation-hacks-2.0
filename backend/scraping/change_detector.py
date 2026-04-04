"""
Login-triggered change detection.

On every user login:
1. Fetch all policies associated with that user.
2. For each policy, fetch the live content from the provider's site.
3. Hash-compare with stored version.
4. If changed: semantic diff via Gemini, store in policy_updates, notify user.
"""
import hashlib
import difflib
import json
import re
from datetime import datetime
from uuid import UUID

import google.generativeai as genai
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.models import (
    Policy, PolicyUpdate, PolicyUpdateNotification,
    Payer, HealthCardPolicyMap, User, DrugPolicyMap
)

settings = get_settings()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def _fetch_live_policy_text(policy: Policy, payer: Payer) -> str | None:
    """Fetch the current live text of a policy from the provider's website."""
    if not policy.pdf_url:
        return None

    payer_name = payer.name if payer else ""

    if "unitedhealth" in payer_name.lower() or "uhc" in payer_name.lower():
        from backend.scraping.uhc_scraper import fetch_policy_text
        return await fetch_policy_text(policy.pdf_url)

    elif "cigna" in payer_name.lower():
        from backend.scraping.cigna_scraper import fetch_policy_text
        return await fetch_policy_text(policy.pdf_url)

    elif "aetna" in payer_name.lower():
        from backend.scraping.aetna_scraper import fetch_policy_text
        return await fetch_policy_text(policy.pdf_url)

    return None


async def _semantic_diff(old_text: str, new_text: str, policy_title: str) -> dict:
    """
    Use Gemini to summarize what changed between two policy versions.
    Returns: { diff_summary, change_class, effective_from }
    """
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")

    # Get structural diff for context
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm='', n=3))
    diff_text = "\n".join(diff[:100])  # limit diff size

    prompt = f"""You are a medical policy analyst. Analyze the changes between two versions of a medical benefit drug policy.

Policy: {policy_title}

DIFF (lines starting with + are new, - are removed):
{diff_text}

Return ONLY valid JSON:
{{
  "diff_summary": "1-2 sentence plain English summary of what changed",
  "change_class": "coverage|pa|step_therapy|site_of_care|effective_date|administrative|other",
  "effective_from": "date string if mentioned in changes, else null",
  "is_significant": true/false
}}

change_class options:
- coverage: coverage criteria changed
- pa: prior authorization requirements changed
- step_therapy: step therapy requirements changed
- site_of_care: site of care restrictions changed
- effective_date: only effective date changed
- administrative: administrative/formatting changes only
- other: other changes
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"[change_detector] Semantic diff failed: {e}")

    return {
        "diff_summary": "Policy content has been updated.",
        "change_class": "other",
        "effective_from": None,
        "is_significant": True,
    }


async def check_policy_for_updates(policy: Policy, db: Session) -> PolicyUpdate | None:
    """
    Check a single policy for updates against the live provider site.
    Returns a PolicyUpdate record if changes detected, else None.
    """
    payer = db.query(Payer).filter(Payer.id == policy.payer_id).first()
    live_text = await _fetch_live_policy_text(policy, payer)

    if not live_text or not live_text.strip():
        return None

    new_hash = _hash_text(live_text)
    old_hash = policy.content_hash

    if old_hash == new_hash:
        return None  # No change

    print(f"[change_detector] Change detected in: {policy.title}")

    # Semantic diff
    old_text = policy.raw_text or ""
    diff_result = await _semantic_diff(old_text, live_text, policy.title or "")

    # Parse effective_from date
    effective_from = None
    if diff_result.get("effective_from"):
        try:
            from dateutil import parser as dateparser
            effective_from = dateparser.parse(diff_result["effective_from"])
        except Exception:
            pass

    # Store update record
    update = PolicyUpdate(
        policy_id=policy.id,
        detected_at=datetime.utcnow(),
        effective_from=effective_from,
        old_hash=old_hash,
        new_hash=new_hash,
        old_text_snippet=old_text[:500] if old_text else None,
        new_text_snippet=live_text[:500],
        diff_summary=diff_result.get("diff_summary"),
        change_class=diff_result.get("change_class", "other"),
    )
    db.add(update)

    # Update policy with new content
    policy.content_hash = new_hash
    policy.raw_text = live_text
    policy.updated_at = datetime.utcnow()
    db.flush()

    # Re-index updated content
    try:
        from backend.rag.indexer import index_policy
        await index_policy(policy, live_text, db)
    except Exception as e:
        print(f"[change_detector] Re-indexing failed: {e}")

    db.commit()
    return update


async def run_change_detection_for_user(user_id: UUID, db: Session):
    """
    Run change detection for all policies associated with a user.
    Called as background task on every login.
    Creates notifications for any changes found.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    # Get user's policies
    if user.health_card_number:
        mapping = db.query(HealthCardPolicyMap).filter(
            HealthCardPolicyMap.health_card_number == user.health_card_number
        ).first()
        policy_ids = mapping.policy_ids if mapping else []
        policies = db.query(Policy).filter(Policy.id.in_(policy_ids)).all()
    else:
        policies = db.query(Policy).filter(Policy.uploaded_by == user_id).all()

    # Also check system policies (knowledge base)
    system_policies = db.query(Policy).filter(Policy.source == "system").all()
    all_policies = list({p.id: p for p in policies + system_policies}.values())

    for policy in all_policies:
        try:
            update = await check_policy_for_updates(policy, db)
            if update:
                # Create notification for this user
                existing_notif = db.query(PolicyUpdateNotification).filter(
                    PolicyUpdateNotification.user_id == user_id,
                    PolicyUpdateNotification.update_id == update.id,
                ).first()
                if not existing_notif:
                    notification = PolicyUpdateNotification(
                        user_id=user_id,
                        update_id=update.id,
                        seen=False,
                    )
                    db.add(notification)
                    db.commit()
        except Exception as e:
            print(f"[change_detector] Error checking policy {policy.id}: {e}")

    print(f"[change_detector] Completed for user {user_id}")
