export default function SourceLogo({ source }) {
  if (!source) return null;               // hides json_import
  const s = String(source).toLowerCase();
  let fn = null;
  if (s.includes("carsandbids")) fn = "carsandbids.png";
  // add more: if (s.includes("bringatrailer")) fn = "bringatrailer.png";
  if (!fn) return <span className="badge muted">{source}</span>;
  return <img className="source-logo" src={`/logos/${fn}`} alt={source} title={source} />;
}
