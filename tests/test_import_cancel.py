import pathlib, sys, types, importlib

if 'sqlmodel' in sys.modules:
    del sys.modules['sqlmodel']
real_sqlmodel = importlib.import_module("sqlmodel")
sys.modules['sqlmodel'] = real_sqlmodel
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = pathlib.Path(__file__).resolve().parent.parent

settings = types.SimpleNamespace(
    ADMIN_USER="admin",
    ADMIN_PASS="admin",
    DATABASE_URL="sqlite://",
    ADMIN_DATABASE_URL="sqlite://",
    UPLOAD_DIR="uploads",
    SECRET_KEY="test",
)
sys.modules['backend_settings'] = types.SimpleNamespace(settings=settings)
sys.path.append(str(ROOT))

# ensure required directories
(ROOT / "static").mkdir(exist_ok=True)
(ROOT / "uploads").mkdir(exist_ok=True)
(ROOT / "templates").mkdir(exist_ok=True)

# in-memory database and db stub
engine = create_engine("sqlite://", connect_args={"check_same_thread": False})

def _init_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

sys.modules['db'] = types.SimpleNamespace(engine=engine, init_db=_init_db)
sys.modules['admin_db'] = types.SimpleNamespace(engine=engine, init_db=_init_db)
import backend.models as real_models
sys.modules['models'] = real_models
from backend.models import ImportJob, AdminAudit
import importlib
if 'backend.app' in sys.modules:
    del sys.modules['backend.app']
import backend.app as app_module

app_module.engine = engine
app_module.DBSession = Session
app_module.init_db = _init_db
app_module.admin_engine = engine
app_module.init_admin_db = _init_db

# bypass auth and csrf
app_module.require_csrf = lambda *a, **k: None
app_module.admin_session_required = lambda request: True


class DummyRequest:
    def __init__(self):
        self.session = {}
        self.headers = {}
        self.client = types.SimpleNamespace(host="test")


def test_cancel_queued_job_marks_cancelled():
    _init_db()
    with Session(engine) as s:
        job = ImportJob(source="test", status="queued", created="now")
        s.add(job)
        s.commit()
        jid = job.id
    req = DummyRequest()
    resp = app_module.admin_import_cancel(req, jid, csrf="x", _=True)
    assert resp.status_code == 303
    with Session(engine) as s:
        job = s.get(ImportJob, jid)
        assert job.status == "cancelled"
        assert job.cancellable is False
        audit = s.exec(select(AdminAudit).where(AdminAudit.row_id == str(jid))).first()
        assert audit is not None


def test_cancel_finished_job_no_change():
    _init_db()
    with Session(engine) as s:
        job = ImportJob(source="test", status="finished", created="now", cancellable=False)
        s.add(job)
        s.commit()
        jid = job.id
    req = DummyRequest()
    resp = app_module.admin_import_cancel(req, jid, csrf="x", _=True)
    assert resp.status_code == 303
    with Session(engine) as s:
        job = s.get(ImportJob, jid)
        assert job.status == "finished"
