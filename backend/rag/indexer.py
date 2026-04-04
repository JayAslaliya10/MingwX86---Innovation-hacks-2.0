"""
RAG indexing: chunk policy text and store embeddings in pgvector.
Uses LlamaIndex + Gemini text-embedding-004.
"""
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.models import Policy, PolicyEmbedding

settings = get_settings()

CHUNK_SIZE = 512      # characters per chunk
CHUNK_OVERLAP = 64


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def _get_embedding(text: str) -> list[float] | None:
    """Get embedding vector from Gemini text-embedding-004."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]
    except Exception as e:
        print(f"[indexer] Embedding failed: {e}")
        return None


async def index_policy(policy: Policy, text: str, db: Session) -> int:
    """
    Chunk policy text, generate embeddings, and store in pgvector.
    Returns number of chunks indexed.
    """
    if not text:
        return 0

    # Remove existing embeddings for this policy (re-index)
    db.query(PolicyEmbedding).filter(PolicyEmbedding.policy_id == policy.id).delete()
    db.commit()

    chunks = _chunk_text(text)
    indexed = 0

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        embedding = await _get_embedding(chunk)
        record = PolicyEmbedding(
            policy_id=policy.id,
            chunk_text=chunk,
            chunk_index=i,
            embedding=embedding,
            source=policy.source,
        )
        db.add(record)
        indexed += 1

    db.commit()
    print(f"[indexer] Indexed {indexed} chunks for policy {policy.id}")
    return indexed


async def similarity_search(
    query: str,
    db: Session,
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Search policy embeddings by semantic similarity.
    Returns top_k most relevant chunks with metadata.
    """
    from sqlalchemy import text as sql_text

    query_embedding = await _get_embedding(query)
    if not query_embedding:
        return []

    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

    source_clause = ""
    if source_filter:
        source_clause = f"AND pe.source = '{source_filter}'"

    sql = f"""
        SELECT
            pe.chunk_text,
            pe.policy_id,
            pe.source,
            p.title,
            py.name as payer_name,
            1 - (pe.embedding <=> '{embedding_str}'::vector) AS similarity
        FROM policy_embeddings pe
        JOIN policies p ON pe.policy_id = p.id
        LEFT JOIN payers py ON p.payer_id = py.id
        WHERE pe.embedding IS NOT NULL
        {source_clause}
        ORDER BY pe.embedding <=> '{embedding_str}'::vector
        LIMIT {top_k}
    """

    try:
        result = db.execute(sql_text(sql))
        rows = result.fetchall()
        return [
            {
                "chunk_text": row.chunk_text,
                "policy_id": str(row.policy_id),
                "source": row.source,
                "policy_title": row.title,
                "payer_name": row.payer_name,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[indexer] Similarity search failed: {e}")
        return []
