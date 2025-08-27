export default function Gallery({ images }) {
  if (!images || !images.length) return null;
  return (
    <div className="gallery">
      {images.map((src, i) => (
        <img key={i} src={src} alt={`photo ${i+1}`} loading="lazy" className="gallery-img" />
      ))}
    </div>
  );
}
