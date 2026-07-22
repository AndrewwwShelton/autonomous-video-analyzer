import { NavLink } from "react-router-dom";

const ITEMS = [
  { to: "/", icon: "video_library", label: "Content", end: true },
  { to: "/reports", icon: "description", label: "Reports" },
  { to: "/settings", icon: "settings", label: "Settings" },
];

export default function Sidebar({ mini }) {
  return (
    <nav className={`sidebar${mini ? " sidebar--mini" : ""}`}>
      <div className="sidebar__channel">
        <div className="sidebar__avatar">AS</div>
        <h3>Your studio</h3>
        <p>Local library · offline</p>
      </div>
      {ITEMS.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          end={it.end}
          className={({ isActive }) => `navitem${isActive ? " active" : ""}`}
        >
          <span className="material-symbols-outlined">{it.icon}</span>
          <span>{it.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
