import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Paths
db_path = Path("cars.db")   # keep the old DB
json_path = Path("carsandbids.json")

# Load JSON
data = json.loads(json_path.read_text(encoding="utf-8"))

# Connect to existing SQLite
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Make sure table exists
cur.execute("""
CREATE TABLE IF NOT EXISTS cars (
    vin TEXT PRIMARY KEY,
    make TEXT,
    model TEXT,
    trim TEXT,
    year INTEGER,
    mileage INTEGER,
    price REAL,
    city TEXT,
    state TEXT,
    seller_type TEXT,
    exterior_color TEXT,
    interior_color TEXT,
    transmission TEXT,
    drivetrain TEXT,
    fuel_type TEXT,
    body_type TEXT,
    posted_at TEXT,
    image_url TEXT,
    source TEXT,
    url TEXT
)
""")

# Insert new dataset
for car in data:
    cur.execute("""
    INSERT OR REPLACE INTO cars (
        vin, make, model, trim, year, mileage, price, city, state, seller_type,
        exterior_color, interior_color, transmission, drivetrain, fuel_type,
        body_type, posted_at, image_url, source, url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        car.get("vin"),
        car.get("make"),
        car.get("model"),
        car.get("trim"),
        car.get("year"),
        car.get("mileage"),
        car.get("price"),
        car.get("city"),
        car.get("state"),
        car.get("seller_type"),
        car.get("exterior_color"),
        car.get("interior_color"),
        car.get("transmission"),
        car.get("drivetrain"),
        car.get("fuel_type"),
        car.get("body_type"),
        car.get("posted_at", datetime.utcnow().isoformat()),
        car.get("image_url"),
        car.get("source", "imported"),
        car.get("url")
    ))

conn.commit()
conn.close()

print(f"✅ Added/updated {len(data)} cars into {db_path}")

