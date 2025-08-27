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
    parts = [p.strip() for p in address.split(",")]
    return parts[0] if parts else None

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

def num_clean(x, float_ok=False):
    if x is None: return None
    s = str(x).replace(",", "").strip()
    if s == "": return None
    try:
        return float(s) if float_ok else int(float(s))
    except:
        return None

def join_list(lst):
    if isinstance(lst, list):
        return " • ".join([str(x).strip() for x in lst if str(x).strip()])
    return None

def normalize(item):
    # core
    title = item.get("title")
    make = item.get("carMark") or item.get("make") or "Porsche"
    model = item.get("model")
    vin = item.get("vin")
    year = item.get("year") or parse_year(title)
    price = num_clean(((item.get("offer") or {}).get("price")), float_ok=True)
    currency = (item.get("offer") or {}).get("currency")

    mileage = num_clean(item.get("mileage"))
    loc = item.get("location") or {}
    address = loc.get("address")
    city = parse_city(address)
    state = parse_state(item.get("status"), address)

    transmission = map_transmission(item.get("transmission"))
    drivetrain = map_drivetrain(item.get("drivetrain"))
    exterior_color = item.get("exteriorColor")
    interior_color = item.get("interiorColor")
    body_type = item.get("bodyStyle") or item.get("bodyStayle")

    seller_type = item.get("sellerType")
    url = item.get("url")
    images = item.get("images") or []
    image_url = images[0] if images else None

    # extra meta
    auction_status = item.get("auctionStatus") or item.get("status")
    end_time = item.get("endTime")
    time_left = item.get("timeLeft")
    number_of_views = num_clean(item.get("numberOfViews"))
    number_of_bids = num_clean(item.get("numberOfBids"))

    # text blocks / lists
    description = item.get("description")
    highlights = item.get("highlights") or join_list(item.get("highlightsList"))
    equipment = item.get("equipment") or join_list(item.get("equipmentList"))
    modifications = join_list(item.get("modificationsList"))
    known_flaws = join_list(item.get("knownFlowsList") or item.get("knownFlawsList"))
    service_history = join_list(item.get("serviceHistoryList"))
    ownership_history = item.get("ownershipHistory")
    seller_notes = item.get("sellerNotes")
    other_items = item.get("otherItems")

    # seller/location
    location_url = loc.get("url")
    seller = item.get("seller") or {}
    seller_name = seller.get("name")
    seller_url = seller.get("url")

    # basic validation for our API
    if not (make and model and year and price is not None):
        return None

    return {
        "vin": vin,
        "make": make,
        "model": model,
        "trim": None,
        "year": int(year),
        "mileage": mileage,
        "price": float(price),
        "currency": currency,
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
        "source": "json_import",
        "url": url,
        "title": title,
        "auction_status": auction_status,
        "end_time": end_time,
        "time_left": time_left,
        "number_of_views": number_of_views,
        "number_of_bids": number_of_bids,
        "description": description,
        "highlights": highlights,
        "equipment": equipment,
        "modifications": modifications,
        "known_flaws": known_flaws,
        "service_history": service_history,
        "ownership_history": ownership_history,
        "seller_notes": seller_notes,
        "other_items": other_items,
        "engine": item.get("engine"),
        "image_url": image_url,
        "images": images,
        "location_address": address,
        "location_url": location_url,
        "seller_name": seller_name,
        "seller_url": seller_url,
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
        print("Usage: python import_from_json.py <path_to_json>")
        sys.exit(1)
    path = sys.argv[1]
    data = json.load(open(path, "r", encoding="utf-8"))
    print(f"Loaded {len(data)} raw items")

    records, skipped = [], 0
    for it in data:
        r = normalize(it)
        if r: records.append(r)
        else: skipped += 1
    print(f"Prepared {len(records)} items, skipped {skipped}.")

    ins = sk = 0
    for batch in chunked(records, 200):
        resp = requests.post(f"{API}/cars/bulk", json=batch, timeout=60)
        if resp.ok:
            res = resp.json()
            ins += res.get("inserted", 0)
            sk  += res.get("skipped", 0)
            print("Batch OK:", res)
        else:
            print("Batch FAILED:", resp.status_code, resp.text[:300])
    print(f"Done. Inserted: {ins}, skipped: {sk}")

if __name__ == "__main__":
    main()
