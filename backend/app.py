from secrets import token_urlsafe
import hmac
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, Response, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
from sqlmodel import Session as DBSession, select
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
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
from admin_db import engine as admin_engine, init_db as init_admin_db
from models import Car, ImportJob, Setting, AdminAudit, Dealership
try:
    from models import Make, Model, Category
except Exception:  # during tests models may be stubbed
    Make = Model = Category = None

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
    init_admin_db()

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

def audit(
    actor: str,
    action: str,
    table: str,
    row_id: str,
    before: dict | None,
    after: dict | None,
    ip: str,
):
    with DBSession(admin_engine) as session:
        session.add(
            AdminAudit(
                actor=actor,
                action=action,
                table_name=table,
                row_id=str(row_id),
                before_json=json.dumps(before, ensure_ascii=False) if before else None,
                after_json=json.dumps(after, ensure_ascii=False) if after else None,
                ip=ip,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.commit()


def _to_int(value):
    """Coerce form values to int or None.

    HTML forms submit empty strings for unselected numeric fields which
    causes Pydantic's integer parsing to fail. This helper gracefully
    converts such values to ``None``.
    """
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None

# --------- Auth views ----------
@app.get("/admin/login")
def admin_login_form(request: Request):
    t = csrf_token(request)
    # Render the themed template
    resp = templates.TemplateResponse(
        request, "admin_login.html", {"title": "Login", "csrf": t}
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
def list_cars(dealership_id: int | None = Query(None)):
    """List cars with optional dealership filtering."""
    if not isinstance(dealership_id, (int, type(None))):
        dealership_id = None
    # ORM first
    try:
        with DBSession(engine) as s:
            stmt = select(Car).where((Car.deleted_at.is_(None)))
            if dealership_id is not None:
                stmt = stmt.where(Car.dealership_id == dealership_id)
            # order by posted_at desc if present else id desc
            order_col = getattr(Car, "posted_at", Car.id)
            cars = s.exec(stmt.order_by(order_col.desc())).all()
            ids = {getattr(c, "dealership_id", None) for c in cars if getattr(c, "dealership_id", None)}
            dealerships = {}
            if ids:
                dealerships = {d.id: d for d in s.exec(select(Dealership).where(Dealership.id.in_(ids))).all()}
            result = []
            for c in cars:
                try:
                    data = c.model_dump()
                except Exception:
                    data = {k: getattr(c, k, None) for k in ("id","vin","year","make","model","price","currency","source","url","title","description","image_url","posted_at","dealership_id")}
                imgs = _parse_images(getattr(c, "images_json", None))
                data["images"] = imgs
                if not data.get("image_url") and imgs:
                    data["image_url"] = imgs[0]
                d = dealerships.get(getattr(c, "dealership_id", None))
                if d:
                    try:
                        data["dealership"] = d.model_dump()
                    except Exception:
                        data["dealership"] = {"id": d.id, "name": d.name, "logo_url": getattr(d, "logo_url", None)}
                else:
                    data["dealership"] = None
                result.append(data)
            return result
    except Exception:
        pass
    # raw fallback
    with DBSession(engine) as s:
        sql = """
            SELECT cars.*, d.id AS d_id, d.name AS d_name, d.logo_url AS d_logo
            FROM cars LEFT JOIN dealerships d ON cars.dealership_id = d.id
            WHERE cars.deleted_at IS NULL
        """
        args = {}
        if dealership_id is not None:
            sql += " AND cars.dealership_id = :dealership_id"
            args["dealership_id"] = dealership_id
        sql += " ORDER BY COALESCE(cars.posted_at,'') DESC, cars.id DESC"
        rows = s.exec(text(sql).bindparams(**args)).mappings().all()
        res = []
        for r in rows:
            car = dict(r)
            d = None
            if r.get("d_id") is not None:
                d = {"id": r["d_id"], "name": r["d_name"], "logo_url": r["d_logo"]}
            car.pop("d_id", None)
            car.pop("d_name", None)
            car.pop("d_logo", None)
            car["dealership"] = d
            imgs = _parse_images(car.get("images_json"))
            car["images"] = imgs
            if not car.get("image_url") and imgs:
                car["image_url"] = imgs[0]
            res.append(car)
        return res

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
            raise HTTPException(status_code=404, detail="Not found")
        try:
            data = car.model_dump()
        except Exception:
            data = {k: getattr(car, k, None) for k in ("id","vin","year","make","model","price","currency","source","url","title","description","image_url","posted_at","dealership_id")}
        d = None
        if getattr(car, "dealership_id", None):
            d = s.get(Dealership, car.dealership_id)
        if d:
            try:
                data["dealership"] = d.model_dump()
            except Exception:
                data["dealership"] = {"id": d.id, "name": d.name, "logo_url": getattr(d, "logo_url", None)}
        else:
            data["dealership"] = None
        imgs = _parse_images(getattr(car, "images_json", None))
        data["images"] = imgs
        if not data.get("image_url") and imgs:
            data["image_url"] = imgs[0]
        return data

@app.get("/dealerships")
def list_dealerships():
    with DBSession(engine) as s:
        ds = s.exec(select(Dealership).order_by(Dealership.name)).all()
        try:
            return [d.model_dump() for d in ds]
        except Exception:
            return [{"id": d.id, "name": d.name, "logo_url": getattr(d, "logo_url", None)} for d in ds]

@app.get("/public/settings")
def public_settings():
    with DBSession(admin_engine) as s:
        rows = s.exec(text("SELECT key,value FROM settings")).mappings().all()
        return {r["key"]: r["value"] for r in rows}

# -------- admin UI ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request, _=Depends(admin_session_required)):
    csrf_token(request)
    return templates.TemplateResponse(
        request,
        "admin_index.html",
        {"title": "Dashboard", "flash": pop_flash(request)},
    )

def allowed_sorts():
    return {"posted_at","id","price","year","mileage","make","model"}


def _maybe_int(val: Optional[str]) -> Optional[int]:
    try:
        return int(val) if val not in (None, "") else None
    except ValueError:
        return None


def _parse_images(value: Optional[str]) -> list[str]:
    """Return a list of image URLs from various textual inputs.

    Accepts JSON arrays, comma-separated strings, or newline separated
    lists. Invalid JSON falls back to splitting on commas/newlines.
    """
    if not value:
        return []
    if isinstance(value, str):
        value = value.strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(x) for x in parsed if x]
        if isinstance(parsed, str):
            return [parsed] if parsed else []
    except Exception:
        pass
    parts = [p.strip() for p in str(value).replace(",", "\n").splitlines() if p.strip()]
    return parts


def _parse_images_form(value: Optional[str]) -> Optional[str]:
    """Normalize image input from admin forms to a JSON string."""
    imgs = _parse_images(value)
    return json.dumps(imgs) if imgs else None

# --- Dealership admin ---
@app.get("/admin/dealerships", response_class=HTMLResponse)
def admin_dealerships(request: Request, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        ds = s.exec(select(Dealership).order_by(Dealership.name)).all()
    return templates.TemplateResponse(
        request,
        "admin_dealerships.html",
        {
            "dealerships": ds,
            "csrf": csrf_token(request),
            "title": "Dealerships",
            "flash": pop_flash(request),
        },
    )

@app.post("/admin/dealerships/new")
def admin_dealership_create(
    request: Request,
    csrf: str = Form(...),
    name: str = Form(...),
    logo: UploadFile | None = File(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    logo_url = None
    if logo and getattr(logo, "filename", ""):
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        fname = f"{token_urlsafe(16)}_{logo.filename}"
        path = Path(settings.UPLOAD_DIR) / fname
        data = logo.file.read()
        with open(path, "wb") as f:
            f.write(data)
        logo_url = f"/uploads/{fname}"
    with DBSession(engine) as s:
        d = Dealership(name=name, logo_url=logo_url)
        s.add(d)
        s.commit()
        audit(
            request.session.get("admin_user", "admin"),
            "create",
            "dealerships",
            d.id,
            None,
            {"name": name, "logo_url": logo_url},
            get_ip(request),
        )
    flash(request, "Dealership added", "success")
    return RedirectResponse("/admin/dealerships", status_code=303)

@app.get("/admin/dealerships/{dealership_id}", response_class=HTMLResponse)
def admin_dealership_edit(request: Request, dealership_id: int, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        d = s.get(Dealership, dealership_id)
    if not d:
        flash(request, "Dealership not found", "error")
        return RedirectResponse("/admin/dealerships", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin_dealership_edit.html",
        {
            "dealership": d,
            "csrf": csrf_token(request),
            "title": "Edit Dealership",
            "flash": pop_flash(request),
        },
    )

@app.post("/admin/dealerships/{dealership_id}")
def admin_dealership_update(
    request: Request,
    dealership_id: int,
    csrf: str = Form(...),
    name: str = Form(...),
    logo: UploadFile | None = File(None),
    remove_logo: bool = Form(False),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    with DBSession(engine) as s:
        d = s.get(Dealership, dealership_id)
        if not d:
            flash(request, "Dealership not found", "error")
            return RedirectResponse("/admin/dealerships", status_code=303)
        before = d.model_dump() if hasattr(d, "model_dump") else {"name": d.name, "logo_url": d.logo_url}
        d.name = name
        if remove_logo and d.logo_url:
            try:
                (Path(settings.UPLOAD_DIR) / Path(d.logo_url).name).unlink()
            except FileNotFoundError:
                pass
            d.logo_url = None
        elif logo and getattr(logo, "filename", ""):
            Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
            # delete previous file if replacing
            if d.logo_url:
                try:
                    (Path(settings.UPLOAD_DIR) / Path(d.logo_url).name).unlink()
                except FileNotFoundError:
                    pass
            fname = f"{token_urlsafe(16)}_{logo.filename}"
            path = Path(settings.UPLOAD_DIR) / fname
            data = logo.file.read()
            with open(path, "wb") as f:
                f.write(data)
            d.logo_url = f"/uploads/{fname}"
        s.add(d)
        s.commit()
        audit(
            request.session.get("admin_user", "admin"),
            "update",
            "dealerships",
            dealership_id,
            before,
            {"name": d.name, "logo_url": d.logo_url},
            get_ip(request),
        )
    flash(request, "Dealership updated", "success")
    return RedirectResponse("/admin/dealerships", status_code=303)

@app.get("/admin/dealerships/{dealership_id}/delete")
def admin_dealership_delete(request: Request, dealership_id: int, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        d = s.get(Dealership, dealership_id)
        if d:
            before = d.model_dump() if hasattr(d, "model_dump") else {"name": d.name, "logo_url": d.logo_url}
            if d.logo_url:
                try:
                    (Path(settings.UPLOAD_DIR) / Path(d.logo_url).name).unlink()
                except FileNotFoundError:
                    pass
            s.delete(d)
            s.commit()
            audit(
                request.session.get("admin_user", "admin"),
                "delete",
                "dealerships",
                dealership_id,
                before,
                None,
                get_ip(request),
            )
    flash(request, "Dealership deleted", "success")
    return RedirectResponse("/admin/dealerships", status_code=303)

@app.get("/admin/cars", response_class=HTMLResponse)
def admin_cars(
    request: Request,
    page: int = 1,
    per: int = 25,
    q: Optional[str] = None,
    make_id: Optional[str] = None,
    car_model_id: Optional[str] = Query(None, alias="model_id"),
    category_id: Optional[str] = None,
    status: Optional[str] = None,
    year_min: Optional[str] = None,
    year_max: Optional[str] = None,
    sort: str = "posted_at",
    _=Depends(admin_session_required),
):
    make_id = _maybe_int(make_id)
    model_id = _maybe_int(car_model_id)
    category_id = _maybe_int(category_id)
    year_min = _maybe_int(year_min)
    year_max = _maybe_int(year_max)

    per = max(1, min(per, 100))
    off = (max(1,page)-1)*per
    sort_col = sort if sort in allowed_sorts() else "posted_at"

    where = ["(deleted_at IS NULL OR deleted_at='')"]
    args = {}
    if q:
        where.append("(vin LIKE :q OR make LIKE :q OR model LIKE :q OR title LIKE :q)")
        args["q"] = f"%{q}%"
    if make_id is not None:
        where.append("make_id = :make_id"); args["make_id"] = make_id
    if model_id is not None:
        where.append("model_id = :model_id"); args["model_id"] = model_id
    if category_id is not None:
        where.append("category_id = :category_id"); args["category_id"] = category_id
    if status:
        where.append("auction_status = :status"); args["status"] = status
    if year_min is not None:
        where.append("year >= :ymin"); args["ymin"] = year_min
    if year_max is not None:
        where.append("year <= :ymax"); args["ymax"] = year_max
    where_sql = " AND ".join(where)

    with DBSession(engine) as s:
        makes = s.exec(select(Make).order_by(Make.name)).all()
        models = s.exec(select(Model).order_by(Model.name)).all()
        categories = s.exec(select(Category).order_by(Category.name)).all()
        dealerships = s.exec(select(Dealership).order_by(Dealership.name)).all()
        total = s.exec(text(f"SELECT COUNT(*) AS c FROM cars WHERE {where_sql}").bindparams(**args)).first()[0]
        rows = s.exec(
            text(
                f"SELECT cars.*, dealerships.name AS dealership_name FROM cars "
                f"LEFT JOIN dealerships ON dealerships.id = cars.dealership_id "
                f"WHERE {where_sql} ORDER BY {sort_col} DESC LIMIT :per OFFSET :off"
            ).bindparams(**(dict(args, per=per, off=off)))
        ).mappings().all()
    last_page = max(1, (total + per - 1)//per)
    t = csrf_token(request)
    resp = templates.TemplateResponse(
        request,
        "admin_cars.html",
        {
            "cars": rows,
            "q": q or "",
            "make_id": make_id,
            "model_id": model_id,
            "category_id": category_id,
            "status": status or "",
            "year_min": year_min,
            "year_max": year_max,
            "sort": sort_col,
            "per": per,
            "makes": makes,
            "models": models,
            "categories": categories,
            "dealerships": dealerships,
            "page": page,
            "last_page": last_page,
            "total": total,
            "title": "Cars",
            "flash": pop_flash(request),
        },
    )
    return resp

@app.get("/admin/cars/new", response_class=HTMLResponse)
def admin_car_new(request: Request, _=Depends(admin_session_required)):
    t = csrf_token(request)
    with DBSession(engine) as s:
        makes = s.exec(select(Make).order_by(Make.name)).all()
        models = s.exec(select(Model).order_by(Model.name)).all()
        categories = s.exec(select(Category).order_by(Category.name)).all()
        dealerships = s.exec(select(Dealership).order_by(Dealership.name)).all()
    resp = templates.TemplateResponse(
        request,
        "admin_car_edit.html",
        {
            "car": None,
            "action": "/admin/cars/new",
            "title": "New Car",
            "csrf": csrf_token(request),
            "makes": makes,
            "models": models,
            "categories": categories,
            "dealerships": dealerships,
            "images_text": "",
            "flash": pop_flash(request),
        },
    )
    return resp

@app.post("/admin/cars/new")
def admin_car_create(
    request: Request,
    csrf: str = Form(...),
    vin: str = Form(None), year: int = Form(None), make_id: str | None = Form(None), car_model_id: str | None = Form(None, alias="model_id"), category_id: str | None = Form(None), trim: str = Form(None),
    price: float = Form(None), mileage: int = Form(None), currency: str = Form("USD"),
    city: str = Form(None), state: str = Form(None),
    auction_status: str = Form(None), lot_number: str = Form(None), source: str = Form(None),
    url: str = Form(None), title: str = Form(None), image_url: str = Form(None), images_input: str = Form(None, alias="images_json"),
    description: str = Form(None), seller_name: str = Form(None), seller_rating: str = Form(None), seller_reviews: str = Form(None),
    posted_at: str = Form(None), dealership_id: str | None = Form(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    allowed = set(Car.model_fields.keys())
    with DBSession(engine) as s:
        make_id_i = _to_int(make_id)
        model_id_i = _to_int(car_model_id)
        category_id_i = _to_int(category_id)
        dealership_id_i = _to_int(dealership_id)
        make_name = s.get(Make, make_id_i).name if make_id_i else None
        model_name = s.get(Model, model_id_i).name if model_id_i else None
        images_json = _parse_images_form(images_input)
        payload = {k:v for k,v in dict(vin=vin, year=year, make=make_name, make_id=make_id_i, model=model_name, model_id=model_id_i, category_id=category_id_i,
                                       trim=trim, price=price, mileage=mileage, currency=currency,
                                       city=city, state=state, auction_status=auction_status, lot_number=lot_number, source=source,
                                       url=url, title=title, image_url=image_url, images_json=images_json, description=description, seller_name=seller_name,
                                       seller_rating=seller_rating, seller_reviews=seller_reviews, posted_at=posted_at, dealership_id=dealership_id_i).items() if k in allowed}
        c = Car(**payload)
        s.add(c)
        s.flush()
        after = c.model_dump() if hasattr(c, "model_dump") else payload
        audit(
            request.session.get("admin_user", "admin"),
            "create",
            "cars",
            c.id,
            None,
            after,
            get_ip(request),
        )
        s.commit()
    flash(request, "Car created", "success")
    return RedirectResponse("/admin/cars", status_code=303)

# Import/Export
@app.get("/admin/cars/export")
def admin_cars_export(fmt: str = "csv", _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        rows = s.exec(
            text(
                "SELECT * FROM cars WHERE deleted_at IS NULL ORDER BY COALESCE(posted_at,'') DESC, id DESC"
            )
        ).mappings().all()
    if fmt == "json":
        data = json.dumps([dict(r) for r in rows], ensure_ascii=False).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=cars.json"},
        )
    # CSV
    buf = io.StringIO()
    if rows:
        fieldnames = list(rows[0].keys())
        w = csv.DictWriter(buf, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(dict(r))
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cars.csv"},
    )


@app.get("/admin/cars/import")
async def admin_cars_import_get():
    return Response("Use POST with a JSON file.", status_code=405)


@app.post("/admin/cars/import")
async def admin_cars_import(
    request: Request,
    csrf: str = Form(...),
    file: UploadFile = File(...),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    content = await file.read()
    try:
        items = json.loads(content)
    except Exception:
        flash(request, "Invalid JSON file", "error")
        return RedirectResponse("/admin/cars", status_code=303)
    if not isinstance(items, list):
        flash(request, "JSON must be an array of objects", "error")
        return RedirectResponse("/admin/cars", status_code=303)

    cols = set(Car.model_fields.keys())
    seen_vins = set()
    inserted = skipped = 0
    with DBSession(engine) as s:
        for item in items:
            if not isinstance(item, dict):
                skipped += 1
                continue

            imgs_val = item.get("images")
            if imgs_val:
                if isinstance(imgs_val, list):
                    imgs = [str(x).strip() for x in imgs_val if x]
                else:
                    imgs = _parse_images(imgs_val)
                seen_urls: set[str] = set()
                unique: list[str] = []
                for url in imgs:
                    if url and url not in seen_urls:
                        unique.append(url)
                        seen_urls.add(url)
                if unique:
                    item["image_url"] = unique[0]
                    item["images_json"] = (
                        json.dumps(unique[1:]) if len(unique) > 1 else None
                    )

            data = {k: item.get(k) for k in cols}
            vin = (data.get("vin") or "").strip()
            if not vin or vin in seen_vins:
                skipped += 1
                continue
            seen_vins.add(vin)
            exists = s.exec(select(Car).where(Car.vin == vin)).first()
            if exists:
                skipped += 1
                continue
            car = Car(**data)
            s.add(car)
            s.flush()
            audit(
                request.session.get("admin_user", "admin"),
                "create",
                "cars",
                car.id,
                None,
                data,
                get_ip(request),
            )
            inserted += 1
        s.commit()
    flash(request, f"Import done: {inserted} inserted, {skipped} skipped", "success")
    return RedirectResponse("/admin/cars", status_code=303)

# Bulk actions
@app.post("/admin/cars/bulk")
def admin_cars_bulk(
    request: Request,
    csrf: str = Form(...),
    ids: str = Form(...),
    action: str = Form(...),
    dealership_id: str | None = Form(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    dealership_id_i = _to_int(dealership_id)
    with DBSession(engine) as s:
        if action == "delete":
            ts = datetime.now(timezone.utc).isoformat()
            for cid in id_list:
                    car = s.get(Car, cid)
                    if car:
                        before = car.model_dump() if hasattr(car, "model_dump") else None
                        car.deleted_at = ts
                        audit(
                            request.session.get("admin_user", "admin"),
                            "delete",
                            "cars",
                            cid,
                            before,
                            {"deleted_at": ts},
                            get_ip(request),
                        )
            flash(request, f"Deleted {len(id_list)} car(s)", "success")
        elif action in ("LIVE", "SOLD", "RESERVE_NOT_MET", "ENDED", "DRAFT"):
            for cid in id_list:
                    car = s.get(Car, cid)
                    if car:
                        before = {"auction_status": car.auction_status}
                        car.auction_status = action
                        audit(
                            request.session.get("admin_user", "admin"),
                            "update",
                            "cars",
                            cid,
                            before,
                            {"auction_status": action},
                            get_ip(request),
                        )
            flash(request, f"Updated status for {len(id_list)} car(s)", "success")
        elif action == "set_dealership" and dealership_id_i:
            for cid in id_list:
                    car = s.get(Car, cid)
                    if car:
                        before = {"dealership_id": car.dealership_id}
                        car.dealership_id = dealership_id_i
                        audit(
                            request.session.get("admin_user", "admin"),
                            "update",
                            "cars",
                            cid,
                            before,
                            {"dealership_id": dealership_id_i},
                            get_ip(request),
                        )
            flash(request, f"Assigned {len(id_list)} car(s)", "success")
        s.commit()
    return RedirectResponse("/admin/cars", status_code=303)

@app.get("/admin/cars/{car_id}", response_class=HTMLResponse)
def admin_car_edit(request: Request, car_id: int, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        car = s.get(Car, car_id)
        makes = s.exec(select(Make).order_by(Make.name)).all()
        models = s.exec(select(Model).order_by(Model.name)).all()
        categories = s.exec(select(Category).order_by(Category.name)).all()
        dealerships = s.exec(select(Dealership).order_by(Dealership.name)).all()
    images_text = ""
    if car and getattr(car, "images_json", None):
        try:
            images_text = "\n".join(json.loads(car.images_json))
        except Exception:
            images_text = car.images_json
    t = csrf_token(request)
    resp = templates.TemplateResponse(
        request,
        "admin_car_edit.html",
        {
            "car": car,
            "action": f"/admin/cars/{car_id}",
            "title": f"Edit Car {car_id}",
            "csrf": csrf_token(request),
            "makes": makes,
            "models": models,
            "categories": categories,
            "dealerships": dealerships,
            "images_text": images_text,
            "flash": pop_flash(request),
        },
    )
    return resp

@app.post("/admin/cars/{car_id}")
def admin_car_update(
    request: Request, car_id: int,
    csrf: str = Form(...),
    vin: str = Form(None), year: int = Form(None), make_id: str | None = Form(None), car_model_id: str | None = Form(None, alias="model_id"), category_id: str | None = Form(None), trim: str = Form(None),
    price: float = Form(None), mileage: int = Form(None), currency: str = Form("USD"),
    city: str = Form(None), state: str = Form(None),
    auction_status: str = Form(None), lot_number: str = Form(None), source: str = Form(None),
    url: str = Form(None), title: str = Form(None), image_url: str = Form(None), images_input: str = Form(None, alias="images_json"),
    description: str = Form(None), seller_name: str = Form(None), seller_rating: str = Form(None), seller_reviews: str = Form(None),
    posted_at: str = Form(None), dealership_id: str | None = Form(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    allowed = set(Car.model_fields.keys())
    with DBSession(engine) as s:
        make_id_i = _to_int(make_id)
        model_id_i = _to_int(car_model_id)
        category_id_i = _to_int(category_id)
        dealership_id_i = _to_int(dealership_id)
        make_name = s.get(Make, make_id_i).name if make_id_i else None
        model_name = s.get(Model, model_id_i).name if model_id_i else None
        images_json = _parse_images_form(images_input)
        payload = {k:v for k,v in dict(vin=vin, year=year, make=make_name, make_id=make_id_i, model=model_name, model_id=model_id_i, category_id=category_id_i,
                                       trim=trim, price=price, mileage=mileage, currency=currency,
                                       city=city, state=state, auction_status=auction_status, lot_number=lot_number, source=source,
                                       url=url, title=title, image_url=image_url, images_json=images_json, description=description, seller_name=seller_name,
                                       seller_rating=seller_rating, seller_reviews=seller_reviews, posted_at=posted_at, dealership_id=dealership_id_i).items() if k in allowed}
        car = s.get(Car, car_id)
        before = car.model_dump() if hasattr(car, "model_dump") else car.__dict__.copy()
        for k, v in payload.items():
            setattr(car, k, v)
        audit(
            request.session.get("admin_user", "admin"),
            "update",
            "cars",
            car_id,
            before,
            payload,
            get_ip(request),
        )
        s.add(car)
        s.commit()
    flash(request, "Car updated", "success")
    return RedirectResponse("/admin/cars", status_code=303)

@app.get("/admin/cars/{car_id}/delete")
def admin_car_delete(request: Request, car_id: int, _=Depends(admin_session_required)):
    # soft delete
    with DBSession(engine) as s:
        car = s.get(Car, car_id)
        if car:
            before = car.model_dump() if hasattr(car, "model_dump") else None
            car.deleted_at = datetime.now(timezone.utc).isoformat()
            audit(
                request.session.get("admin_user", "admin"),
                "delete",
                "cars",
                car_id,
                before,
                {"deleted_at": car.deleted_at},
                get_ip(request),
            )
            s.add(car)
            s.commit()
    flash(request, "Car deleted", "success")
    return RedirectResponse("/admin/cars", status_code=303)

# Imports
@app.get("/admin/imports", response_class=HTMLResponse)
def admin_imports(request: Request, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        jobs = s.exec(
            text("SELECT * FROM import_jobs ORDER BY created DESC")
        ).mappings().all()
    return templates.TemplateResponse(
        request,
        "admin_imports.html",
        {
            "jobs": jobs,
            "title": "Imports",
            "csrf": csrf_token(request),
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/imports/run")
def admin_imports_run(
    request: Request,
    csrf: str = Form(...),
    source: str = Form(...),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    with DBSession(engine) as s:
        job = ImportJob(
            source=source, status="queued", created=datetime.now(timezone.utc).isoformat()
        )
        s.add(job)
        s.flush()
        after = job.model_dump() if hasattr(job, "model_dump") else job.__dict__.copy()
        audit(
            request.session.get("admin_user", "admin"),
            "create",
            "import_jobs",
            job.id,
            None,
            after,
            get_ip(request),
        )
        s.commit()
    flash(request, "Import queued", "success")
    return RedirectResponse("/admin/imports", status_code=303)


@app.get("/admin/imports/{id}", response_class=HTMLResponse)
def admin_import_detail(request: Request, id: int, _=Depends(admin_session_required)):
    with DBSession(engine) as s:
        job = s.get(ImportJob, id)
    if not job:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "admin_import_detail.html",
        {
            "job": job,
            "title": f"Import {id}",
            "csrf": csrf_token(request),
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/imports/{id}/cancel")
def admin_import_cancel(
    request: Request,
    id: int,
    csrf: str = Form(...),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    with DBSession(engine) as s:
        job = s.get(ImportJob, id)
        if not job:
            raise HTTPException(status_code=404)
        if job.status not in ("queued", "running") or job.cancellable is False:
            flash(request, "Job cannot be cancelled", "error")
        else:
            before = job.model_dump() if hasattr(job, "model_dump") else job.__dict__.copy()
            job.status = "cancelled"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            job.cancellable = False
            audit(
                request.session.get("admin_user", "admin"),
                "update",
                "import_jobs",
                id,
                before,
                {
                    "status": "cancelled",
                    "finished_at": job.finished_at,
                    "cancellable": False,
                },
                get_ip(request),
            )
            s.add(job)
            s.commit()
            flash(request, "Job cancelled", "success")
    return RedirectResponse(f"/admin/imports/{id}", status_code=303)

# Settings
@app.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request, _=Depends(admin_session_required)):
    with DBSession(admin_engine) as s:
        rows = s.exec(text("SELECT key,value FROM settings")).mappings().all()
    data = {r["key"]: r["value"] for r in rows}
    t = csrf_token(request)
    resp = templates.TemplateResponse(
        request,
        "admin_settings.html",
        {
            "settings": data,
            "title": "Settings",
            "csrf": csrf_token(request),
            "flash": pop_flash(request),
        },
    )
    return resp

@app.post("/admin/settings")
async def admin_settings_save(
    request: Request,
    csrf: str = Form(...),
    site_title: str = Form("Vinfreak"),
    site_tagline: str = Form("Discover performance & provenance"),
    theme: str = Form("dark"),
    logo_url: str = Form(""),
    contact_email: str = Form(""),
    default_page_size: str = Form("12"),
    maintenance_banner: str = Form(""),
    logo: UploadFile | None = File(None),
    _=Depends(admin_session_required),
):
    require_csrf(request, csrf)
    if logo and logo.filename:
        dest = Path("uploads") / logo.filename
        with dest.open("wb") as f:
            f.write(await logo.read())
        logo_url = f"/uploads/{logo.filename}"
    updates = {
        "site_title": site_title,
        "site_tagline": site_tagline,
        "theme": theme,
        "logo_url": logo_url,
        "contact_email": contact_email,
        "default_page_size": default_page_size,
        "maintenance_banner": maintenance_banner,
    }
    with DBSession(admin_engine) as s:
        before = {
            r["key"]: r["value"]
            for r in s.exec(text("SELECT key,value FROM settings")).mappings().all()
        }
        for k, v in updates.items():
            s.exec(
                text(
                    "INSERT INTO settings(key,value) VALUES(:k,:v) ON CONFLICT(key) DO UPDATE SET value=:v"
                ).bindparams(k=k, v=v)
            )
        audit(
            request.session.get("admin_user", "admin"),
            "settings",
            "settings",
            "-",
            before,
            updates,
            get_ip(request),
        )
        s.commit()
    flash(request, "Settings saved", "success")
    return RedirectResponse("/admin/settings", status_code=303)


@app.post("/admin/login")
async def admin_login(request: Request):
    form = dict(await request.form())
    token = _get_csrf_from_form(form)
    if token != request.session.get("csrf_token"):
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {
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
        request,
        "admin_login.html",
        {
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


# --------- Frontend fallback routes ---------
FRONTEND_BASE = Path(__file__).resolve().parent.parent / "frontend"
_dist_index = FRONTEND_BASE / "dist" / "index.html"
if _dist_index.exists():
    FRONTEND_INDEX = _dist_index
    assets_dir = FRONTEND_INDEX.parent / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")
else:
    FRONTEND_INDEX = FRONTEND_BASE / "index.html"


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    raise HTTPException(status_code=404, detail="Frontend not built")

