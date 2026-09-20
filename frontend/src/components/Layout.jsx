import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth.jsx";

const LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/new-api", label: "New API" },
  { to: "/projects", label: "My projects" },
  { to: "/history", label: "Chat history" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <p className="brand">
          API Generator
          <span>English in, REST API out</span>
        </p>
        <nav aria-label="Main">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} className={({ isActive }) => (isActive ? "active" : "")}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="account">
          <p className="account-name">{user.name}</p>
          <p className="account-email">{user.email}</p>
          <button type="button" className="button-quiet" onClick={handleLogout}>Log out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}