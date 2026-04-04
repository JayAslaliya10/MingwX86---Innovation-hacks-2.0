from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from backend.config import get_settings
from backend.database.connection import init_db
from backend.api import user_routes, policy_routes, drug_routes, comparison_routes, chat_routes

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("✅ Database initialized")

    # Pre-load knowledge base if not already indexed
    try:
        from backend.rag.knowledge_base import preload_knowledge_base
        await preload_knowledge_base()
        print("✅ Knowledge base ready")
    except Exception as e:
        print(f"⚠️  Knowledge base preload skipped: {e}")

    yield
    # Shutdown (nothing needed)


app = FastAPI(
    title="MedPolicy Tracker API",
    description="AI-powered Medical Benefit Drug Policy Tracker",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ───────────────────────────────────────────────────────────────
app.include_router(user_routes.router)
app.include_router(policy_routes.router)
app.include_router(drug_routes.router)
app.include_router(comparison_routes.router)
app.include_router(chat_routes.router)


# ─── Serve React build (production) ───────────────────────────────────────────
frontend_build = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_build):
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
