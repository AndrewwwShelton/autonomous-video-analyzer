export default function TopBar({ onMenu, onCreate, search, setSearch, theme, onToggleTheme }) {
  return (
    <header className="topbar">
      <div className="topbar__left">
        <button className="icon-btn" onClick={onMenu} title="Collapse menu">
          <span className="material-symbols-outlined">menu</span>
        </button>
        <div className="logo">
          <span className="logo__mark">
            <span className="material-symbols-outlined">play_arrow</span>
          </span>
          <span className="logo__text">AdSafe <b>Studio</b></span>
        </div>
      </div>

      <div className="topbar__search">
        <div className="searchbox">
          <span className="material-symbols-outlined">search</span>
          <input
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
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        >
          <span className="material-symbols-outlined">
            {theme === "dark" ? "light_mode" : "dark_mode"}
          </span>
        </button>
        <button className="create-btn" onClick={onCreate}>
          <span className="material-symbols-outlined">video_call</span>
          Create
        </button>
        <div className="avatar">AS</div>
      </div>
    </header>
  );
}
