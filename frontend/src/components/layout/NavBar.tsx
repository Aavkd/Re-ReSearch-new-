import { NavLink } from "react-router-dom";

const LINKS = [
  { label: "Library", to: "/library" },
  { label: "Map", to: "/map" },
  { label: "Drafts", to: "/drafts" },
  { label: "Agent", to: "/agent" },
] as const;

/**
 * Vertical navigation bar rendered inside the sidebar.
 *
 * Active link: blue highlight (bg-blue-100 / text-blue-800).
 * Inactive link: grey with hover highlight.
 */
export function NavBar() {
  return (
    <nav aria-label="Main navigation">
      <ul className="space-y-1 px-2">
        {LINKS.map(({ label, to }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                [
                  "block rounded px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-100 text-blue-800"
                    : "text-gray-600 hover:bg-gray-100",
                ].join(" ")
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
