from typing import Optional
from sqlmodel import SQLModel, Field

# NOTE: Car columns mirror existing DB plus optional deleted_at for soft delete.
class Car(SQLModel, table=True):
    __tablename__ = "cars"
    id: int | None = Field(default=None, primary_key=True)
    vin: str | None = None
    make: str | None = None
    model: str | None = None
    trim: str | None = None
    year: int | None = None
    mileage: int | None = None
    price: float | None = None
    currency: str | None = None
    city: str | None = None
    state: str | None = None
    auction_status: str | None = None
    lot_number: str | None = None
    source: str | None = None
    url: str | None = None
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    seller_name: str | None = None
    seller_rating: str | None = None
    seller_reviews: str | None = None
    posted_at: str | None = None
    deleted_at: str | None = None  # soft delete (TEXT ISO8601)

class Media(SQLModel, table=True):
    __tablename__ = "media"
    id: int | None = Field(default=None, primary_key=True)
    filename: str | None = None
    url: str | None = None
    uploaded_at: str | None = None

class ImportJob(SQLModel, table=True):
    __tablename__ = "import_jobs"
    id: int | None = Field(default=None, primary_key=True)
    source: str | None = None
    status: str | None = "queued"
    started_at: str | None = None
    finished_at: str | None = None
    created: str | None = None
    total_items: int | None = 0
    created_items: int | None = 0
    updated_items: int | None = 0
    errors: str | None = None

class Setting(SQLModel, table=True):
    __tablename__ = "settings"
    key: str | None = Field(default=None, primary_key=True)
    value: str | None = None

class AdminAudit(SQLModel, table=True):
    __tablename__ = "admin_audit"
    id: int | None = Field(default=None, primary_key=True)
    actor: str | None = None
    action: str | None = None   # create/update/delete/settings
    table_name: str | None = None
    row_id: str | None = None
    before_json: str | None = None
    after_json: str | None = None
    ip: str | None = None
    created_at: str | None = None  # ISO8601
