import asyncio
import pathlib
import sys
import types
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Stub dependencies expected by app.py
settings = types.SimpleNamespace(
    ADMIN_USER="admin",
    ADMIN_PASS="admin",
    DATABASE_URL="sqlite://",
    UPLOAD_DIR="uploads",
    SECRET_KEY="change-me",
)
sys.modules['backend_settings'] = types.SimpleNamespace(settings=settings)

class DummySession:
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def exec(self, *a, **kw):
        class R:
            def all(self): return []
            def first(self): return (0,)
            def one(self): return 0
            def mappings(self): return self
        return R()
    def commit(self):
        pass
    def add(self, *a, **kw):
        pass

sys.modules['sqlmodel'] = types.SimpleNamespace(
    Session=DummySession,
    select=lambda *a, **k: None,
    SQLModel=object,
    create_engine=lambda *a, **k: None,
)
sys.modules['db'] = types.SimpleNamespace(engine=None, init_db=lambda: None)
sys.modules['models'] = types.SimpleNamespace(Car=None, Media=None, ImportJob=None, Setting=None, AdminAudit=None)

# Ensure required directories and template
(ROOT / "static").mkdir(exist_ok=True)
(ROOT / "uploads").mkdir(exist_ok=True)
templates_dir = ROOT / "templates"
if templates_dir.exists():
    shutil.rmtree(templates_dir)
templates_dir.mkdir()
for tmpl in [
    "admin_login.html",
    "admin_index.html",
    "admin_cars.html",
    "admin_settings.html",
    "admin_imports.html",
    "admin_media.html",
    "_base.html",
]:
    shutil.copy(ROOT / "backend" / "templates" / tmpl, templates_dir / tmpl)

sys.path.append(str(ROOT))

from backend.app import (
    admin_login,
    admin_index,
    admin_cars,
    admin_settings,
    admin_imports,
    admin_media,
)  # now import after stubs


class DummyRequest:
    def __init__(self, form, session=None):
        self._form = form
        self.session = session or {}
    async def form(self):
        return self._form


def test_invalid_csrf_token_rejected():
    req = DummyRequest(
        {"username": settings.ADMIN_USER, "password": settings.ADMIN_PASS, "csrf": "bad"},
        session={"csrf_token": "good"},
    )
    resp = asyncio.run(admin_login(req))
    assert resp.status_code == 400
    assert resp.context["error"] == "CSRF token invalid"
    assert "admin" not in req.session
    assert "admin_user" not in req.session


def test_successful_login_sets_admin_user():
    req = DummyRequest(
        {"username": settings.ADMIN_USER, "password": settings.ADMIN_PASS, "csrf": "good"},
        session={"csrf_token": "good"},
    )
    resp = asyncio.run(admin_login(req))
    # Successful login should redirect
    assert resp.status_code == 303
    assert req.session.get("admin") is True
    assert req.session.get("admin_user") == settings.ADMIN_USER


def test_admin_dashboard_returns_template():
    """Ensure authenticated requests render the dashboard template."""
    req = DummyRequest({}, session={"admin_user": settings.ADMIN_USER})
    resp = admin_index(req)
    template = getattr(resp, "template", None)
    assert template and template.name == "admin_index.html"


def test_admin_pages_render_templates():
    req = DummyRequest({}, session={"admin_user": settings.ADMIN_USER})
    # Cars list
    resp_cars = admin_cars(req)
    tmpl_cars = getattr(resp_cars, "template", None)
    assert tmpl_cars and tmpl_cars.name == "admin_cars.html"

    # Settings page
    resp_settings = admin_settings(req)
    tmpl_settings = getattr(resp_settings, "template", None)
    assert tmpl_settings and tmpl_settings.name == "admin_settings.html"

    # Imports page
    resp_imports = admin_imports(req)
    tmpl_imports = getattr(resp_imports, "template", None)
    assert tmpl_imports and tmpl_imports.name == "admin_imports.html"

    # Media page
    resp_media = admin_media(req)
    tmpl_media = getattr(resp_media, "template", None)
    assert tmpl_media and tmpl_media.name == "admin_media.html"
