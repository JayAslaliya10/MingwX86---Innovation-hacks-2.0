"""
Agent tools for the LlamaIndex ReAct agent.
Each tool wraps a specific backend capability.
"""
from sqlalchemy.orm import Session
from llama_index.core.tools import FunctionTool


def make_tools(user, db: Session) -> list:
    """Create all agent tools bound to the current user and DB session."""

    def search_drug_coverage(drug_name: str, payer: str = "") -> str:
        """
        Search which health plans cover a specific drug under their medical benefit.
        Args:
            drug_name: Generic or brand name of the drug (e.g. 'adalimumab' or 'Humira')
            payer: Optional payer name to filter (e.g. 'Cigna'). Leave empty for all payers.
        """
        from backend.database.models import Drug, DrugPolicyMap, Policy, Payer, PriorAuth
        drugs = db.query(Drug).filter(
            (Drug.name.ilike(f"%{drug_name}%")) |
            (Drug.brand_name.ilike(f"%{drug_name}%"))
        ).all()

        if not drugs:
            return f"No information found for drug '{drug_name}' in the knowledge base."

        results = []
        for drug in drugs:
            mappings = db.query(DrugPolicyMap).filter(
                DrugPolicyMap.drug_id == drug.id,
                DrugPolicyMap.covered == True,
            ).all()
            for m in mappings:
                policy = db.query(Policy).filter(Policy.id == m.policy_id).first()
                p = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
                if payer and p and payer.lower() not in p.name.lower():
                    continue
                pa = db.query(PriorAuth).filter(
                    PriorAuth.drug_id == drug.id,
                    PriorAuth.policy_id == m.policy_id,
                ).first()
                results.append(
                    f"- {p.name if p else 'Unknown'}: Covered | "
                    f"PA Required: {'Yes' if pa and pa.required else 'No'} | "
                    f"Step Therapy: {'Yes' if m.step_therapy_required else 'No'}"
                )

        if not results:
            return f"No coverage found for '{drug_name}'" + (f" at {payer}" if payer else "")
        return f"Coverage for {drug_name}:\n" + "\n".join(results)

    def compare_policies(drug_name: str, payers: str = "") -> str:
        """
        Compare medical benefit drug policies for a drug across multiple payers.
        Args:
            drug_name: Name of the drug to compare
            payers: Comma-separated list of payer names (e.g. 'UnitedHealthcare,Cigna'). Empty = all.
        """
        from backend.database.models import Drug
        import asyncio

        drugs = db.query(Drug).filter(
            (Drug.name.ilike(f"%{drug_name}%")) |
            (Drug.brand_name.ilike(f"%{drug_name}%"))
        ).all()

        if not drugs:
            return f"Drug '{drug_name}' not found."

        drug = drugs[0]
        payer_list = [p.strip() for p in payers.split(",")] if payers else None

        from backend.comparison.policy_comparator import compare_policies_for_drug
        result = asyncio.get_event_loop().run_until_complete(
            compare_policies_for_drug(drug, payer_list, db)
        )

        lines = [f"Policy Comparison for {drug_name}:"]
        for row in result.rows:
            lines.append(f"\n**{row.field}**")
            for payer, value in row.values.items():
                lines.append(f"  {payer}: {value}")
        return "\n".join(lines)

    def get_prior_auth_requirements(drug_name: str, payer: str) -> str:
        """
        Get prior authorization requirements for a specific drug from a specific payer.
        Args:
            drug_name: Name of the drug
            payer: Payer name (e.g. 'Aetna')
        """
        from backend.database.models import Drug, DrugPolicyMap, Policy, Payer, PriorAuth
        drugs = db.query(Drug).filter(
            (Drug.name.ilike(f"%{drug_name}%")) |
            (Drug.brand_name.ilike(f"%{drug_name}%"))
        ).all()

        if not drugs:
            return f"No information found for '{drug_name}'."

        for drug in drugs:
            mappings = db.query(DrugPolicyMap).filter(DrugPolicyMap.drug_id == drug.id).all()
            for m in mappings:
                policy = db.query(Policy).filter(Policy.id == m.policy_id).first()
                p = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
                if not p or payer.lower() not in p.name.lower():
                    continue
                pa = db.query(PriorAuth).filter(
                    PriorAuth.drug_id == drug.id,
                    PriorAuth.policy_id == m.policy_id,
                ).first()
                if pa:
                    required = "Yes" if pa.required else "No"
                    criteria = pa.criteria_text or "Not specified"
                    snippets = "\n".join(pa.evidence_snippets or [])
                    return (
                        f"Prior Authorization for {drug_name} ({p.name}):\n"
                        f"Required: {required}\n"
                        f"Criteria: {criteria}\n"
                        f"Evidence: {snippets}"
                    )

        return f"No PA information found for '{drug_name}' at '{payer}'."

    def check_policy_updates(policy_title: str = "") -> str:
        """
        Check for recent policy updates across payers.
        Args:
            policy_title: Optional specific policy title to check. Empty = all recent updates.
        """
        from backend.database.models import PolicyUpdate, Policy, Payer
        from datetime import timedelta
        query = db.query(PolicyUpdate).order_by(PolicyUpdate.detected_at.desc())
        updates = query.limit(10).all()

        if not updates:
            return "No policy updates detected recently."

        lines = ["Recent Policy Updates:"]
        for u in updates:
            policy = db.query(Policy).filter(Policy.id == u.policy_id).first()
            payer = db.query(Payer).filter(Payer.id == policy.payer_id).first() if policy else None
            if policy_title and policy and policy_title.lower() not in (policy.title or "").lower():
                continue
            lines.append(
                f"- [{payer.name if payer else 'Unknown'}] {policy.title if policy else 'Unknown'}: "
                f"{u.diff_summary or 'Updated'} "
                f"(detected {u.detected_at.strftime('%Y-%m-%d')})"
            )
        return "\n".join(lines)

    def search_knowledge_base(query: str) -> str:
        """
        Semantic search across all indexed medical benefit drug policies.
        Args:
            query: Natural language question about drug coverage
        """
        import asyncio
        from backend.rag.indexer import similarity_search

        results = asyncio.get_event_loop().run_until_complete(
            similarity_search(query, db, top_k=5)
        )

        if not results:
            return "No relevant policy information found."

        lines = [f"Relevant policy excerpts for: '{query}'\n"]
        for r in results:
            lines.append(
                f"[{r['payer_name']} - {r['policy_title']}] (similarity: {r['similarity']:.2f})\n"
                f"{r['chunk_text']}\n"
            )
        return "\n".join(lines)

    return [
        FunctionTool.from_defaults(fn=search_drug_coverage, name="search_drug_coverage"),
        FunctionTool.from_defaults(fn=compare_policies, name="compare_policies"),
        FunctionTool.from_defaults(fn=get_prior_auth_requirements, name="get_prior_auth_requirements"),
        FunctionTool.from_defaults(fn=check_policy_updates, name="check_policy_updates"),
        FunctionTool.from_defaults(fn=search_knowledge_base, name="search_knowledge_base"),
    ]
