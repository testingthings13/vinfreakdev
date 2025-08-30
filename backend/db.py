from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text
from backend_settings import settings
from models import Make, Model, Category, Dealership, Car



def ensure_columns():
    """Idempotently add missing columns (SQLite)."""
    from sqlmodel import Session
    with Session(engine) as s:
        info = s.exec(text("PRAGMA table_info(cars);")).all()
        have = {row[1] for row in info}
        wanted = {
            "lot_number": "TEXT",
            "auction_status": "TEXT",
            "seller_rating": "REAL",
            "seller_reviews": "INTEGER",
            "make_id": "INTEGER",
            "model_id": "INTEGER",
            "category_id": "INTEGER",
            "dealership_id": "INTEGER",
            "seller_type": "TEXT",
            "exterior_color": "TEXT",
            "interior_color": "TEXT",
            "transmission": "TEXT",
            "drivetrain": "TEXT",
            "fuel_type": "TEXT",
            "body_type": "TEXT",
            "end_time": "TEXT",
            "time_left": "TEXT",
            "number_of_views": "INTEGER",
            "number_of_bids": "INTEGER",
            "highlights": "TEXT",
            "equipment": "TEXT",
            "modifications": "TEXT",
            "known_flaws": "TEXT",
            "service_history": "TEXT",
            "ownership_history": "TEXT",
            "seller_notes": "TEXT",
            "other_items": "TEXT",
            "engine": "TEXT",
            "images_json": "TEXT",
            "location_address": "TEXT",
            "location_url": "TEXT",
            "seller_url": "TEXT",
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
    """Initialize application database."""
    # Create tables if they do not already exist.  Previously the ``cars``
    # table was omitted here because the project started with a pre-existing
    # database.  Deployments that began with an empty database therefore
    # never had the ``cars`` table created which meant API calls like
    # ``/cars`` would fail with "no such table: cars".  By including
    # ``Car.__table__`` in the create_all call we ensure the table exists on
    # fresh installs while remaining a no-op when the table is already
    # present.
    SQLModel.metadata.create_all(
        engine,
        tables=[
            Make.__table__,
            Model.__table__,
            Category.__table__,
            Dealership.__table__,
            Car.__table__,
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
