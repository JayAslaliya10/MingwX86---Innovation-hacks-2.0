"""
RAG retriever: query the vector store and build context for LLM responses.
"""
from sqlalchemy.orm import Session
from backend.rag.indexer import similarity_search


async def retrieve_context(
    query: str,
    db: Session,
    top_k: int = 5,
    payer_filter: str | None = None,
) -> str:
    """
    Retrieve the most relevant policy chunks for a query.
    Returns formatted context string for LLM consumption.
    """
    results = await similarity_search(query, db, top_k=top_k)

    if payer_filter:
        results = [r for r in results if payer_filter.lower() in (r.get("payer_name") or "").lower()]

    if not results:
        return "No relevant policy information found in the knowledge base."

    context_parts = []
    for r in results:
        context_parts.append(
            f"[Source: {r['payer_name']} - {r['policy_title']}]\n{r['chunk_text']}"
        )

    return "\n\n---\n\n".join(context_parts)
