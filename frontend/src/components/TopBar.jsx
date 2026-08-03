import { Link } from "react-router-dom";

export default function TopBar({
  onMenu, menuExpanded, onCreate, search, setSearch, theme, onToggleTheme,
}) {
  return (
    <header className="topbar">
      <div className="topbar__left">
        <button
          className="icon-btn"
          onClick={onMenu}
          aria-label="Toggle navigation menu"
          aria-expanded={menuExpanded}
        >
          <span className="material-symbols-outlined" aria-hidden="true">menu</span>
        </button>
        <Link className="logo" to="/" aria-label="AdSafe Studio home">
          {/* Own mark, deliberately not derived from any platform's branding.
              Crop-mark corners frame a checked area: a verified safe region of
              video, which is exactly what the tool produces. */}
          <svg className="logo__mark" viewBox="0 0 32 32" aria-hidden="true"
               focusable="false">
            <defs>
              <linearGradient id="adsafe-mark" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#7c5cff" />
                <stop offset="100%" stopColor="#4c6ef5" />
              </linearGradient>
            </defs>
            <rect width="32" height="32" rx="9" fill="url(#adsafe-mark)" />
            <g fill="none" stroke="#fff" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 12.4V10.6h1.9M21 12.4V10.6h-1.9M11 19.6v1.8h1.9M21 19.6v1.8h-1.9"
                    strokeWidth="1.9" opacity="0.85" />
              <path d="M12.4 16.3l2.5 2.5 5-5.4" strokeWidth="2.5" />
            </g>
          </svg>
          <span className="logo__text">AdSafe <b>Studio</b></span>
        </Link>
      </div>

      <div className="topbar__search">
        <div className="searchbox">
          <span className="material-symbols-outlined" aria-hidden="true">search</span>
          <input
            type="search"
            aria-label="Search across your library"
            placeholder="Search across your library"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="topbar__right">
        <button
          className="icon-btn"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            {theme === "dark" ? "light_mode" : "dark_mode"}
          </span>
        </button>
        <button className="create-btn" onClick={onCreate}>
          <span className="material-symbols-outlined" aria-hidden="true">video_call</span>
          <span className="create-btn__label">Create</span>
        </button>
        <div className="avatar" aria-hidden="true">AS</div>
      </div>
    </header>
  );
}
