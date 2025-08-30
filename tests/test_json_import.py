import pathlib, sys, types, importlib, io, json, asyncio

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

(ROOT / "static").mkdir(exist_ok=True)
(ROOT / "uploads").mkdir(exist_ok=True)
(ROOT / "templates").mkdir(exist_ok=True)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False})


def _init_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


sys.modules['db'] = types.SimpleNamespace(engine=engine, init_db=_init_db)
sys.modules['admin_db'] = types.SimpleNamespace(engine=engine, init_db=_init_db)
import backend.models as real_models
sys.modules['models'] = real_models
from backend.models import Car

if 'backend.app' in sys.modules:
    del sys.modules['backend.app']
import backend.app as app_module

app_module.engine = engine
app_module.DBSession = Session
app_module.init_db = _init_db
app_module.admin_engine = engine
app_module.init_admin_db = _init_db


class DummyRequest:
    def __init__(self):
        self.session = {"csrf_token": "tok", "admin_user": "admin"}
        self.headers = {}
        self.client = types.SimpleNamespace(host="test")


def test_json_import_skips_duplicates():
    _init_db()
    with Session(engine) as s:
        s.add(Car(vin="EXIST1", make="M", model="X"))
        s.commit()

    data = [
        {"vin": "NEW1", "make": "A", "model": "B"},
        {"vin": "EXIST1", "make": "C", "model": "D"},
        {"vin": "NEW1", "make": "E", "model": "F"},
    ]

    upload = app_module.UploadFile(filename="cars.json", file=io.BytesIO(json.dumps(data).encode("utf-8")))
    req = DummyRequest()

    asyncio.run(app_module.admin_cars_import(req, csrf="tok", file=upload, _=True))

    with Session(engine) as s:
        vins = [c.vin for c in s.exec(select(Car)).all()]
    assert vins.count("EXIST1") == 1
    assert vins.count("NEW1") == 1


def test_json_import_uses_images_field_for_hero_and_gallery():
    _init_db()
    data = [
        {
            "vin": "V1",
            "make": "M",
            "model": "X",
            "images": ["hero.jpg", "gallery1.jpg", "hero.jpg", "gallery2.jpg"],
        }
    ]
    upload = app_module.UploadFile(
        filename="cars.json", file=io.BytesIO(json.dumps(data).encode("utf-8"))
    )
    req = DummyRequest()
    asyncio.run(app_module.admin_cars_import(req, csrf="tok", file=upload, _=True))
    with Session(engine) as s:
        car = s.exec(select(Car)).first()
        assert car.image_url == "hero.jpg"
        assert json.loads(car.images_json) == ["gallery1.jpg", "gallery2.jpg"]
