import { Routes, Route, Link, NavLink } from "react-router-dom";
import Home from "./pages/Home";
import CarDetail from "./pages/CarDetail";
import ErrorBoundary from "./components/ErrorBoundary";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="logo">VINFREAK</Link>
        <nav>
          <NavLink to="/" end className={({isActive}) => isActive ? "active" : ""}>Cars</NavLink>
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
  );
}
