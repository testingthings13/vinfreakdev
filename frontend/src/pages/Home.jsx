import { useEffect, useMemo, useState } from "react";
import { getJSON } from "../lib/api";
import { normalizeCar } from "../utils/normalizeCar";
import { fmtNum, fmtMoney, fmtDate } from "../utils/text";
import SearchBar from "../components/SearchBar";
import Facets from "../components/Facets";
import Chip from "../components/Chip";
import Pagination from "../components/Pagination";
import CarCard from "../components/CarCard";
import SkeletonCard from "../components/SkeletonCard";

const PAGE_SIZE = 12;

export default function Home() {
  const [raw, setRaw] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [q, setQ] = useState("");
  const [sort, setSort] = useState("relevance");
  const [minYear, setMinYear] = useState(null);
  const [maxYear, setMaxYear] = useState(null);
  const [source, setSource] = useState("");

  const [page, setPage] = useState(1);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await getJSON("/cars");
        const list = Array.isArray(data) ? data : (data.items || data.results || []);
        if (!Array.isArray(list)) throw new Error("Backend did not return an array at /cars.");
        setRaw(list.map(normalizeCar));
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const kpis = useMemo(() => {
    if (!raw.length) return null;
    const prices = raw.map(c => c.__price).filter(x => x!=null && !isNaN(Number(x)));
    const avg = prices.length ? (prices.reduce((a,b)=>a+Number(b),0)/prices.length) : null;
    const latest = raw.reduce((acc, c) => acc || c.posted_at, null);
    return { total: raw.length, avgPrice: avg, latest: latest };
  }, [raw]);

  const availableSources = useMemo(() => {
    const s = new Set();
    for (const c of raw) if (c.__source) s.add(c.__source);
    return Array.from(s).sort();
  }, [raw]);

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    const byText = (c) => {
      if (!text) return true;
      const hay = [
        c.__title, c.__make, c.__model, c.__trim, c.__location, c.vin, c.lot_number
      ].filter(Boolean).join(" ").toLowerCase();
      return hay.includes(text);
    };
    const byYear = (c) => (minYear ? (c.__year ?? 0) >= minYear : true) && (maxYear ? (c.__year ?? 9999) <= maxYear : true);
    const bySource = (c) => source ? String(c.__source || "") === source : true;
    return raw.filter(c => byText(c) && byYear(c) && bySource(c));
  }, [raw, q, minYear, maxYear, source]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    const num = (v)=> (v==null||v===""||isNaN(Number(v))) ? Infinity : Number(v);
    const numDesc = (v)=> (v==null||v===""||isNaN(Number(v))) ? -Infinity : Number(v);
    switch (sort) {
      case "price_asc": arr.sort((a,b)=> num(a.__price) - num(b.__price)); break;
      case "price_desc": arr.sort((a,b)=> numDesc(b.__price) - numDesc(a.__price)); break;
      case "year_desc": arr.sort((a,b)=> (b.__year ?? -Infinity) - (a.__year ?? -Infinity)); break;
      case "year_asc": arr.sort((a,b)=> (a.__year ?? Infinity) - (b.__year ?? Infinity)); break;
      case "mileage_asc": arr.sort((a,b)=> num(a.__mileage) - num(b.__mileage)); break;
      case "mileage_desc": arr.sort((a,b)=> numDesc(b.__mileage) - numDesc(a.__mileage)); break;
      case "relevance":
      default: break;
    }
    return arr;
  }, [filtered, sort]);

  const total = sorted.length;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page-1)*PAGE_SIZE;
  const pageItems = sorted.slice(start, start + PAGE_SIZE);
  useEffect(()=>{ setPage(1); }, [q, minYear, maxYear, source, sort]);

  return (
    <div>
      {/* Futuristic hero */}
      <section className="hero">
        <div className="hero-inner">
          <h1>Discover performance & provenance</h1>
          <p className="sub">Search curated listings across enthusiast markets with clean specs and history highlights.</p>
          <div className="kpis">
            <div className="kpi"><span className="k">Total cars</span><span className="v">{kpis? fmtNum(kpis.total):"—"}</span></div>
            <div className="kpi"><span className="k">Avg price</span><span className="v">{kpis? fmtMoney(kpis.avgPrice):"—"}</span></div>
            <div className="kpi"><span className="k">Latest import</span><span className="v">{kpis? fmtDate(kpis.latest):"—"}</span></div>
          </div>
          <SearchBar value={q} onChange={setQ} />
        </div>
      </section>

      {/* Controls */}
      <section className="toolbar-row">
        <Facets
          sort={sort} setSort={setSort}
          minYear={minYear} setMinYear={setMinYear}
          maxYear={maxYear} setMaxYear={setMaxYear}
          source={source} setSource={setSource}
          sources={availableSources}
        />
        <div className="chips">
          {q && <Chip label={`q: ${q}`} onClear={()=>setQ("")} />}
          {minYear!=null && <Chip label={`≥ ${minYear}`} onClear={()=>setMinYear(null)} />}
          {maxYear!=null && <Chip label={`≤ ${maxYear}`} onClear={()=>setMaxYear(null)} />}
          {source && <Chip label={source} onClear={()=>setSource("")} />}
        </div>
        <div className="results">{fmtNum(total)} result{total===1?"":"s"}</div>
      </section>

      {/* Grid */}
      <section className="grid">
        {loading && Array.from({length:12}).map((_,i)=> <SkeletonCard key={i} />)}
        {!loading && !error && pageItems.map(c => <CarCard key={c.__id} car={c} />)}
        {!loading && !error && !total && <div className="state">No cars match your filters.</div>}
        {!loading && error && <div className="state error">Error: {error}</div>}
      </section>

      {!loading && total>PAGE_SIZE && (
        <Pagination page={page} setPage={setPage} total={total} pageSize={PAGE_SIZE} />
      )}
    </div>
  );
}
