export default function DealershipLogo({ dealership }) {
  if (!dealership || !dealership.logo_url) return null;
  const url = dealership.logo_url.startsWith('http')
    ? dealership.logo_url
    : dealership.logo_url.startsWith('/')
      ? dealership.logo_url
      : `/logos/${dealership.logo_url}`;
  return (
    <img
      className="dealership-logo"
      src={url}
      alt={dealership.name || 'dealership'}
      title={dealership.name || ''}
    />
  );
}
