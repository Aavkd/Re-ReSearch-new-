import { NavLink } from "react-router-dom";
import { BookOpen, Network, FileText, Bot, MessageSquare, Settings } from "lucide-react";

const LINKS = [
  { label: "Library",  to: "/library",  Icon: BookOpen      },
  { label: "Map",      to: "/map",      Icon: Network       },
  { label: "Drafts",   to: "/drafts",   Icon: FileText      },
  { label: "Agent",    to: "/agent",    Icon: Bot           },
  { label: "Chat",     to: "/chat",     Icon: MessageSquare },
] as const;

/**
 * Vertical navigation bar rendered inside the sidebar.
 *
 * Active link: blue highlight (bg-blue-100 / text-blue-800).
 * Inactive link: grey with hover highlight.
 * Settings link is pinned to the bottom.
 */
export function NavBar() {
  return (
    <nav aria-label="Main navigation" className="flex flex-col flex-1">
      <ul className="space-y-1 px-2">
        {LINKS.map(({ label, to, Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-2 rounded px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800",
                ].join(" ")
              }
            >
              <Icon size={16} aria-hidden="true" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* Settings pinned to bottom */}
      <div className="mt-auto px-2 pb-2">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            [
              "flex items-center gap-2 rounded px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800",
            ].join(" ")
          }
        >
          <Settings size={16} aria-hidden="true" />
          Settings
        </NavLink>
      </div>
    </nav>
  );
}
