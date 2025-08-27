import { Routes, Route, Link, NavLink } from "react-router-dom";
import { createContext, useEffect, useState } from "react";
import Home from "./pages/Home";
import CarDetail from "./pages/CarDetail";
import ErrorBoundary from "./components/ErrorBoundary";
import { getSettings } from "./api";

export const SettingsContext = createContext({
  site_title: "VINFREAK",
  site_tagline: "Discover performance & provenance",
  logo_url: "",
  theme: "dark",
});

export default function App() {
  const [settings, setSettings] = useState({
    site_title: "VINFREAK",
    site_tagline: "Discover performance & provenance",
    logo_url: "",
    theme: "dark",
  });

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        if (s && typeof s === "object") {
          setSettings((prev) => ({ ...prev, ...s }));
          if (s.site_title) document.title = s.site_title;
        }
      } catch (e) {
        console.error("Failed to load settings", e);
      }
    })();
  }, []);

  return (
    <SettingsContext.Provider value={settings}>
      <div className="app">
        <header className="app-header">
          <Link to="/" className="logo">
            {settings.logo_url ? (
              <img src={settings.logo_url} alt={settings.site_title} />
            ) : (
              settings.site_title
            )}
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
      </div>
    </SettingsContext.Provider>
  );
}
