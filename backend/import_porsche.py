import sys, json, re, requests

API = "http://127.0.0.1:8000"

def parse_year(title, fallback=None):
    m = re.match(r'^\s*(\d{4})\b', title or "")
    return int(m.group(1)) if m else fallback

def parse_state(status, address):
    if status:
        m = re.search(r'\(([A-Z]{2})\)', status)
        if m: return m.group(1)
    if address:
        m = re.search(r'\b([A-Z]{2})\b', address)
        if m: return m.group(1)
    return None

def parse_city(address):
    if not address: return None
    return address.split(",")[0].strip() or None

def map_drivetrain(s):
    if not s: return None
    s = s.lower()
    if "rear" in s: return "RWD"
    if "front" in s: return "FWD"
    if "all" in s: return "AWD"
    if "4-wheel" in s or "4wd" in s or "four" in s: return "4WD"
    return None

def map_transmission(s):
    if not s: return None
    s = s.lower()
    if "manual" in s: return "manual"
    if "auto" in s: return "automatic"
    return s

def map_body_type(obj):
    bt = obj.get("bodyStayle") or obj.get("bodyStyle")
    return bt.lower() if isinstance(bt, str) else None

def map_price(obj):
    offer = obj.get("offer") or {}
    price = offer.get("price")
    try:
        return float(str(price).replace(",", "")) if price is not None else None
    except:
        return None

def map_image(obj):
    imgs = obj.get("images") or []
    return imgs[0] if imgs else None

def join_list(lst):
    if isinstance(lst, list):
        return " • ".join([str(x).strip() for x in lst if str(x).strip()])
    return None

def normalize(item):
    title = item.get("title") or ""
    make = item.get("carMark") or item.get("make") or "Porsche"
    model = item.get("model")
    vin = item.get("vin")
    year = item.get("year") or parse_year(title)
    price = map_price(item)

    mileage = item.get("mileage")
    loc = item.get("location") or {}
    address = loc.get("address")
    city = parse_city(address)
    state = parse_state(item.get("status"), address)
    transmission = map_transmission(item.get("transmission"))
    drivetrain = map_drivetrain(item.get("drivetrain"))
    exterior_color = item.get("exteriorColor")
    interior_color = item.get("interiorColor")
    body_type = map_body_type(item)
    seller_type = item.get("sellerType")
    image_url = map_image(item)
    url = item.get("url")

    # extras
    engine = item.get("engine")
    description = item.get("description")
    highlights = join_list(item.get("highlightsList"))
    equipment = join_list(item.get("equipmentList"))
    service_history = join_list(item.get("serviceHistoryList"))
    ownership_history = item.get("ownershipHistory")
    seller_notes = item.get("sellerNotes")
    auction_status = item.get("auctionStatus") or item.get("status")
    end_time = item.get("endTime")

    # trim guess from title
    trim = None
    if make and model and title:
        t = re.sub(r'^\s*\d{4}\s+', '', title)
        t = re.sub(fr'^{re.escape(make)}\s+', '', t, flags=re.I)
        t = re.sub(fr'^{re.escape(model)}\s*', '', t, flags=re.I).strip(" -–:|")
        trim = t if t and len(t) <= 60 else None

    if not (make and model and year and price is not None):
        return None

    # normalize mileage (e.g., "12,345")
    m_val = None
    if isinstance(mileage, (int, float)):
        m_val = int(mileage)
    elif isinstance(mileage, str):
        s = mileage.replace(",", "").strip()
        if s.isdigit():
            m_val = int(s)

    return {
        "vin": vin,
        "make": "Porsche",  # force Porsche
        "model": model,
        "trim": trim,
        "year": int(year),
        "mileage": m_val,
        "price": price,
        "city": city,
        "state": state,
        "seller_type": seller_type,
        "exterior_color": exterior_color,
        "interior_color": interior_color,
        "transmission": transmission,
        "drivetrain": drivetrain,
        "fuel_type": None,
        "body_type": body_type,
        "posted_at": None,
        "image_url": image_url,
        "source": "carsandbids",
        "url": url,
        "engine": engine,
        "description": description,
        "highlights": highlights,
        "equipment": equipment,
        "service_history": service_history,
        "ownership_history": ownership_history,
        "seller_notes": seller_notes,
        "auction_status": auction_status,
        "end_time": end_time,
    }

def chunked(seq, n):
    buf = []
    for x in seq:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_porsche.py <path_to_json>")
        sys.exit(1)
    path = sys.argv[1]
    data = json.load(open(path, "r", encoding="utf-8"))
    print(f"Loaded {len(data)} raw items")

    records, skipped = [], 0
    for it in data:
        row = normalize(it)
        if row: records.append(row)
        else: skipped += 1
    print(f"Prepared {len(records)} items, skipped {skipped} (missing fields).")

    total_inserted = total_skipped = 0
    for batch in chunked(records, 200):
        r = requests.post(f"{API}/cars/bulk", json=batch, timeout=60)
        if r.ok:
            res = r.json()
            total_inserted += res.get("inserted", 0)
            total_skipped += res.get("skipped", 0)
            print("Batch OK:", res)
        else:
            print("Batch FAILED:", r.status_code, r.text[:400])
    print(f"Done. Inserted: {total_inserted}, skipped: {total_skipped}")

if __name__ == "__main__":
    main()
