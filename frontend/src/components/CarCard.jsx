import { useState } from "react";
import { Link } from "react-router-dom";
import SourceLogo from "./SourceLogo";
import Badge from "./Badge";
import { fmtMoney, fmtNum } from "../utils/text";

export default function CarCard({ car }) {
  const [open, setOpen] = useState(false);
  const id = car.__id;
  return (
    <article className={`card glass ${open ? "open" : ""}`}>
      <div className="thumb">
        {car.__image ? <img src={car.__image} alt={car.__title} loading="lazy" /> : <div className="noimg">No Photo</div>}
        {car.__status === "SOLD" && <div className="ribbon">SOLD</div>}
      </div>

      <div className="card-body">
        <div className="card-head">
          <Link to={`/car/${encodeURIComponent(id)}`} className="ctitle">{car.__title}</Link>
          <div className="meta">
            {!car.__sourceHidden && <SourceLogo source={car.__source} />}
          </div>
        </div>

        <div className="brief">
          <span><Badge tone="muted">{car.__year || "—"}</Badge></span>
          <span><Badge tone="muted">{car.__make || "—"}</Badge></span>
          <span><Badge tone="muted">{car.__model || "—"}</Badge></span>
          {car.__trim && <span><Badge tone="muted">{car.__trim}</Badge></span>}
        </div>

        <div className="specrow">
          <div><span className="k">Price</span><span className="v">{fmtMoney(car.__price, car.currency || "USD")}</span></div>
          <div><span className="k">Mileage</span><span className="v">{car.__mileage? `${fmtNum(car.__mileage)} mi`:"—"}</span></div>
          <div><span className="k">Location</span><span className="v">{car.__location || "—"}</span></div>
        </div>

        <div className="actions">
          <Link to={`/car/${encodeURIComponent(id)}`} className="btn primary">Open details</Link>
          <button className="btn ghost" onClick={()=>setOpen(v=>!v)} aria-expanded={open}>{open?"Hide":"More"}</button>
          {car.url && <a className="btn link" href={car.url} target="_blank" rel="noreferrer">Source</a>}
        </div>

        {open && (
          <div className="more">
            {Object.entries(car)
              .filter(([k]) => !k.startsWith("__") && !["images","image","image_url","thumbnail","photo_url","main_image","source"].includes(k))
              .slice(0, 18)
              .map(([k,v]) => <div key={k} className="kv"><span className="k">{k}</span><span className="v">{String(v)}</span></div>)}
          </div>
        )}
      </div>
    </article>
  );
}
