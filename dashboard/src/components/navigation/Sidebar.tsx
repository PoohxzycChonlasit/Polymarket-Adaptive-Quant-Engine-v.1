import { NavLink } from "react-router-dom";

import { navItems } from "./navItems";

export function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Dashboard navigation">
      <div className="sidebar-title">Quant Terminal</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            end={item.path === "/"}
            key={item.path}
            to={item.path}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
