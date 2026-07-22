import { useCallback, useEffect, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import UploadDialog from "./components/UploadDialog";
import ContentPage from "./pages/ContentPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import VideoDetailPage from "./pages/VideoDetailPage";

export default function App() {
  const [mini, setMini] = useState(false);
  const [search, setSearch] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [toastMsg, setToastMsg] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") ?? "dark");
  const toastTimer = useRef(null);

  // Dark is the default; the stamp on <html> drives every token in styles.css.
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toast = useCallback((msg) => {
    setToastMsg(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMsg(null), 3200);
  }, []);

  return (
    <>
      <TopBar
        onMenu={() => setMini((m) => !m)}
        onCreate={() => setUploadOpen(true)}
        search={search}
        setSearch={setSearch}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      />
      <div className="shell">
        <Sidebar mini={mini} />
        <main className={`main${mini ? " main--mini" : ""}`}>
          <Routes>
            <Route path="/" element={
              <ContentPage search={search} toast={toast} refreshKey={refreshKey} />
            } />
            <Route path="/video/:id" element={<VideoDetailPage toast={toast} />} />
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
      {toastMsg && <div className="toast">{toastMsg}</div>}
    </>
  );
}
