import { NavLink } from "react-router-dom";

const ITEMS = [
  { to: "/", icon: "dashboard", label: "Dashboard", end: true },
  { to: "/content", icon: "video_library", label: "Content" },
  { to: "/analytics", icon: "bar_chart", label: "Analytics" },
  { to: "/reports", icon: "description", label: "Reports" },
  { to: "/settings", icon: "settings", label: "Settings" },
];

export default function Sidebar({ mini, drawerOpen, onNavigate }) {
  return (
    <nav
      className={`sidebar${mini ? " sidebar--mini" : ""}${drawerOpen ? " sidebar--open" : ""}`}
      aria-label="Main navigation"
    >
      <div className="sidebar__channel">
        <div className="sidebar__avatar" aria-hidden="true">AS</div>
        <h3>Your studio</h3>
        <p>Local library · offline</p>
      </div>
      {ITEMS.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          end={it.end}
          onClick={onNavigate}
          className={({ isActive }) => `navitem${isActive ? " active" : ""}`}
        >
          <span className="material-symbols-outlined" aria-hidden="true">{it.icon}</span>
          <span>{it.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
