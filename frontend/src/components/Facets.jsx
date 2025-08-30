export default function Facets({
  sort, setSort,
  minYear, setMinYear,
  maxYear, setMaxYear,
  minPrice, setMinPrice,
  maxPrice, setMaxPrice,
  dealershipId, setDealershipId,
  dealerships = []
}) {
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
        <span>Min Price</span>
        <input type="number" value={minPrice ?? ""} onChange={e=>setMinPrice(e.target.value?Number(e.target.value):null)} />
      </label>
      <label className="f">
        <span>Max Price</span>
        <input type="number" value={maxPrice ?? ""} onChange={e=>setMaxPrice(e.target.value?Number(e.target.value):null)} />
      </label>
      <label className="f">
        <span>Dealership</span>
        <select value={dealershipId} onChange={e=>setDealershipId(e.target.value)}>
          <option value="">All dealerships</option>
          {dealerships.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </label>
    </div>
  );
}
