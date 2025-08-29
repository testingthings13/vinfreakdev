import { useEffect, useMemo, useState } from "react";
import { getJSON, getDealerships } from "../api";
import { normalizeCar } from "../utils/normalizeCar";
import useDebounce from "../utils/useDebounce";
import SearchBar from "../components/SearchBar";
import SortFilterBar from "../components/SortFilterBar";
import Pagination from "../components/Pagination";
import CarCard from "../components/CarCard";
import { useToast } from "../ToastContext";

const PAGE_SIZE = 12;

export default function CarList() {
  const [raw, setRaw] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  const [q, setQ] = useState("");
  const dq = useDebounce(q, 300);

  const [sort, setSort] = useState("relevance");
  const [minYear, setMinYear] = useState(null);
  const [maxYear, setMaxYear] = useState(null);
  const [dealershipId, setDealershipId] = useState("");
  const [dealerships, setDealerships] = useState([]);

  const [page, setPage] = useState(1);

  // Fetch once
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const [carData, dealerData] = await Promise.all([
          getJSON("/cars"),
          getDealerships(),
        ]);
        const dealerList = Array.isArray(dealerData) ? dealerData : (dealerData.items || dealerData.results || []);
        setDealerships(dealerList);
        const dealerMap = Object.fromEntries(dealerList.map(d => [d.id, d]));
        const list = Array.isArray(carData) ? carData : (carData.items || carData.results || []);
        if (!Array.isArray(list)) throw new Error("Backend did not return an array at /cars.");
        setRaw(list.map(c => ({ ...normalizeCar(c), dealership: dealerMap[c.dealership_id] }))); 
      } catch (e) {
        addToast(String(e), "error");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Filter + search
  const filtered = useMemo(() => {
    const text = dq.trim().toLowerCase();
    const byText = (c) => {
      if (!text) return true;
      const hay = [
        c.__title, c.__make, c.__model, c.__trim, c.__location, c.vin, c.lot_number, c.__source
      ].filter(Boolean).join(" ").toLowerCase();
      return hay.includes(text);
    };
    const byYear = (c) => (minYear ? (c.__year ?? 0) >= minYear : true) && (maxYear ? (c.__year ?? 9999) <= maxYear : true);
    const byDealership = (c) => (dealershipId ? String(c.dealership_id) === String(dealershipId) : true);

    return raw.filter(c => byText(c) && byYear(c) && byDealership(c));
  }, [raw, dq, minYear, maxYear, dealershipId]);

  // Sort
  const sorted = useMemo(() => {
    const arr = [...filtered];
    const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v))) ? Infinity : Number(v);
    const numNullLast = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v))) ? -Infinity : Number(v);

    switch (sort) {
      case "price_asc": arr.sort((a,b)=> num(a.__price) - num(b.__price)); break;
      case "price_desc": arr.sort((a,b)=> numNullLast(b.__price) - numNullLast(a.__price)); break;
      case "year_desc": arr.sort((a,b)=> (b.__year ?? -Infinity) - (a.__year ?? -Infinity)); break;
      case "year_asc": arr.sort((a,b)=> (a.__year ?? Infinity) - (b.__year ?? Infinity)); break;
      case "mileage_asc": arr.sort((a,b)=> num(a.__mileage) - num(b.__mileage)); break;
      case "mileage_desc": arr.sort((a,b)=> numNullLast(b.__mileage) - numNullLast(a.__mileage)); break;
      case "relevance":
      default:
        // keep as-is (backend or original order)
        break;
    }
    return arr;
  }, [filtered, sort]);

  // Pagination
  const total = sorted.length;
  const start = (page - 1) * PAGE_SIZE;
  const pageItems = sorted.slice(start, start + PAGE_SIZE);
  useEffect(() => { setPage(1); }, [dq, minYear, maxYear, dealershipId, sort]);

  if (loading) return <div className="state">Loading cars…</div>;

  return (
    <div className="wrap">
      <div className="topbar">
        <SearchBar value={q} onChange={setQ} />
        <SortFilterBar
          sort={sort} setSort={setSort}
          minYear={minYear} setMinYear={setMinYear}
          maxYear={maxYear} setMaxYear={setMaxYear}
          dealershipId={dealershipId} setDealershipId={setDealershipId}
          dealerships={dealerships}
        />
      </div>

      <div className="meta">{total} result{total===1?"":"s"}</div>

      {total ? (
        <>
          <div className="grid">
            {pageItems.map(c => <CarCard key={c.__id} car={c} />)}
          </div>
          <Pagination page={page} setPage={setPage} total={total} pageSize={PAGE_SIZE} />
        </>
      ) : (
        <div className="state">No cars match your filters.</div>
      )}
    </div>
  );
}
