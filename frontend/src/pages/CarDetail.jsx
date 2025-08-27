import { useEffect, useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { getJSON } from "../lib/api";
import Gallery from "../components/Gallery";
import SourceLogo from "../components/SourceLogo";
import { fmtMoney, fmtNum, fmtDate, toList } from "../utils/text";

const SHOW_KEYS = [
  ["Year","year"], ["Make","make"], ["Model","model"], ["Trim","trim"],
  ["Body","body_type"], ["Engine","engine"], ["Fuel","fuel_type"], ["Transmission","transmission"],
  ["Drivetrain","drivetrain"], ["Exterior","exterior_color"], ["Interior","interior_color"],
  ["Mileage","mileage"], ["Price","price"], ["Currency","currency"], ["Location","location"],
  ["City","city"], ["State","state"], ["Seller","seller_name"], ["Seller Type","seller_type"],
  ["Auction","auction_status"], ["Lot #","lot_number"], 
  ["Views","number_of_views"], ["Bids","number_of_bids"],
  ["Posted","posted_at"], ["Ends","end_time"],
  ["VIN","vin"] // VIN last, with copy button
];

export default function CarDetail() {
  const { id } = useParams();
  const [car, setCar] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(()=> {
    (async () => {
      try {
        setLoading(true);
        const data = await getJSON(`/cars/${encodeURIComponent(id)}`);
        setCar(data);
      } catch (e) { setError(String(e)); }
      finally { setLoading(false); }
    })();
  }, [id]);

  const images = useMemo(()=> {
    if (!car) return [];
    const imgs = [];
    if (car.main_image) imgs.push(car.main_image);
    if (car.image_url) imgs.push(car.image_url);
    if (car.image) imgs.push(car.image);
    if (car.thumbnail) imgs.push(car.thumbnail);
    if (Array.isArray(car.images)) imgs.push(...car.images);
    return Array.from(new Set(imgs.filter(Boolean)));
  }, [car]);

  const title = useMemo(()=> {
    if (!car) return "";
    const bits = [car.year, car.make, car.model, car.trim].filter(v => v && v !== "null");
    return car.title || bits.join(" ") || "Car";
  }, [car]);

  const sourceHidden = String(car?.source||"").toLowerCase() === "json_import";

  if (loading) return <div className="state">Loading…</div>;
  if (error) return <div className="state error">Error: {error}</div>;
  if (!car) return <div className="state">Not found.</div>;

  const highlights = toList(car.highlights);
  const equipment = toList(car.equipment);
  const modifications = toList(car.modifications);
  const flaws = toList(car.known_flaws);
  const service = toList(car.service_history);
  const notes = toList(car.seller_notes || car.other_items || car.ownership_history);

  const copyVin = async () => {
    try { await navigator.clipboard.writeText(String(car.vin || "")); alert("VIN copied to clipboard"); } catch {}
  };

  return (
    <div className="detail-wrap">
      <nav className="bread"><Link to="/">← Back</Link></nav>

      <header className="detail-hero glass">
        <div className="hero-top">
          <h1>{title}</h1>
          <div className="hero-meta">
            {car.auction_status?.toUpperCase()==="SOLD" && <span className="ribbon sm">SOLD</span>}
            {!sourceHidden && <SourceLogo source={car.source} />}
          </div>
        </div>

        {images.length ? (
          <div className="hero-img">
            <img src={images[0]} alt={title} />
          </div>
        ) : <div className="hero-img noimg">No Image</div>}

        <div className="hero-specs">
          <div className="spec">
            <span className="k">Price</span>
            <span className="v">{fmtMoney(car.price, car.currency || "USD")}</span>
          </div>
          <div className="spec">
            <span className="k">Mileage</span>
            <span className="v">{car.mileage? `${fmtNum(car.mileage)} mi` : "—"}</span>
          </div>
          <div className="spec">
            <span className="k">Location</span>
            <span className="v">{car.location || [car.city, car.state].filter(Boolean).join(", ") || "—"}</span>
          </div>
        </div>

        <div className="hero-actions">
          {car.url && <a className="btn primary" href={car.url} target="_blank" rel="noreferrer">Open source listing</a>}
        </div>
      </header>

      {images.length > 1 && <Gallery images={images.slice(1)} />}

      <section className="glass section">
        <h2>Specifications</h2>
        <div className="spec-grid">
          {SHOW_KEYS.map(([label,key]) => {
            let val = car[key];
            if (key === "price") val = fmtMoney(car.price, car.currency || "USD");
            if (key === "mileage") val = car.mileage ? `${fmtNum(car.mileage)} mi` : null;
            if (key === "posted_at" || key==="end_time") val = fmtDate(val);
            if (!val || val==="null" || val==="None") return null;
            const content = key==="vin"
              ? <span className="v vin">{String(val)} <button className="vin-copy" onClick={copyVin} title="Copy VIN">📋</button></span>
              : <span className="v">{String(val)}</span>;
            return (
              <div className="kv" key={key}>
                <span className="k">{label}</span>
                {content}
              </div>
            );
          })}
        </div>
      </section>

      {car.description && (
        <section className="glass section">
          <h2>Description</h2>
          <p className="prewrap">{car.description}</p>
        </section>
      )}

      {highlights.length>0 && (
        <section className="glass section">
          <h2>Highlights</h2>
          <ul className="bullets">{highlights.map((x,i)=><li key={i}>{x}</li>)}</ul>
        </section>
      )}

      {equipment.length>0 && (
        <section className="glass section">
          <h2>Equipment</h2>
          <ul className="bullets">{equipment.map((x,i)=><li key={i}>{x}</li>)}</ul>
        </section>
      )}

      {modifications.length>0 && (
        <section className="glass section">
          <h2>Modifications</h2>
          <ul className="bullets">{modifications.map((x,i)=><li key={i}>{x}</li>)}</ul>
        </section>
      )}

      {flaws.length>0 && (
        <section className="glass section">
          <h2>Known Flaws</h2>
          <ul className="bullets">{flaws.map((x,i)=><li key={i}>{x}</li>)}</ul>
        </section>
      )}

      {service.length>0 && (
        <section className="glass section">
          <h2>Service History</h2>
          <ul className="bullets">{service.map((x,i)=><li key={i}>{x}</li>)}</ul>
        </section>
      )}

      {notes.length>0 && (
        <section className="glass section">
          <h2>Additional Notes</h2>
          <ul className="bullets">{notes.map((x,i)=><li key={i}>{x}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
