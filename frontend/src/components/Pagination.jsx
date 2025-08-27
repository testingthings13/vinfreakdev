export default function Pagination({ page, setPage, total, pageSize }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const prev = () => setPage(Math.max(1, page-1));
  const next = () => setPage(Math.min(pages, page+1));
  return (
    <div className="pagination">
      <button onClick={prev} disabled={page<=1}>Prev</button>
      <span>Page {page} / {pages}</span>
      <button onClick={next} disabled={page>=pages}>Next</button>
    </div>
  );
}
