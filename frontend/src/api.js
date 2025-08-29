// Unified API helper that supports both array and {items,total,...} responses
const DEFAULT_BASE = (() => {
  const orig = window.location.origin;

})();

// Allow an explicit VITE_API_BASE but fall back to DEFAULT_BASE for empty strings
const BASE = (import.meta.env.VITE_API_BASE || DEFAULT_BASE).replace(/\/+$/, "");

// Generic JSON fetch with timeout
export async function getJSON(path, { timeoutMs = 12000 } = {}) {
  const url = `${BASE}${path.startsWith("/") ? path : "/" + path}`;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: ctrl.signal,
    });
    const text = await res.text();
    if (!res.ok)
      throw new Error(`${res.status} ${res.statusText} • ${text.slice(0, 200)}`);
    try {
      return JSON.parse(text);
    } catch {
      throw new Error(`Invalid JSON from ${url}: ${text.slice(0, 200)}`);
    }
  } catch (e) {
    if (e.name === "AbortError")
      throw new Error(`Request timed out after ${timeoutMs}ms: ${url}`);
    throw e;
  } finally {
    clearTimeout(t);
  }
}

// Fetch global site settings exposed by the backend
export function getSettings() {
  return getJSON("/public/settings");
}

// Fetch dealerships list
export function getDealerships() {
  return getJSON("/dealerships");
}

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
