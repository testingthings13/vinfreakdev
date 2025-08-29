import pathlib, sys, types, importlib
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = pathlib.Path(__file__).resolve().parent.parent

settings = types.SimpleNamespace(
    ADMIN_USER="admin",
    ADMIN_PASS="admin",
    DATABASE_URL="sqlite://",
    UPLOAD_DIR="uploads",
    SECRET_KEY="test",
)
sys.modules['backend_settings'] = types.SimpleNamespace(settings=settings)
sys.path.append(str(ROOT))

# ensure required directories
(ROOT / "static").mkdir(exist_ok=True)
(ROOT / "uploads").mkdir(exist_ok=True)
(ROOT / "templates").mkdir(exist_ok=True)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False})

def _init_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

sys.modules['db'] = types.SimpleNamespace(engine=engine, init_db=_init_db)
import backend.models as real_models
sys.modules['models'] = real_models
from backend.models import Car, AdminAudit

if 'backend.app' in sys.modules:
    del sys.modules['backend.app']
import backend.app as app_module

app_module.engine = engine
app_module.DBSession = Session
app_module.init_db = _init_db
app_module.require_csrf = lambda *a, **k: None
app_module.admin_session_required = lambda request: True

class DummyClient:
    host = "test"

class DummyRequest:
    def __init__(self):
        self.session = {"admin_user": "tester"}
        self.headers = {}
        self.client = DummyClient()


def test_audit_on_car_create_update_delete():
    _init_db()
    req = DummyRequest()
    resp = app_module.admin_car_create(
        req,
        csrf='x',
        vin='VIN1',
        year=None,
        make_id=None,
        car_model_id=None,
        category_id=None,
        trim=None,
        price=None,
        mileage=None,
        currency='USD',
        city=None,
        state=None,
        auction_status=None,
        lot_number=None,
        source=None,
        url=None,
        title=None,
        image_url=None,
        description=None,
        seller_name=None,
        seller_rating=None,
        seller_reviews=None,
        posted_at=None,
        _=True,
    )
    assert resp.status_code == 303
    with Session(engine) as s:
        car = s.exec(select(Car).where(Car.vin == 'VIN1')).first()
        cid = car.id
        audit = s.exec(select(AdminAudit).where(AdminAudit.action == 'create')).first()
        assert audit is not None and audit.row_id == str(cid)

    req = DummyRequest()
    resp = app_module.admin_car_update(
        req,
        cid,
        csrf='x',
        vin='VIN1',
        year=None,
        make_id=None,
        car_model_id=None,
        category_id=None,
        trim=None,
        price=None,
        mileage=None,
        currency='USD',
        city=None,
        state=None,
        auction_status=None,
        lot_number=None,
        source=None,
        url=None,
        title='New Title',
        image_url=None,
        description=None,
        seller_name=None,
        seller_rating=None,
        seller_reviews=None,
        posted_at=None,
        _=True,
    )
    assert resp.status_code == 303
    with Session(engine) as s:
        audit = s.exec(select(AdminAudit).where(AdminAudit.action == 'update', AdminAudit.row_id == str(cid))).first()
        assert audit is not None and 'New Title' in (audit.after_json or '')

    req = DummyRequest()
    resp = app_module.admin_car_delete(req, cid, _=True)
    assert resp.status_code == 303
    with Session(engine) as s:
        audit = s.exec(select(AdminAudit).where(AdminAudit.action == 'delete', AdminAudit.row_id == str(cid))).first()
        assert audit is not None and 'deleted_at' in (audit.after_json or '')
