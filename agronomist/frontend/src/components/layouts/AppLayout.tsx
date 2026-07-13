import { useMemo, useState } from "react";
import {
  Bell,
  BookOpen,
  Bot,
  ChevronLeft,
  ChevronRight,
  CloudSun,
  FileText,
  Gauge,
  HeartPulse,
  HelpCircle,
  Home,
  Landmark,
  LayoutDashboard,
  Leaf,
  LogOut,
  Map,
  Menu,
  MessageCircle,
  Newspaper,
  Settings,
  ShieldCheck,
  Sprout,
  Stethoscope,
  User,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/auth-store";
import { API_BASE_URL } from "../../lib/api/client";
import { useTheme } from "../ui/ThemeProvider";

type NavIcon = LucideIcon;

type NavItem = {
  label: string;
  to?: string;
  icon: NavIcon;
  end?: boolean;
  adminOnly?: boolean;
  farmerOnly?: boolean;
  action?: "logout";
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

function itemClass(isActive: boolean) {
  return isActive ? "sidebar-link sidebar-link-active" : "sidebar-link";
}

function isItemVisible(item: NavItem, role: string | undefined) {
  if (item.adminOnly) {
    return role === "admin";
  }
  if (item.farmerOnly) {
    return role === "farmer";
  }
  return true;
}

function AccountAvatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";

  return <span className="account-avatar" aria-hidden="true">{initials}</span>;
}

function SidebarNav({
  groups,
  collapsed,
  onNavigate,
  onLogout,
}: {
  groups: NavGroup[];
  collapsed: boolean;
  onNavigate?: () => void;
  onLogout: () => void;
}) {
  const location = useLocation();

  return (
    <nav className="sidebar-nav" aria-label="Primary navigation">
      {groups.map((group) => (
        <section className="sidebar-nav-group" key={group.label}>
          <div className="sidebar-group-label">{group.label}</div>
          {group.items.map((item) => {
            const Icon = item.icon;
            if (item.action === "logout") {
              return (
                <button
                  aria-label={item.label}
                  className="sidebar-link sidebar-link-button"
                  key={item.label}
                  onClick={() => {
                    onLogout();
                    onNavigate?.();
                  }}
                  type="button"
                >
                  <Icon aria-hidden size={18} />
                  <span className="sidebar-link-label">{item.label}</span>
                </button>
              );
            }

            if (!item.to) {
              return null;
            }

            const itemPath = item.to.split("?")[0];
            const isActive =
              item.end
                ? location.pathname === itemPath
                : location.pathname === itemPath || location.pathname.startsWith(`${itemPath}/`);

            return (
              <NavLink
                aria-label={collapsed ? item.label : undefined}
                className={() => itemClass(isActive)}
                end={item.end}
                key={`${group.label}-${item.label}`}
                onClick={onNavigate}
                to={item.to}
              >
                <Icon aria-hidden size={18} />
                <span className="sidebar-link-label">{item.label}</span>
              </NavLink>
            );
          })}
        </section>
      ))}
    </nav>
  );
}

function BottomNav({ groups }: { groups: NavGroup[] }) {
  const flattened = groups.flatMap((group) => group.items).filter((item) => item.to);
  const primaryItems = flattened.slice(0, 5);

  return (
    <nav className="bottom-nav" aria-label="Mobile primary navigation">
      {primaryItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            aria-label={item.label}
            className={({ isActive }) =>
              isActive ? "bottom-nav-link bottom-nav-link-active" : "bottom-nav-link"
            }
            end={item.end}
            key={item.label}
            to={item.to!}
          >
            <Icon aria-hidden size={18} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}

export function AppLayout() {
  const { state, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const role = state.user?.role;
  const isAdmin = role === "admin";
  const defaultFarmId = state.user?.default_farm_id || null;
  const farmBase = defaultFarmId ? `/app/farms/${defaultFarmId}` : "/app/farms";
  const displayName = state.user?.full_name || state.user?.email || "Authenticated user";

  const groups = useMemo<NavGroup[]>(() => {
    const farmerGroups: NavGroup[] = [
      {
        label: "Overview",
        items: [{ label: "Dashboard", to: "/app", icon: LayoutDashboard, end: true, farmerOnly: true }],
      },
      {
        label: "Farm Management",
        items: [
          { label: "My Farms", to: "/app/farms", icon: Sprout, farmerOnly: true },
          { label: "Farm Details", to: farmBase, icon: Map, farmerOnly: true },
          { label: "Crop Stage", to: defaultFarmId ? `${farmBase}/stage-advisory` : "/app/farms", icon: Leaf, farmerOnly: true },
          { label: "Farm Timeline", to: defaultFarmId ? `${farmBase}/timeline` : "/app/farms", icon: FileText, farmerOnly: true },
        ],
      },
      {
        label: "AI Tools",
        items: [
          { label: "AI Diagnosis", to: defaultFarmId ? `${farmBase}/diagnosis` : "/app/farms", icon: Stethoscope, farmerOnly: true },
          { label: "AI Farming Chat", to: "/app/chat", icon: Bot, farmerOnly: true },
          { label: "Recommendations", to: defaultFarmId ? `${farmBase}/recommendations` : "/app/farms", icon: HeartPulse, farmerOnly: true },
        ],
      },
      {
        label: "Farm Intelligence",
        items: [
          { label: "Weather", to: defaultFarmId ? `${farmBase}/weather` : "/app/farms", icon: CloudSun, farmerOnly: true },
          { label: "Advisories", to: defaultFarmId ? `${farmBase}/advisories` : "/app/farms", icon: ShieldCheck, farmerOnly: true },
          { label: "Agricultural News", to: defaultFarmId ? `${farmBase}/news` : "/app/farms", icon: Newspaper, farmerOnly: true },
          { label: "Market Prices", to: defaultFarmId ? `${farmBase}/market` : "/app/farms", icon: Landmark, farmerOnly: true },
          { label: "Soil Information", to: defaultFarmId ? `${farmBase}/soil` : "/app/farms", icon: Leaf, farmerOnly: true },
          { label: "Knowledge Search", to: "/app/knowledge", icon: BookOpen, farmerOnly: true },
        ],
      },
      {
        label: "Communication",
        items: [
          { label: "Notifications", to: "/app/notifications", icon: Bell, farmerOnly: true },
          { label: "Contact an Expert", to: defaultFarmId ? `/app/contact-expert?farmId=${defaultFarmId}` : "/app/contact-expert", icon: MessageCircle, farmerOnly: true },
          { label: "Escalation History", to: "/app/escalations", icon: HelpCircle, farmerOnly: true },
        ],
      },
      {
        label: "Account",
        items: [
          { label: "Profile", to: "/app/profile", icon: User },
          { label: "Settings", to: "/app/settings", icon: Settings },
          { label: "Sign Out", icon: LogOut, action: "logout" },
        ],
      },
    ];

    const adminGroups: NavGroup[] = [
      {
        label: "Overview",
        items: [{ label: "Admin Dashboard", to: "/app/admin", icon: Gauge, end: true, adminOnly: true }],
      },
      {
        label: "Management",
        items: [
          { label: "Users", to: "/app/admin/users", icon: Users, adminOnly: true },
          { label: "Knowledge Documents", to: "/app/admin/knowledge", icon: BookOpen, adminOnly: true },
          { label: "Intelligence Sources", to: "/app/admin/intelligence-sources", icon: Newspaper, adminOnly: true },
          { label: "Escalation Contacts", to: "/app/admin/escalation-contacts", icon: MessageCircle, adminOnly: true },
        ],
      },
      {
        label: "Operations",
        items: [
          { label: "Escalations", to: "/app/admin/escalations", icon: HelpCircle, adminOnly: true },
          { label: "Provider Health", to: "/app/admin/provider-health", icon: HeartPulse, adminOnly: true },
          { label: "System Health", to: "/app/admin/system-health", icon: ShieldCheck, adminOnly: true },
        ],
      },
      {
        label: "Account",
        items: [
          { label: "Profile", to: "/app/profile", icon: User },
          { label: "Settings", to: "/app/settings", icon: Settings },
          { label: "Sign Out", icon: LogOut, action: "logout" },
        ],
      },
    ];

    const selectedGroups = isAdmin ? adminGroups : farmerGroups;
    return selectedGroups.map((group) => ({
      ...group,
      items: group.items.filter((item) => isItemVisible(item, role)),
    }));
  }, [defaultFarmId, farmBase, isAdmin, role]);

  return (
    <div className={`app-shell${sidebarCollapsed ? " app-shell-collapsed" : ""}`}>
      <aside className="app-sidebar">
        <div className="sidebar-brand-row">
          <Link className="brand-link" to={isAdmin ? "/app/admin" : "/app"}>
            <Home aria-hidden size={18} />
            <span className="sidebar-link-label">AI Agronomist</span>
          </Link>
          <button
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="icon-button sidebar-collapse"
            onClick={() => setSidebarCollapsed((current) => !current)}
            type="button"
          >
            {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        <div className="sidebar-caption">Production workspace</div>

        <SidebarNav
          collapsed={sidebarCollapsed}
          groups={groups}
          onLogout={logout}
        />

        <div className="sidebar-footer">
          <div className="meta-label">API</div>
          <div className="meta-value">{API_BASE_URL}</div>
        </div>
      </aside>

      <div className={`mobile-drawer${mobileNavOpen ? " mobile-drawer-open" : ""}`}>
        <div className="mobile-drawer-panel">
          <div className="panel-header">
            <Link className="brand-link" to={isAdmin ? "/app/admin" : "/app"}>
              AI Agronomist
            </Link>
            <button
              aria-label="Close navigation"
              className="icon-button"
              onClick={() => setMobileNavOpen(false)}
              type="button"
            >
              <X size={18} />
            </button>
          </div>
          <SidebarNav
            collapsed={false}
            groups={groups}
            onLogout={logout}
            onNavigate={() => setMobileNavOpen(false)}
          />
        </div>
      </div>

      <main className="app-main">
        <header className="topbar">
          <div className="topbar-heading">
            <button
              aria-label="Open navigation"
              className="icon-button mobile-menu-button"
              onClick={() => setMobileNavOpen(true)}
              type="button"
            >
              <Menu size={20} />
            </button>
            <div>
              <div className="eyebrow">{isAdmin ? "Admin workspace" : "Farmer workspace"}</div>
              <div className="topbar-title">{isAdmin ? "Administration" : "Farm operations"}</div>
            </div>
          </div>
          <div className="topbar-actions">
            <Link className="account-chip" to="/app/profile">
              <AccountAvatar name={displayName} />
              <span>{displayName}</span>
            </Link>
            <button className="button button-secondary" onClick={toggleTheme} type="button">
              Theme: {theme}
            </button>
            <button className="button button-ghost" onClick={logout} type="button">
              Sign out
            </button>
          </div>
        </header>

        <section className="content-shell">
          <Outlet />
        </section>
      </main>

      <BottomNav groups={groups} />
    </div>
  );
}
