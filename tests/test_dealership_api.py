import pathlib, sys, types, importlib

if 'sqlmodel' in sys.modules:
    del sys.modules['sqlmodel']
real_sqlmodel = importlib.import_module("sqlmodel")
sys.modules['sqlmodel'] = real_sqlmodel
from sqlmodel import SQLModel, Session, create_engine

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
from backend.models import Car, Dealership

if 'backend.app' in sys.modules:
    del sys.modules['backend.app']
import backend.app as app_module

app_module.engine = engine
app_module.DBSession = Session
app_module.init_db = _init_db


def _seed():
    _init_db()
    with Session(engine) as s:
        d1 = Dealership(name="Dealer1", logo_url="logo1")
        d2 = Dealership(name="Dealer2", logo_url="logo2")
        s.add(d1)
        s.add(d2)
        s.commit()
        c1 = Car(vin="VIN1", make="Make1", model="Model1", dealership_id=d1.id)
        c2 = Car(vin="VIN2", make="Make2", model="Model2", dealership_id=d2.id)
        c3 = Car(vin="VIN3", make="Make3", model="Model3")
        s.add(c1)
        s.add(c2)
        s.add(c3)
        s.commit()
        return d1.id, d2.id, c1.id, c2.id, c3.id


def test_list_cars_includes_dealership_and_filter():
    d1_id, d2_id, c1_id, c2_id, c3_id = _seed()
    cars = app_module.list_cars()
    assert len(cars) == 3
    car = next(c for c in cars if c["id"] == c1_id)
    assert car["dealership"] == {"id": d1_id, "name": "Dealer1", "logo_url": "logo1"}
    car = next(c for c in cars if c["id"] == c3_id)
    assert car["dealership"] is None
    cars = app_module.list_cars(dealership_id=d2_id)
    assert len(cars) == 1 and cars[0]["id"] == c2_id


def test_get_car_includes_dealership():
    d1_id, d2_id, c1_id, c2_id, c3_id = _seed()
    car = app_module.get_car(str(c1_id))
    assert car["dealership"] == {"id": d1_id, "name": "Dealer1", "logo_url": "logo1"}
    car = app_module.get_car(str(c3_id))
    assert car["dealership"] is None


def test_list_dealerships():
    d1_id, d2_id, *_ = _seed()
    deals = app_module.list_dealerships()
    names = {d["name"] for d in deals}
    assert names == {"Dealer1", "Dealer2"}


def test_remove_logo_from_dealership():
    d1_id, *_ = _seed()
    upload_dir = ROOT / "uploads"
    upload_dir.mkdir(exist_ok=True)
    old = upload_dir / "old.png"
    old.write_text("x")
    with Session(engine) as s:
        d = s.get(Dealership, d1_id)
        d.logo_url = f"/uploads/{old.name}"
        s.add(d)
        s.commit()
    req = types.SimpleNamespace(
        session={"csrf_token": "tok", "admin_user": "admin"},
        headers={},
        client=types.SimpleNamespace(host="test"),
    )
    app_module.admin_dealership_update(
        req, d1_id, csrf="tok", name="Dealer1", logo=None, remove_logo=True, _=True
    )
    with Session(engine) as s:
        d = s.get(Dealership, d1_id)
        assert d.logo_url is None
    assert not old.exists()
