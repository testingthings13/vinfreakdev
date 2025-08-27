const BAD_PUBLIC_SOURCE = new Set(["json_import"]);
const isBad = (v) => v === null || v === undefined || v === "" || v === "null" || v === "None";

export function normalizeCar(raw) {
  const id = raw.id ?? raw._id ?? raw.vin ?? raw.lot_number ?? raw.url ?? Math.random().toString(36).slice(2);
  const year = raw.year ?? raw.model_year ?? null;
  const make = raw.make ?? raw.brand ?? raw.manufacturer ?? null;
  const model = raw.model ?? raw.series ?? null;
  const trim = isBad(raw.trim) ? null : raw.trim;
  const title = raw.title || [year, make, model, trim].filter(Boolean).join(" ") || "Car";

  const price = raw.price ?? raw.current_bid ?? raw.buy_now_price ?? null;
  const mileage = raw.mileage ?? raw.odometer ?? null;

  /* ✅ parenthesized to avoid `??` + `||` conflict */
  const location = raw.location ?? ([raw.city, raw.state].filter(Boolean).join(", ") || null);

  const sourceRaw = (raw.source ?? raw.market ?? "").toLowerCase().trim();
  const sourceHidden = BAD_PUBLIC_SOURCE.has(sourceRaw);
  const source = sourceHidden ? "" : sourceRaw;

  const images = [
    raw.main_image, raw.image_url, raw.image, raw.thumbnail, raw.photo_url,
    ...(Array.isArray(raw.images) ? raw.images : [])
  ].filter(Boolean);

  const status = (raw.auction_status || "").toUpperCase();

  return {
    ...raw,
    __id: String(id),
    __title: title,
    __year: year,
    __make: make,
    __model: model,
    __trim: trim,
    __price: price,
    __mileage: mileage,
    __location: location || raw.location || null,
    __source: source,           // never "json_import" in public UI
    __sourceHidden: sourceHidden,
    __images: images,
    __image: images[0] || null,
    __status: status,
  };
}
