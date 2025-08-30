from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text
from backend_settings import settings
from models import (
    Car,
    ImportJob,
    Make,
    Model,
    Category,
    Dealership,
    Media,
)



def ensure_columns():
    """Idempotently add missing columns (SQLite)."""
    from sqlmodel import Session
    with Session(engine) as s:
        info = s.exec(text("PRAGMA table_info(cars);")).all()
        have = {row[1] for row in info}
        wanted = {
            "lot_number": "TEXT",
            "seller_rating": "REAL",
            "seller_reviews": "INTEGER",
            "make_id": "INTEGER",
            "model_id": "INTEGER",
            "category_id": "INTEGER",
            "dealership_id": "INTEGER",
        }
        for col, typ in wanted.items():
            if col not in have:
                s.exec(text(f"ALTER TABLE cars ADD COLUMN {col} {typ}"))
        s.commit()

engine = create_engine(


    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

def init_db():
    # Create application tables if they don't exist yet
    SQLModel.metadata.create_all(
        engine,
        tables=[
            Car.__table__,
            Media.__table__,
            ImportJob.__table__,
            Make.__table__,
            Model.__table__,
            Category.__table__,
            Dealership.__table__,
        ],
    )
    ensure_columns()
    # --- ensure cars.lot_number exists for legacy DBs ---
    try:
        from sqlmodel import Session
        with Session(engine) as s:
            rows = s.exec(text("PRAGMA table_info('cars')")).all()
            # rows can be tuples or Row objects depending on SQLAlchemy version
            def colname(r):
                try:
                    return r["name"]
                except Exception:
                    return r[1]
            cols = {colname(r) for r in rows}
            if "lot_number" not in cols:
                s.exec(text("ALTER TABLE cars ADD COLUMN lot_number TEXT"))
    except Exception as e:
        # don't block startup if pragma/alter fails
        print("init_db: lot_number ensure failed:", e)
    # ----------------------------------------------------
    with Session(engine) as s:
        # Ensure cars table has deleted_at column (soft delete)
        pragma = s.exec(text("PRAGMA table_info(cars)")).mappings().all()
        cols = {r['name'] for r in pragma}
        if "deleted_at" not in cols:
            s.exec(text("ALTER TABLE cars ADD COLUMN deleted_at TEXT"))
        # Indices
        s.exec(text("CREATE INDEX IF NOT EXISTS idx_cars_vin ON cars(vin)"))
        s.exec(text("CREATE INDEX IF NOT EXISTS idx_cars_year ON cars(year)"))
        s.exec(text("CREATE INDEX IF NOT EXISTS idx_cars_make ON cars(make)"))
        s.exec(text("CREATE INDEX IF NOT EXISTS idx_cars_model ON cars(model)"))
        s.exec(text("CREATE INDEX IF NOT EXISTS idx_cars_posted_at ON cars(posted_at)"))
        s.exec(text("CREATE INDEX IF NOT EXISTS idx_cars_status ON cars(auction_status)"))
        s.commit()
