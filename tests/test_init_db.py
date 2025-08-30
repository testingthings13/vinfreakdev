import importlib
import sys
import types
from sqlalchemy import text
from sqlmodel import Session


def test_init_db_creates_cars_table(tmp_path, monkeypatch):
    db_file = tmp_path / "cars.db"
    settings = types.SimpleNamespace(
        DATABASE_URL=f"sqlite:///{db_file}",
        ADMIN_DATABASE_URL="sqlite://",
    )
    monkeypatch.setitem(sys.modules, "backend_settings", types.SimpleNamespace(settings=settings))
    import backend.models as real_models
    monkeypatch.setitem(sys.modules, "models", real_models)
    if "backend.db" in sys.modules:
        del sys.modules["backend.db"]
    import backend.db as db
    importlib.reload(db)
    db.init_db()
    assert db_file.exists()
    with Session(db.engine) as s:
        assert s.exec(text("SELECT name FROM sqlite_master WHERE name='cars'")).first()
