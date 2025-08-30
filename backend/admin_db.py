from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from backend_settings import settings
from models import Setting, AdminAudit

engine = create_engine(
    settings.ADMIN_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if settings.ADMIN_DATABASE_URL.startswith("sqlite") else {},
)

def init_db():
    SQLModel.metadata.create_all(engine, tables=[Setting.__table__, AdminAudit.__table__])
    with Session(engine) as s:
        defaults = {
            "site_title": "Vinfreak",
            "site_tagline": "Discover performance & provenance",
            "theme": "dark",
            "logo_url": "",
            "contact_email": "",
            "default_page_size": "12",
            "maintenance_banner": "",
        }
        for k, v in defaults.items():
            r = s.exec(text("SELECT key FROM settings WHERE key=:k").bindparams(k=k)).first()
            if not r:
                s.exec(text("INSERT INTO settings(key,value) VALUES (:k,:v)").bindparams(k=k, v=v))
        s.commit()
