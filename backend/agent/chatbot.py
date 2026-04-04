"""
Agentic AI chatbot using LlamaIndex ReAct Agent with Gemini 1.5 Pro.
The agent decides which tools to call based on the user's question.
"""
from typing import AsyncGenerator
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database.models import User

settings = get_settings()

SYSTEM_PROMPT = """You are MedPolicy AI, an expert assistant for medical benefit drug policy analysis.
You help users understand drug coverage across health plans (UnitedHealthcare, Cigna, Aetna).

You have access to tools to:
1. Search which health plans cover a specific drug
2. Compare policies for a drug across payers (side-by-side)
3. Get prior authorization requirements for a specific drug + payer
4. Check for recent policy updates
5. Search the knowledge base semantically for any coverage question

Always be specific and cite which payer/policy your information comes from.
If you're unsure, use the search_knowledge_base tool to find relevant information.
Format your responses clearly with headers and bullet points when appropriate.
"""


async def run_agent(message: str, user: User, db: Session, session_id: str | None = None) -> str:
    """Run the ReAct agent and return full response."""
    try:
        from llama_index.core.agent import ReActAgent
        from llama_index.llms.gemini import Gemini
        from backend.agent.tools import make_tools

        llm = Gemini(
            model="models/gemini-1.5-pro",
            api_key=settings.gemini_api_key,
        )

        tools = make_tools(user, db)

        agent = ReActAgent.from_tools(
            tools=tools,
            llm=llm,
            verbose=True,
            max_iterations=8,
            context=SYSTEM_PROMPT,
        )

        response = agent.chat(message)
        return str(response)

    except Exception as e:
        print(f"[chatbot] Agent error: {e}")
        # Fallback: direct Gemini response with RAG context
        return await _fallback_rag_response(message, user, db)


async def run_agent_streaming(
    message: str,
    user: User,
    db: Session,
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream agent responses for WebSocket."""
    try:
        from llama_index.core.agent import ReActAgent
        from llama_index.llms.gemini import Gemini
        from backend.agent.tools import make_tools

        llm = Gemini(
            model="models/gemini-1.5-pro",
            api_key=settings.gemini_api_key,
        )

        tools = make_tools(user, db)
        agent = ReActAgent.from_tools(
            tools=tools,
            llm=llm,
            verbose=False,
            max_iterations=8,
            context=SYSTEM_PROMPT,
        )

        # LlamaIndex streaming
        response = agent.stream_chat(message)
        for token in response.response_gen:
            yield token

    except Exception as e:
        print(f"[chatbot] Streaming agent error: {e}")
        fallback = await _fallback_rag_response(message, user, db)
        yield fallback


async def _fallback_rag_response(message: str, user: User, db: Session) -> str:
    """Direct Gemini + RAG fallback when agent framework fails."""
    import google.generativeai as genai
    from backend.rag.indexer import similarity_search

    genai.configure(api_key=settings.gemini_api_key)

    # Get relevant context from vector store
    context_results = await similarity_search(message, db, top_k=5)
    context = "\n\n".join([
        f"[{r['payer_name']} - {r['policy_title']}]\n{r['chunk_text']}"
        for r in context_results
    ])

    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""{SYSTEM_PROMPT}

Use the following policy excerpts to answer the user's question.
If the context doesn't contain the answer, say so clearly.

POLICY CONTEXT:
{context}

USER QUESTION: {message}
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"I'm sorry, I couldn't process your request. Please try again. Error: {str(e)}"
