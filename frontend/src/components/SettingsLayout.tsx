import { NavLink, Outlet } from "react-router-dom";
import "./SettingsLayout.css";

const SETTINGS_NAV_ITEMS = [
  { to: "/settings/accounts", label: "Accounts" },
  { to: "/settings/categories", label: "Categories" },
];

export function SettingsLayout() {
  return (
    <>
      <nav className="nav settings-subnav">
        {SETTINGS_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link${isActive ? " nav-link-active" : ""}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </>
  );
}
