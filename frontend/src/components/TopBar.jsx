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
          <span className="logo__mark" aria-hidden="true">
            <span className="material-symbols-outlined">play_arrow</span>
          </span>
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
