import { useState } from "react";

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

  function handleKey(e) { if (e.key === "Enter") submit(); }

  function submit() {
    onChange({
      q: q.trim() || undefined,
      vin: vin.trim() || undefined,
      make: make.trim() || undefined,
      model: model.trim() || undefined,
      yearMin: yearMin ? Number(yearMin) : undefined,
      yearMax: yearMax ? Number(yearMax) : undefined,
      priceMin: priceMin ? Number(priceMin) : undefined,
      priceMax: priceMax ? Number(priceMax) : undefined,
      source: source || undefined,
    });
  }

  function clearAll() {
    setQ(""); setVin(""); setMake(""); setModel("");
    setYearMin(""); setYearMax(""); setPriceMin(""); setPriceMax(""); setSource("");
    onChange({});
  }

  return (
    <div className="filters">
      <input placeholder="Search (free text)" value={q} onChange={e=>setQ(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="VIN" value={vin} onChange={e=>setVin(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="Make" value={make} onChange={e=>setMake(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="Model" value={model} onChange={e=>setModel(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="Year min" value={yearMin} onChange={e=>setYearMin(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="Year max" value={yearMax} onChange={e=>setYearMax(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="Price min" value={priceMin} onChange={e=>setPriceMin(e.target.value)} onKeyDown={handleKey} />
      <input placeholder="Price max" value={priceMax} onChange={e=>setPriceMax(e.target.value)} onKeyDown={handleKey} />
      <select value={source} onChange={e=>setSource(e.target.value)}>
        <option value="">Any source</option>
        <option value="carsandbids">Cars & Bids</option>
      </select>
      <button onClick={submit}>Search</button>
      <button onClick={clearAll}>Clear</button>
    </div>
  );
}
