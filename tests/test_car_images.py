import importlib, pathlib, sys, types, json

real_sqlmodel = importlib.import_module("sqlmodel")
sys.modules["sqlmodel"] = real_sqlmodel
from sqlmodel import SQLModel, Session, create_engine

ROOT = pathlib.Path(__file__).resolve().parent.parent

settings = types.SimpleNamespace(
    ADMIN_USER="admin",
    ADMIN_PASS="admin",
    DATABASE_URL="sqlite://",
    ADMIN_DATABASE_URL="sqlite://",
    UPLOAD_DIR="uploads",
    SECRET_KEY="test",
)
sys.modules["backend_settings"] = types.SimpleNamespace(settings=settings)
sys.path.append(str(ROOT))

# ensure required directories
(ROOT / "static").mkdir(exist_ok=True)
(ROOT / "uploads").mkdir(exist_ok=True)
(ROOT / "templates").mkdir(exist_ok=True)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False})


def _init_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


sys.modules["db"] = types.SimpleNamespace(engine=engine, init_db=_init_db)
sys.modules["admin_db"] = types.SimpleNamespace(engine=engine, init_db=_init_db)
import backend.models as real_models
sys.modules["models"] = real_models
from backend.models import Car

if "backend.app" in sys.modules:
    del sys.modules["backend.app"]
import backend.app as app_module

app_module.engine = engine
app_module.DBSession = Session
app_module.init_db = _init_db
app_module.admin_engine = engine
app_module.init_admin_db = _init_db


def test_images_json_exposed():
    _init_db()
    with Session(engine) as s:
        car = Car(vin="V1", make="M", model="Model", images_json=json.dumps(["a.jpg", "b.jpg"]))
        s.add(car)
        s.commit()
        cid = car.id

    data = app_module.get_car(str(cid))
    assert data["images"] == ["a.jpg", "b.jpg"]
    assert data["image_url"] == "a.jpg"

    lst = app_module.list_cars()
    item = next(c for c in lst if c["id"] == cid)
    assert item["images"] == ["a.jpg", "b.jpg"]
    assert item["image_url"] == "a.jpg"

