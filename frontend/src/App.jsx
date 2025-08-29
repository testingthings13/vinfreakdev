import { Routes, Route, Link, NavLink } from "react-router-dom";
import { createContext, useEffect, useState } from "react";
import Home from "./pages/Home";
import CarDetail from "./pages/CarDetail";
import ErrorBoundary from "./components/ErrorBoundary";
import { getSettings, API_BASE } from "./api";
import { useToast } from "./ToastContext";

export const SettingsContext = createContext({
  site_title: "VINFREAK",
  site_tagline: "Discover performance & provenance",
  logo_url: "",
  theme: "dark",
  contact_email: "",
  default_page_size: 12,
  maintenance_banner: "",
});

export default function App() {
  const [settings, setSettings] = useState({
    site_title: "VINFREAK",
    site_tagline: "Discover performance & provenance",
    logo_url: "",
    theme: "dark",
    contact_email: "",
    default_page_size: 12,
    maintenance_banner: "",
  });

  const { addToast } = useToast();

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        if (s && typeof s === "object") {
          setSettings((prev) => ({ ...prev, ...s }));
          if (s.site_title) document.title = s.site_title;
        }
      } catch (e) {
        addToast("Failed to load settings", "error");
      }
    })();
  }, [addToast]);

  return (
    <SettingsContext.Provider value={settings}>
      <div className="app">
        {settings.maintenance_banner && (
          <div className="banner">{settings.maintenance_banner}</div>
        )}
        <header className="app-header">
          <Link to="/" className="logo">
            {(() => {
              const u = settings.logo_url;
              if (!u) return settings.site_title;
              const src = u.startsWith("http") ? u : `${API_BASE}${u}`;
              return <img src={src} alt={settings.site_title} />;
            })()}
          </Link>
          <nav>
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Cars</NavLink>
          </nav>
        </header>
        <main className="app-main">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/car/:id/*" element={<CarDetail />} />
            </Routes>
          </ErrorBoundary>
        </main>
        {settings.contact_email && (
          <footer className="app-footer">
            <a href={`mailto:${settings.contact_email}`}>{settings.contact_email}</a>
          </footer>
        )}
      </div>
    </SettingsContext.Provider>
  );
}
