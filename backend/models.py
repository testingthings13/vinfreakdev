from typing import ClassVar
from sqlmodel import SQLModel, Field, Relationship
from pydantic import ConfigDict, BaseModel

# Allow "model_*" field names globally
BaseModel.model_config["protected_namespaces"] = ()


class Make(SQLModel, table=True):
    __tablename__ = "makes"
    id: int | None = Field(default=None, primary_key=True)
    name: str


class Model(SQLModel, table=True):
    __tablename__ = "models"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    make_id: int | None = Field(default=None, foreign_key="makes.id")


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: int | None = Field(default=None, primary_key=True)
    name: str


class Dealership(SQLModel, table=True):
    __tablename__ = "dealerships"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    logo_url: str | None = None

    cars: list["Car"] = Relationship(back_populates="dealership")


# NOTE: Car columns mirror existing DB plus optional deleted_at for soft delete.
class Car(SQLModel, table=True):
    __tablename__ = "cars"
    # Allow field names that would otherwise clash with Pydantic protected namespaces
    model_config = ConfigDict(protected_namespaces=())
    id: int | None = Field(default=None, primary_key=True)
    vin: str | None = None
    make: str | None = None
    make_id: int | None = Field(default=None, foreign_key="makes.id")
    model: str | None = None
    model_id: int | None = Field(default=None, foreign_key="models.id")
    category_id: int | None = Field(default=None, foreign_key="categories.id")
    dealership_id: int | None = Field(default=None, foreign_key="dealerships.id")
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

    dealership: Dealership | None = Relationship(back_populates="cars")

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
    cancellable: bool | None = True
    log: str | None = None

class Setting(SQLModel, table=True):
    __tablename__ = "settings"
    key: str | None = Field(default=None, primary_key=True)
    value: str | None = None

    # Known keys
    SITE_TITLE: ClassVar[str] = "site_title"
    SITE_TAGLINE: ClassVar[str] = "site_tagline"
    THEME: ClassVar[str] = "theme"
    LOGO_URL: ClassVar[str] = "logo_url"
    CONTACT_EMAIL: ClassVar[str] = "contact_email"
    DEFAULT_PAGE_SIZE: ClassVar[str] = "default_page_size"
    MAINTENANCE_BANNER: ClassVar[str] = "maintenance_banner"

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
