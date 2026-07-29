import { useCallback, useEffect, useRef, useState } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import UploadDialog from "./components/UploadDialog";
import AnalyticsPage from "./pages/AnalyticsPage";
import ContentPage from "./pages/ContentPage";
import DashboardPage from "./pages/DashboardPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import VideoDetailPage from "./pages/VideoDetailPage";
import useMediaQuery from "./useMediaQuery";

export default function App() {
  const [mini, setMini] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [toastMsg, setToastMsg] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "dark");
  const toastTimer = useRef(null);
  const location = useLocation();

  // Below this width the sidebar becomes an overlay drawer instead of a rail.
  const isCompact = useMediaQuery("(max-width: 899px)");

  // Dark is the default; the stamp on <html> drives every token in styles.css.
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Close the mobile drawer on navigation and whenever we grow back to desktop.
  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);
  useEffect(() => { if (!isCompact) setDrawerOpen(false); }, [isCompact]);

  // Escape closes the drawer.
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e) => e.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  const toast = useCallback((msg) => {
    setToastMsg(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMsg(null), 3200);
  }, []);

  // One button, two jobs: collapse the rail on desktop, open the drawer on mobile.
  const onMenu = () =>
    isCompact ? setDrawerOpen((o) => !o) : setMini((m) => !m);

  return (
    <>
      <TopBar
        onMenu={onMenu}
        menuExpanded={isCompact ? drawerOpen : !mini}
        onCreate={() => setUploadOpen(true)}
        search={search}
        setSearch={setSearch}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      />
      <div className="shell">
        <Sidebar
          mini={mini && !isCompact}
          drawerOpen={drawerOpen}
          onNavigate={() => setDrawerOpen(false)}
        />
        {drawerOpen && (
          <div className="scrim" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
        )}
        <main className={`main${mini && !isCompact ? " main--mini" : ""}`}>
          <Routes>
            <Route path="/" element={<DashboardPage toast={toast} />} />
            <Route path="/content" element={
              <ContentPage search={search} toast={toast} refreshKey={refreshKey} />
            } />
            <Route path="/video/:id" element={<VideoDetailPage toast={toast} />} />
            <Route path="/analytics" element={<AnalyticsPage toast={toast} />} />
            <Route path="/reports" element={<ReportsPage toast={toast} />} />
            <Route path="/settings" element={<SettingsPage toast={toast} />} />
          </Routes>
        </main>
      </div>

      {uploadOpen && (
        <UploadDialog
          onClose={() => setUploadOpen(false)}
          onUploaded={() => setRefreshKey((k) => k + 1)}
          toast={toast}
        />
      )}

      {/* Announced to screen readers without stealing focus. */}
      <div className="sr-only" role="status" aria-live="polite">{toastMsg}</div>
      {toastMsg && <div className="toast">{toastMsg}</div>}
    </>
  );
}
