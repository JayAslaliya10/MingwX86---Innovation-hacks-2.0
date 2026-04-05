from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.database import models  # noqa: F401 - registers all models
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    _seed_payers()


def _seed_payers():
    """Ensure the 3 payers always exist in the DB at startup."""
    from backend.database.models import Payer
    db = SessionLocal()
    try:
        payers = [
            {
                "name": "UnitedHealthcare",
                "bulletin_url": "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html",
                "policy_index_url": "https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html",
            },
            {
                "name": "Cigna",
                "bulletin_url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy_a-z.html",
                "policy_index_url": "https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy_a-z.html",
            },
            {
                "name": "Aetna",
                "bulletin_url": "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html",
                "policy_index_url": "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html",
            },
        ]
        for p in payers:
            exists = db.query(Payer).filter(Payer.name == p["name"]).first()
            if not exists:
                db.add(Payer(**p))
                print(f"[db] Seeded payer: {p['name']}")
        db.commit()
    except Exception as e:
        print(f"[db] Payer seeding error: {e}")
        db.rollback()
    finally:
        db.close()
