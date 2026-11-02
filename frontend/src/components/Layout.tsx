import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/documents", label: "Documents" },
  { to: "/analysis/new", label: "New Analysis" },
  { to: "/sensitivity", label: "Sensitivity Explorer" },
];

export function Layout({ children }: { children: ReactNode }) {
  const { email, role, logout } = useAuth();

  return (
    <div className="min-h-screen flex" style={{ background: "var(--page-plane)" }}>
      <aside className="w-60 shrink-0 border-r border-[var(--border-hairline)] bg-[var(--surface-1)] flex flex-col">
        <div className="px-5 py-5 border-b border-[var(--border-hairline)]">
          <div className="font-semibold text-[var(--text-primary)] text-lg leading-tight">PE-Analyst</div>
          <div className="text-xs text-[var(--text-muted)]">Deal underwriting workbench</div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[var(--series-1)] text-white"
                    : "text-[var(--text-secondary)] hover:bg-[var(--page-plane)]"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-[var(--border-hairline)]">
          <div className="text-sm text-[var(--text-primary)] truncate" title={email ?? undefined}>
            {email ?? "Signed in"}
          </div>
          {role && <div className="text-xs text-[var(--text-muted)] capitalize">{role}</div>}
          <button
            onClick={logout}
            className="mt-3 w-full rounded-md border border-[var(--border-hairline)] px-3 py-1.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--page-plane)]"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 px-8 py-8">{children}</main>
    </div>
  );
}
