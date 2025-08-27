from secrets import token_urlsafe
import hmac
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional, List
from sqlmodel import Session as DBSession, select
from sqlalchemy import text
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import func

from backend_settings import settings
security = HTTPBasic()

def require_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
):
    if request.session.get("admin_user"):
        return True
    username_ok = hmac.compare_digest(credentials.username or "", settings.ADMIN_USER)
    password_ok = hmac.compare_digest(credentials.password or "", settings.ADMIN_PASS)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

import io, csv, json, os, secrets, time
from db import engine, init_db
from models import Car, Media, ImportJob, Setting, AdminAudit

app = FastAPI(title="Vinfreak Backend")

@app.middleware("http")
async def _force_admin(request, call_next):
    return await call_next(request)

templates = Jinja2Templates(directory="templates")

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# CORS (loose for dev)
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass

@app.on_event("startup")
def on_start():
    init_db()

# -------- helpers: auth/flash/csrf/audit ----------
FAILED_LOGINS = {}  # ip -> [timestamps]

def flash(request: Request, message: str, category: str = "success"):
    request.session.setdefault("flash", []).append({"cat": category, "msg": message})

def pop_flash(request: Request):
    msgs = request.session.get("flash", [])
    request.session["flash"] = []
    return msgs

def get_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for") or request.client.host

def admin_session_required(request: Request):
    if not request.session.get("admin_user"):
        raise HTTPException(status_code=401)
    return True

def csrf_token(request: Request):
    tok = request.session.get("csrf_token")
    if not tok:
        tok = secrets.token_urlsafe(32)
        request.session["csrf_token"] = tok
    return tok

templates.env.globals["csrf_token"] = csrf_token


def _get_csrf_from_form(form: dict) -> str:
    """Accept either 'csrf' or 'csrf_token' field names from the form."""
    return form.get("csrf") or form.get("csrf_token") or ""

def require_csrf(request: Request, token: str):
    if token != request.session.get("csrf_token"):
        raise HTTPException(status_code=400, detail="CSRF token invalid")

def audit(actor: str, action: str, table: str, row_id: str, before: dict|None, after: dict|None, ip: str):
    with DBSession(engine) as s:
        s.add(AdminAudit(
            actor=actor,
            action=action,
            table_name=table,
            row_id=str(row_id),
            before_json=json.dumps(before, ensure_ascii=False) if before else None,
            after_json=json.dumps(after, ensure_ascii=False) if after else None,
            ip=ip,
            created_at=datetime.utcnow().isoformat(),
        ))
        s.commit()

# --------- Auth views ----------
@app.get("/admin/login")
def admin_login_form(request: Request):
    t = csrf_token(request)
    # Render the themed template
    resp = templates.TemplateResponse(
        "admin_login.html", {"request": request, "title": "Login", "csrf": t}
    )
    # Also set a cookie (harmless; keeps some clients happy)
    resp.set_cookie("csrftoken", t, samesite="lax")
    return resp

@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)

# -------- public API used by frontend --------
@app.get("/cars")
def list_cars():
    # ORM first
    try:
        with DBSession(engine) as s:
            stmt = select(Car).where((Car.deleted_at.is_(None)))
            # order by posted_at desc if present else id desc
            order_col = getattr(Car, "posted_at", Car.id)
            cars = s.exec(stmt.order_by(order_col.desc())).all()
            try:
                return [c.model_dump() for c in cars]
            except Exception:
                return [ {k:getattr(c,k,None) for k in ("id","vin","year","make","model","price","currency","source","url","title","description","image_url","posted_at")} for c in cars ]
    except Exception:
        pass
    # raw fallback
    with DBSession(engine) as s:
        rows = s.exec(text("SELECT * FROM cars WHERE deleted_at IS NULL ORDER BY COALESCE(posted_at,'') DESC, id DESC")).mappings().all()
        return [ dict(r) for r in rows ]

@app.get("/cars/{id}")
def get_car(id: str):
    with DBSession(engine) as s:
        # by numeric id or vin/lot_number
        car = None
        if id.isdigit():
            car = s.get(Car, int(id))
        if not car:
            car = s.exec(select(Car).where((Car.vin == id))).first()
        if not car:
            car = s.exec(select(Car).where((Car.lot_number == id))).first()
        if not car or getattr(car, "deleted_at", None):
            return {"detail": "Not found"}
        return car.model_dump() if hasattr(car, "model_dump") else dict(car)

@app.get("/public/settings")
def public_settings():
    with DBSession(engine) as s:
        rows = s.exec(text("SELECT key,value FROM settings")).mappings().all()
        return {r["key"]: r["value"] for r in rows}

# -------- admin UI ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request, _=Depends(admin_session_required)):
    csrf_token(request)
    return templates.TemplateResponse(
        "admin_index.html",
        {"request": request, "title": "Dashboard", "flash": pop_flash(request)},
    )

def allowed_sorts():
    return {"posted_at","id","price","year","mileage","make","model"}

@app.get("/admin/cars", response_class=HTMLResponse)
def admin_cars(
    request: Request,
    page: int = 1, per: int = 25,
    q: Optional[str] = None,
    make: Optional[str] = None,
    status: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    sort: str = "posted_at",
    _=Depends(admin_session_required),
):
    per = max(1, min(per, 100))
    off = (max(1,page)-1)*per
    sort_col = sort if sort in allowed_sorts() else "posted_at"

    where = ["(deleted_at IS NULL OR deleted_at='')"]
    args = {}
    if q:
        where.append("(vin LIKE :q OR make LIKE :q OR model LIKE :q OR title LIKE :q)")
        args["q"] = f"%{q}%"
    if make:
        where.append("make = :make"); args["make"] = make
    if status:
        where.append("auction_status = :status"); args["status"] = status
    if year_min is not None:
        where.append("year >= :ymin"); args["ymin"] = year_min
    if year_max is not None:
        where.append("year <= :ymax"); args["ymax"] = year_max
    where_sql = " AND ".join(where)

    with DBSession(engine) as s:
        total = s.exec(text(f"SELECT COUNT(*) AS c FROM cars WHERE {where_sql}").bindparams(**args)).first()[0]
        rows = s.exec(
            text(f"SELECT * FROM cars WHERE {where_sql} ORDER BY {sort_col} DESC LIMIT :per OFFSET :off").bindparams(**(dict(args, per=per, off=off)))).mappings().all()
    last_page = max(1, (total + per - 1)//per)
    t = csrf_token(request)
    resp = templates.TemplateResponse("admin_cars.html", {
        "request": request, "cars": rows, "q": q or "", "make": make or "", "status": status or "",
        "year_min": year_min, "year_max": year_max, "sort": sort_col, "per": per,
        "page": page, "last_page": last_page, "total": total, "title":"Cars",
        "flash": pop_flash(request)
    })

@app.get("/admin/cars/new", response_class=HTMLResponse)
def admin_car_new(request: Request, _=Depends(admin_session_required)):
    t = csrf_token(request)
    resp = templates.TemplateResponse("admin_car_edit.html", {"request": request, "car": None, "action": "/admin/cars/new", "title":"New Car", "csrf": csrf_token(request), "flash": pop_flash(request)})

@app.post("/admin/cars/new")
def admin_car_create(
    request: Request,
    csrf: str = Form(...),
    vin: str = Form(None), year: int = Form(None), make: str = Form(None), model: str = Form(None), trim: str = Form(None),
    price: float = Form(None), mileage: int = Form(None), currency: str = Form("USD"),
    city: str = Form(None), state: str = Form(None),
    auction_status: str = Form(None), lot_number: str = Form(None), source: str = Form(None),
    url: str = Form(None), title: str = Form(None), image_url: str = Form(None),
    description: str = Form(None), seller_name: str = Form(None), seller_rating: str = Form(None), seller_reviews: str = Form(None),
    posted_at: str = Form(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    allowed = set(Car.model_fields.keys())
    payload = {k:v for k,v in dict(vin=vin, year=year, make=make, model=model, trim=trim, price=price, mileage=mileage, currency=currency,
                                   city=city, state=state, auction_status=auction_status, lot_number=lot_number, source=source,
                                   url=url, title=title, image_url=image_url, description=description, seller_name=seller_name,
                                   seller_rating=seller_rating, seller_reviews=seller_reviews, posted_at=posted_at).items() if k in allowed}
    with DBSession(engine) as s:
        c = Car(**payload)
        s.add(c); s.commit()
        audit(request.session.get("admin_user","admin"), "create", "cars", c.id, None, payload, get_ip(request))
    flash(request, "Car created", "success")
    return RedirectResponse("/admin/cars", status_code=303)

@app.get("/admin/cars/{car_id}", response_class=HTMLResponse)
def admin_car_edit(request: Request, car_id: int, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        car = s.get(Car, car_id)
    t = csrf_token(request)
    resp = templates.TemplateResponse("admin_car_edit.html", {"request": request, "car": car, "action": f"/admin/cars/{car_id}", "title": f"Edit Car {car_id}", "csrf": csrf_token(request), "flash": pop_flash(request)})

@app.post("/admin/cars/{car_id}")
def admin_car_update(
    request: Request, car_id: int,
    csrf: str = Form(...),
    vin: str = Form(None), year: int = Form(None), make: str = Form(None), model: str = Form(None), trim: str = Form(None),
    price: float = Form(None), mileage: int = Form(None), currency: str = Form("USD"),
    city: str = Form(None), state: str = Form(None),
    auction_status: str = Form(None), lot_number: str = Form(None), source: str = Form(None),
    url: str = Form(None), title: str = Form(None), image_url: str = Form(None),
    description: str = Form(None), seller_name: str = Form(None), seller_rating: str = Form(None), seller_reviews: str = Form(None),
    posted_at: str = Form(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    allowed = set(Car.model_fields.keys())
    payload = {k:v for k,v in dict(vin=vin, year=year, make=make, model=model, trim=trim, price=price, mileage=mileage, currency=currency,
                                   city=city, state=state, auction_status=auction_status, lot_number=lot_number, source=source,
                                   url=url, title=title, image_url=image_url, description=description, seller_name=seller_name,
                                   seller_rating=seller_rating, seller_reviews=seller_reviews, posted_at=posted_at).items() if k in allowed}
    with DBSession(engine) as s:
        car = s.get(Car, car_id)
        before = car.model_dump() if hasattr(car,"model_dump") else car.__dict__.copy()
        for k,v in payload.items(): setattr(car,k,v)
        s.add(car); s.commit()
        audit(request.session.get("admin_user","admin"), "update", "cars", car_id, before, payload, get_ip(request))
    flash(request, "Car updated", "success")
    return RedirectResponse("/admin/cars", status_code=303)

@app.get("/admin/cars/{car_id}/delete")
def admin_car_delete(request: Request, car_id: int, _=Depends(admin_session_required)):
    # soft delete
    with DBSession(engine) as s:
        car = s.get(Car, car_id)
        if car:
            before = car.model_dump() if hasattr(car,"model_dump") else None
            car.deleted_at = datetime.utcnow().isoformat()
            s.add(car); s.commit()
            audit(request.session.get("admin_user","admin"), "delete", "cars", car_id, before, {"deleted_at": car.deleted_at}, get_ip(request))
    flash(request, "Car deleted", "success")
    return RedirectResponse("/admin/cars", status_code=303)

# Bulk actions
@app.post("/admin/cars/bulk")
def admin_cars_bulk(request: Request, csrf: str = Form(...), ids: str = Form(...), action: str = Form(...), _=Depends(admin_session_required)):
    require_csrf(request, csrf)
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    with DBSession(engine) as s:
        if action == "delete":
            (
    lambda _ids: (
        (lambda _sql, _params: s.exec(text(_sql).bindparams(**_params)))(
            "UPDATE cars SET deleted_at=:ts WHERE id IN (" + ",".join([f":id{i}" for i,_ in enumerate(_ids)]) + ")",
            dict({"ts": datetime.utcnow().isoformat()}, **{f"id{i}": v for i,v in enumerate(_ids)})
        )
    )
)(id_list)
            flash(request, f"Deleted {len(id_list)} car(s)", "success")
        elif action in ("LIVE","SOLD","RESERVE_NOT_MET","ENDED","DRAFT"):
            (
    lambda _ids: (
        (lambda _sql, _params: s.exec(text(_sql).bindparams(**_params)))(
            "UPDATE cars SET auction_status=:st WHERE id IN (" + ",".join([f":id{i}" for i,_ in enumerate(_ids)]) + ")",
            dict({"st": action}, **{f"id{i}": v for i,v in enumerate(_ids)})
        )
    )
)(id_list)
            flash(request, f"Updated status for {len(id_list)} car(s)", "success")
        s.commit()
    return RedirectResponse("/admin/cars", status_code=303)

# Import/Export
@app.get("/admin/cars/export")
def admin_cars_export(fmt: str = "csv", _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        rows = s.exec(text("SELECT * FROM cars WHERE deleted_at IS NULL ORDER BY COALESCE(posted_at,'') DESC, id DESC")).mappings().all()
    if fmt == "json":
        data = json.dumps([dict(r) for r in rows], ensure_ascii=False).encode("utf-8")
        return StreamingResponse(io.BytesIO(data), media_type="application/json", headers={"Content-Disposition":"attachment; filename=cars.json"})
    # CSV
    buf = io.StringIO()
    if rows:
        fieldnames = list(rows[0].keys())
        w = csv.DictWriter(buf, fieldnames=fieldnames)
        w.writeheader()
        for r in rows: w.writerow(dict(r))
    return StreamingResponse(io.BytesIO(buf.getvalue().encode("utf-8")), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=cars.csv"})

@app.post("/admin/cars/import")
async def admin_cars_import(request: Request, csrf: str = Form(...), file: UploadFile = File(...), _=Depends(admin_session_required)):
    require_csrf(request, csrf)
    content = (await file.read()).decode("utf-8", errors="ignore")
    rdr = csv.DictReader(io.StringIO(content))
    inserted = updated = 0
    cols = set(rdr.fieldnames or [])
    keep = cols & set(Car.model_fields.keys())
    with DBSession(engine) as s:
        for row in rdr:
            data = {k: row.get(k) for k in keep}
            vin = (data.get("vin") or "").strip()
            car = None
            if vin:
                car = s.exec(select(Car).where(Car.vin==vin)).first()
            if car:
                for k,v in data.items(): setattr(car,k,v)
                updated += 1
            else:
                s.add(Car(**data)); inserted += 1
        s.commit()
    flash(request, f"Import done: {inserted} inserted, {updated} updated", "success")
    return RedirectResponse("/admin/cars", status_code=303)

# Settings
@app.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        rows = s.exec(text("SELECT key,value FROM settings")).mappings().all()
    data = {r["key"]: r["value"] for r in rows}
    t = csrf_token(request)
    resp = templates.TemplateResponse("admin_settings.html", {"request": request, "settings": data, "title":"Settings", "csrf": csrf_token(request), "flash": pop_flash(request)})

@app.post("/admin/settings")
async def admin_settings_save(request: Request, csrf: str = Form(...), site_title: str = Form("Vinfreak"), site_tagline: str = Form("Discover performance & provenance"), theme: str = Form("dark"), logo_url: str = Form(""), logo: UploadFile | None = File(None), _=Depends(admin_session_required)):
    require_csrf(request, csrf)
    if logo and logo.filename:
        dest = Path("uploads") / logo.filename
        with dest.open("wb") as f:
            f.write(await logo.read())
        logo_url = f"/uploads/{logo.filename}"
    before = None
    with DBSession(engine) as s:
        # simple upserts
        for k,v in {"site_title":site_title, "site_tagline":site_tagline, "theme":theme, "logo_url":logo_url}.items():
            s.exec(text("INSERT INTO settings(key,value) VALUES(:k,:v) ON CONFLICT(key) DO UPDATE SET value=:v").bindparams(k=k, v=v))
        s.commit()
    flash(request, "Settings saved", "success")
    audit(request.session.get("admin_user","admin"), "settings", "settings", "-", before, {"theme":theme,"logo_url":logo_url}, get_ip(request))
    return RedirectResponse("/admin/settings", status_code=303)


@app.post("/admin/login")
async def admin_login(request: Request):
    form = dict(await request.form())
    token = _get_csrf_from_form(form)
    if token != request.session.get("csrf_token"):
        return templates.TemplateResponse(
            "admin_login.html",
            {
                "request": request,
                "title": "Login",
                "error": "CSRF token invalid",
                "csrf": csrf_token(request),
            },
            status_code=400,
        )

    username = form.get("username", "")
    password = form.get("password", "")
    if username == settings.ADMIN_USER and password == settings.ADMIN_PASS:
        request.session["admin_user"] = username
        request.session["admin"] = True
        request.session["csrf_token"] = token_urlsafe(32)  # rotate token
        return RedirectResponse(url="/admin", status_code=303)

    return templates.TemplateResponse(
        "admin_login.html",
        {
            "request": request,
            "title": "Login",
            "error": "Invalid credentials",
            "csrf": csrf_token(request),
        },
        status_code=400,
    )

@app.get("/admin/seed")
def _admin_seed(request: Request, _=Depends(admin_session_required)):
    """Insert a few demo cars if table is empty, then show a tiny report."""
    from starlette.responses import PlainTextResponse
    try:
        with Session(engine) as s:
            try:
                has = s.exec(select(func.count()).select_from(Car)).one()
            except Exception:
                has = 0
            added = 0
            if not has:
                demo = [
                    Car(vin="DEMO000000000001", make="Honda", model="Civic", trim="EX", year=2018, mileage=42000, price=15900, currency="USD", city="Austin", state="TX", source="seed", title="Demo Honda Civic", description="Seed row", image_url="", seller_name="Demo", lot_number="D1", seller_rating=4.5, seller_reviews=12),
                    Car(vin="DEMO000000000002", make="Toyota", model="Camry", trim="SE", year=2019, mileage=38000, price=17900, currency="USD", city="Denver", state="CO", source="seed", title="Demo Toyota Camry", description="Seed row", image_url="", seller_name="Demo", lot_number="D2", seller_rating=4.7, seller_reviews=20),
                    Car(vin="DEMO000000000003", make="Ford",   model="Focus", trim="SEL", year=2017, mileage=52000, price=9900,  currency="USD", city="Miami",  state="FL", source="seed", title="Demo Ford Focus",  description="Seed row", image_url="", seller_name="Demo", lot_number="D3", seller_rating=4.2, seller_reviews=8),
                ]
                for c in demo:
                    try:
                        s.add(c)
                        added += 1
                    except Exception:
                        pass
                s.commit()
            return PlainTextResponse(f"Seeded: {added} | Total cars now: {has + added}")
    except Exception as e:
        return PlainTextResponse(f"Seed error: {e}", status_code=500)
