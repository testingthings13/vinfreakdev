export const fmtNum = (v, d=0) => {
  if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "—";
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: d });
};
export const fmtMoney = (v, cur="USD") => (v==null? "—" : `${cur==="USD"?"$":""}${fmtNum(v)}`);
export const fmtDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return String(iso);
  return d.toLocaleString();
};
// turn blobs of text or bullet points into list items
export function toList(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val.map(x => String(x)).filter(Boolean);
  const s = String(val).trim();
  const parts = s.split(/\n+|\r+|\u2022|•|\*/g).map(x => x.trim()).filter(Boolean);
  const seen = new Set(); const out = [];
  for (const p of parts) { const k = p.toLowerCase(); if (!seen.has(k)) { seen.add(k); out.push(p); } }
  return out;
}
export const statusLabel = (s) => {
  const t = String(s || "").toUpperCase().replace(/\s+/g,"_");
  switch (t) {
    case "RESERVE_NOT_MET": return "Reserve not met";
    case "SOLD": return "Sold";
    case "LIVE": return "Live";
    case "ENDED": return "Ended";
    default: return s || "—";
  }
};
