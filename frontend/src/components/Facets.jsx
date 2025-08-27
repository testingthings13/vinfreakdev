export default function Facets({ sort, setSort, minYear, setMinYear, maxYear, setMaxYear, source, setSource, sources }) {
  return (
    <div className="facets">
      <label className="f">
        <span>Sort</span>
        <select value={sort} onChange={e=>setSort(e.target.value)}>
          <option value="relevance">Relevance</option>
          <option value="price_desc">Price ↓</option>
          <option value="price_asc">Price ↑</option>
          <option value="year_desc">Year ↓</option>
          <option value="year_asc">Year ↑</option>
          <option value="mileage_asc">Mileage ↑</option>
          <option value="mileage_desc">Mileage ↓</option>
        </select>
      </label>
      <label className="f">
        <span>Min Year</span>
        <input type="number" value={minYear ?? ""} onChange={e=>setMinYear(e.target.value?Number(e.target.value):null)} />
      </label>
      <label className="f">
        <span>Max Year</span>
        <input type="number" value={maxYear ?? ""} onChange={e=>setMaxYear(e.target.value?Number(e.target.value):null)} />
      </label>
      <label className="f">
        <span>Source</span>
        <select value={source} onChange={e=>setSource(e.target.value)}>
          <option value="">All sources</option>
          {sources.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
    </div>
  );
}
