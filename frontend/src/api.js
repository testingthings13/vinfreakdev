// Unified API helper that supports both array and {items,total,...} responses
const BASE = (import.meta.env.VITE_API_BASE ?? window.location.origin).replace(/\/+$/, "");

// Map filters -> URLSearchParams
function toParams(filters = {}, paging = {}) {
  const p = new URLSearchParams();
  const { page = 1, pageSize = 24, limit, offset } = paging;
  if (limit != null || offset != null) {
    if (limit != null) p.set("limit", String(limit));
    if (offset != null) p.set("offset", String(offset));
  } else {
    p.set("page", String(page));
    p.set("page_size", String(pageSize));
  }

  // Filters
  if (filters.q) p.set("q", filters.q);
  if (filters.vin) p.set("vin", filters.vin);
  if (filters.make) p.set("make", filters.make);
  if (filters.model) p.set("model", filters.model);
  if (filters.yearMin) p.set("year_min", String(filters.yearMin));
  if (filters.yearMax) p.set("year_max", String(filters.yearMax));
  if (filters.priceMin) p.set("price_min", String(filters.priceMin));
  if (filters.priceMax) p.set("price_max", String(filters.priceMax));
  if (filters.source) p.set("source", filters.source);
  if (filters.sort) p.set("sort", filters.sort); // pass-through sort key

  return p;
}

// Fetch one page
export async function getCars(filters = {}, paging = {}) {
  const url = new URL(`${BASE}/cars`);
  url.search = toParams(filters, paging).toString();
  const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`GET /cars ${res.status}`);
  const data = await res.json();
  if (Array.isArray(data)) return { items: data, total: data.length, page: paging.page ?? 1, pageSize: paging.pageSize ?? data.length };
  const items = Array.isArray(data.items) ? data.items : [];
  const total = typeof data.total === "number" ? data.total : items.length;
  return { items, total, page: data.page ?? paging.page ?? 1, pageSize: data.page_size ?? paging.pageSize ?? items.length };
}
