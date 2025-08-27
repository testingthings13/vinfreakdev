import { useEffect, useMemo, useState } from "react";

const useDebounced = (value, delay=400) => {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
};

export default function FilterBar({ initial = {}, onChange }) {
  const [q, setQ] = useState(initial.q || "");
  const [vin, setVin] = useState(initial.vin || "");
  const [make, setMake] = useState(initial.make || "");
  const [model, setModel] = useState(initial.model || "");
  const [yearMin, setYearMin] = useState(initial.yearMin || "");
  const [yearMax, setYearMax] = useState(initial.yearMax || "");
  const [priceMin, setPriceMin] = useState(initial.priceMin || "");
  const [priceMax, setPriceMax] = useState(initial.priceMax || "");
  const [source, setSource] = useState(initial.source || "");
  const [sort, setSort] = useState(initial.sort || "relevance");

  const dq = useDebounced(q);
  const dvin = useDebounced(vin);
  const dmake = useDebounced(make);
  const dmodel = useDebounced(model);

  useEffect(() => {
    onChange({
      q: dq || undefined,
      vin: dvin || undefined,
      make: dmake || undefined,
      model: dmodel || undefined,
      yearMin: yearMin ? Number(yearMin) : undefined,
      yearMax: yearMax ? Number(yearMax) : undefined,
      priceMin: priceMin ? Number(priceMin) : undefined,
      priceMax: priceMax ? Number(priceMax) : undefined,
      source: source || undefined,
      sort: sort || undefined,
    });
    // eslint-disable-next-line
  }, [dq, dvin, dmake, dmodel, yearMin, yearMax, priceMin, priceMax, source, sort]);

  function clearAll() {
    setQ(""); setVin(""); setMake(""); setModel("");
    setYearMin(""); setYearMax(""); setPriceMin(""); setPriceMax(""); setSource("");
    setSort("relevance");
    onChange({});
  }

  return (
    <div className="filters">
      <input placeholder="Search…" value={q} onChange={e=>setQ(e.target.value)} />
      <input placeholder="VIN" value={vin} onChange={e=>setVin(e.target.value)} />
      <input placeholder="Make" value={make} onChange={e=>setMake(e.target.value)} />
      <input placeholder="Model" value={model} onChange={e=>setModel(e.target.value)} />
      <input placeholder="Year min" value={yearMin} onChange={e=>setYearMin(e.target.value)} />
      <input placeholder="Year max" value={yearMax} onChange={e=>setYearMax(e.target.value)} />
      <input placeholder="Price min" value={priceMin} onChange={e=>setPriceMin(e.target.value)} />
      <input placeholder="Price max" value={priceMax} onChange={e=>setPriceMax(e.target.value)} />
      <select value={source} onChange={e=>setSource(e.target.value)}>
        <option value="">Any source</option>
        <option value="carsandbids">Cars & Bids</option>
      </select>
      <select value={sort} onChange={e=>setSort(e.target.value)}>
        <option value="relevance">Sort: Relevance</option>
        <option value="price_asc">Sort: Price ↑</option>
        <option value="price_desc">Sort: Price ↓</option>
        <option value="year_desc">Sort: Year ↓</option>
        <option value="year_asc">Sort: Year ↑</option>
        <option value="mileage_asc">Sort: Mileage ↑</option>
        <option value="mileage_desc">Sort: Mileage ↓</option>
      </select>
      <button onClick={clearAll}>Clear</button>
    </div>
  );
}
