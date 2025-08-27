from datetime import datetime, timedelta
from typing import List, Any
import csv
from io import StringIO

from sqladmin import ModelView, expose
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse, HTMLResponse

from models import Car
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

    column_list = [Car.id, Car.year, Car.make, Car.model, Car.vin, Car.source, Car.url, Car.created_at]
    column_sortable_list = [Car.year, Car.make, Car.model, Car.created_at, Car.source]
    column_searchable_list = [Car.vin, Car.make, Car.model, Car.source]
    column_default_sort = ("created_at", True)

    column_formatters = {
        Car.url: lambda m, a: f'<a href="{m.url}" target="_blank">Open</a>' if m.url else "",
        Car.source: lambda m, a: f'<span class="badge source {(m.source or "unknown").lower()}">{m.source or "unknown"}</span>',
    }

    column_filters = [Car.source, Car.make, Car.year, Car.created_at]

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
