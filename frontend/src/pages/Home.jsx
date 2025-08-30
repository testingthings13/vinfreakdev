import { useContext, useEffect, useMemo, useState } from "react";
import { getCars, getDealerships } from "../api";
import { normalizeCar } from "../utils/normalizeCar";
import { fmtNum, fmtMoney, fmtDate } from "../utils/text";
import SearchBar from "../components/SearchBar";
import Facets from "../components/Facets";
import Chip from "../components/Chip";
import Pagination from "../components/Pagination";
import CarCard from "../components/CarCard";
import SkeletonCard from "../components/SkeletonCard";
import { SettingsContext } from "../App";
import { useToast } from "../ToastContext";

export default function Home() {
  const [raw, setRaw] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const { addToast } = useToast();

  const [q, setQ] = useState("");
  const [sort, setSort] = useState("relevance");
  const [minYear, setMinYear] = useState(null);
  const [maxYear, setMaxYear] = useState(null);
  const [minPrice, setMinPrice] = useState(null);
  const [maxPrice, setMaxPrice] = useState(null);
  const [dealershipId, setDealershipId] = useState("");
  const [dealerships, setDealerships] = useState([]);
  const [dealerMap, setDealerMap] = useState({});
  const [total, setTotal] = useState(0);

  const [page, setPage] = useState(1);
  const settings = useContext(SettingsContext);
  const PAGE_SIZE = Number(settings.default_page_size) || 12;
  // Load dealerships once
  useEffect(() => {
    (async () => {
      try {
        const dealerData = await getDealerships();
        const dealerList = Array.isArray(dealerData)
          ? dealerData
          : dealerData.items || dealerData.results || [];
        setDealerships(dealerList);
        setDealerMap(Object.fromEntries(dealerList.map((d) => [d.id, d])));
      } catch (e) {
        setHasError(true);
        addToast(String(e), "error");
      }
    })();
  }, []);

  // Load cars whenever filters/pagination change
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setHasError(false);
        const carData = await getCars(
          {
            q: q || undefined,
            sort,
            yearMin: minYear || undefined,
            yearMax: maxYear || undefined,
            priceMin: minPrice || undefined,
            priceMax: maxPrice || undefined,
            dealershipId: dealershipId || undefined,
          },
          { page, pageSize: PAGE_SIZE }
        );
        const list = Array.isArray(carData.items)
          ? carData.items
          : Array.isArray(carData)
          ? carData
          : carData.results || [];
        if (!Array.isArray(list))
          throw new Error("Backend did not return an array at /cars.");
        setRaw(list);
        setTotal(carData.total || list.length);
      } catch (e) {
        setHasError(true);
        addToast(String(e), "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [q, sort, minYear, maxYear, minPrice, maxPrice, dealershipId, page, PAGE_SIZE]);

  const cars = useMemo(
    () => raw.map((c) => ({ ...normalizeCar(c), dealership: dealerMap[c.dealership_id] })),
    [raw, dealerMap]
  );

  const kpis = useMemo(() => {
    if (!cars.length && !total) return null;
    const prices = cars.map(c => c.__price).filter(x => x!=null && !isNaN(Number(x)));
    const avg = prices.length ? (prices.reduce((a,b)=>a+Number(b),0)/prices.length) : null;
    const latest = cars.reduce((acc, c) => acc || c.posted_at, null);
    return { total, avgPrice: avg, latest: latest };
  }, [cars, total]);

  useEffect(()=>{ setPage(1); }, [q, minYear, maxYear, minPrice, maxPrice, dealershipId, sort, PAGE_SIZE]);

  return (
    <div>
      {/* Futuristic hero */}
      <section className="hero">
        <div className="hero-inner">
          <h1>{settings.site_tagline || "Discover performance & provenance"}</h1>
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
          minPrice={minPrice} setMinPrice={setMinPrice}
          maxPrice={maxPrice} setMaxPrice={setMaxPrice}
          dealershipId={dealershipId} setDealershipId={setDealershipId}
          dealerships={dealerships}
        />
        <div className="chips">
          {q && <Chip label={`q: ${q}`} onClear={()=>setQ("")} />}
          {minYear!=null && <Chip label={`≥ ${minYear}`} onClear={()=>setMinYear(null)} />}
          {maxYear!=null && <Chip label={`≤ ${maxYear}`} onClear={()=>setMaxYear(null)} />}
          {minPrice!=null && <Chip label={`≥ ${fmtMoney(minPrice)}`} onClear={()=>setMinPrice(null)} />}
          {maxPrice!=null && <Chip label={`≤ ${fmtMoney(maxPrice)}`} onClear={()=>setMaxPrice(null)} />}
          {dealershipId && (
            <Chip
              label={dealerships.find(d => String(d.id) === String(dealershipId))?.name || dealershipId}
              onClear={() => setDealershipId("")}
            />
          )}
        </div>
        <div className="results">{fmtNum(total)} result{total===1?"":"s"}</div>
      </section>

      {/* Grid */}
      <section className="grid">
        {loading && Array.from({length:PAGE_SIZE}).map((_,i)=> <SkeletonCard key={i} />)}
        {!loading && !hasError && cars.map(c => <CarCard key={c.__id} car={c} />)}
        {!loading && !hasError && !cars.length && <div className="state">No cars match your filters.</div>}
      </section>

      {!loading && total>PAGE_SIZE && (
        <Pagination page={page} setPage={setPage} total={total} pageSize={PAGE_SIZE} />
      )}
    </div>
  );
}
