export function apiBase() {
  return (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "");
}
export async function getJSON(path, {timeoutMs=12000} = {}) {
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : "/" + path}`;
  const ctrl = new AbortController(); const t = setTimeout(()=>ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { headers: { Accept: "application/json" }, signal: ctrl.signal });
    const text = await r.text();
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} • ${text.slice(0,200)}`);
    try { return JSON.parse(text); } catch { throw new Error(`Invalid JSON from ${url}: ${text.slice(0,200)}`); }
  } catch (e) { if (e.name==="AbortError") throw new Error(`Request timed out after ${timeoutMs}ms: ${url}`); throw e; }
  finally { clearTimeout(t); }
}
