from datetime import datetime, timedelta
from typing import List, Any
import csv
from io import StringIO

from sqladmin import ModelView, expose
from wtforms import FileField
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse, HTMLResponse

import os
from uuid import uuid4

from models import Car, Dealership
from backend_settings import settings
from db import engine
from sqlmodel import Session, select, func

def _csv_response(filename: str, rows: List[dict]) -> Response:
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

class CarAdmin(ModelView, model=Car):
    name = "Car"
    name_plural = "Cars"
    icon = "fa-solid fa-car"

    column_list = [Car.id, Car.year, Car.make, Car.model, Car.dealership_id, Car.vin, Car.source, Car.url, Car.created_at]
    column_sortable_list = [Car.year, Car.make, Car.model, Car.created_at, Car.source]
    column_searchable_list = [Car.vin, Car.make, Car.model, Car.source]
    column_default_sort = ("created_at", True)

    column_formatters = {
        Car.url: lambda m, a: f'<a href="{m.url}" target="_blank">Open</a>' if m.url else "",
        Car.source: lambda m, a: f'<span class="badge source {(m.source or "unknown").lower()}">{m.source or "unknown"}</span>',
        Car.dealership_id: lambda m, a: f'<span class="badge dealership">{m.dealership.name}</span>' if m.dealership else "",
    }

    column_filters = [Car.source, Car.make, Car.year, Car.created_at, Car.dealership_id]

    column_labels = {Car.dealership_id: "Dealership"}

    form_columns = [Car.vin, Car.year, Car.make_id, Car.model_id, Car.category_id, Car.trim, Car.price, Car.mileage, Car.currency,
                    Car.city, Car.state, Car.auction_status, Car.lot_number, Car.source, Car.url, Car.title, Car.image_url,
                    Car.description, Car.seller_name, Car.seller_rating, Car.seller_reviews, Car.posted_at, Car.dealership_id]
    form_ajax_refs = {
        "dealership": {
            "fields": (Dealership.name,),
        }
    }

    def _normalize_ids(self, data: dict) -> None:
        for key in ("make_id", "model_id", "category_id", "dealership_id"):
            if data.get(key) in ("", None):
                data[key] = None

    async def insert_model(self, request, data):
        self._normalize_ids(data)
        return await super().insert_model(request, data)

    async def update_model(self, request, pk, data):
        self._normalize_ids(data)
        return await super().update_model(request, pk, data)

    async def action_export_csv(self, ids: List[Any]) -> Response:
        if not ids:
            return PlainTextResponse("No rows selected.", status_code=400)
        with Session(engine) as s:
            items = s.exec(select(Car).where(Car.id.in_(ids))).all()
        rows = [{
            "id": str(i.id),
            "year": i.year,
            "make": i.make,
            "model": i.model,
            "vin": i.vin,
            "source": i.source,
            "url": i.url,
            "created_at": i.created_at.isoformat() if getattr(i, "created_at", None) else ""
        } for i in items]
        return _csv_response("cars_export.csv", rows)

    async def action_delete_selected(self, ids: List[Any]) -> Response:
        if not ids:
            return PlainTextResponse("No rows selected.", status_code=400)
        with Session(engine) as s:
            items = s.exec(select(Car).where(Car.id.in_(ids))).all()
            for i in items:
                s.delete(i)
            s.commit()
        return PlainTextResponse(f"Deleted {len(ids)} item(s).")

    actions = [("Export CSV", "action_export_csv"), ("Delete selected", "action_delete_selected")]


class DealershipAdmin(ModelView, model=Dealership):
    name = "Dealership"
    name_plural = "Dealerships"
    icon = "fa-solid fa-building"

    column_list = [Dealership.id, Dealership.name, Dealership.logo]
    form_columns = [Dealership.name, "logo_file"]
    form_extra_fields = {
        "logo_file": FileField("Logo"),
    }

    async def _handle_logo(self, data: dict):
        file = data.pop("logo_file", None)
        if file and getattr(file, "filename", None):
            upload_dir = settings.UPLOAD_DIR
            os.makedirs(upload_dir, exist_ok=True)
            fname = f"{uuid4().hex}_{file.filename}"
            path = os.path.join(upload_dir, fname)
            content = file.read() if hasattr(file, "read") else await file.read()
            with open(path, "wb") as f:
                f.write(content)
            data["logo"] = fname

    async def insert_model(self, request, data):
        await self._handle_logo(data)
        return await super().insert_model(request, data)

    async def update_model(self, request, pk, data):
        await self._handle_logo(data)
        return await super().update_model(request, pk, data)

class DashboardView(ModelView):
    name = "Dashboard"
    icon = "fa-solid fa-gauge"

    @expose("/dashboard", methods=["GET"])
    async def dashboard(self, request: Request) -> HTMLResponse:
        with Session(engine) as s:
            total = s.exec(select(func.count()).select_from(Car)).one()
            by_source = s.exec(select(Car.source, func.count()).group_by(Car.source)).all()
            since = datetime.utcnow() - timedelta(days=7)
            last7 = s.exec(select(func.count()).where(Car.created_at >= since)).one()

        html = """
        <div class="kpi-grid">
          <div class="kpi"><div class="kpi-label">Total Cars</div><div class="kpi-value">{total}</div></div>
          <div class="kpi"><div class="kpi-label">New (7 days)</div><div class="kpi-value">{last7}</div></div>
        </div>
        <div class="card">
          <h3>By Source</h3>
          <table class="table">
            <thead><tr><th>Source</th><th>Count</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """.format(
            total=total or 0,
            last7=last7 or 0,
            rows="".join(
                f'<tr><td><span class="badge source {(src or "unknown").lower()}">{src or "unknown"}</span></td><td>{cnt}</td></tr>'
                for src, cnt in by_source
            )
        )
        return HTMLResponse(html)
