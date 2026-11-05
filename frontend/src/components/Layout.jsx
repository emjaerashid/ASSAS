import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { COUNTS_CHANGED_EVENT } from '../context/FeedbackContext';
import api, { resolveMediaUrl } from '../utils/api';

// Pending counts change as students submit requests, so the badges re-poll
// in the background and also refresh whenever the tab regains focus.
const COUNTS_POLL_MS = 45000;
const COLLAPSED_KEY = 'assas.sidebarCollapsed';
const OPEN_GROUPS_KEY = 'assas.openNavGroups';
const MOBILE_QUERY = '(max-width: 900px)';

// Top-level entries are either a single link or a folder group whose
// children render as a dashed tree, mirroring the CityU student portal.
const ADMIN_NAV = [
  { to: '/admin', end: true, icon: 'home', label: 'Dashboard' },
  {
    group: 'Allocation',
    icon: 'folder',
    items: [
      { to: '/admin/assign', label: 'Assign Subjects' },
      { to: '/admin/exceptions', label: 'Exceptions', badgeKey: 'pending_exceptions' },
      { to: '/admin/add-drop', label: 'Add/Drop Requests', badgeKey: 'pending_add_drop' },
    ],
  },
  {
    group: 'Records',
    icon: 'folder',
    items: [
      { to: '/admin/students', label: 'Students' },
      { to: '/admin/subjects', label: 'Subjects' },
      { to: '/admin/timetables', label: 'Timetables' },
      { to: '/admin/venues', label: 'Venues' },
    ],
  },
];

const STUDENT_NAV = [
  { to: '/student', end: true, icon: 'home', label: 'My Subjects' },
  {
    group: 'Academic',
    icon: 'folder',
    items: [
      { to: '/student/progress', label: 'Academic Progress' },
      { to: '/student/timetables', label: 'Class Schedule' },
    ],
  },
  {
    group: 'Registration',
    icon: 'folder',
    items: [
      { to: '/student/add-drop', label: 'Add/Drop Request' },
    ],
  },
];

const ADMIN_RAIL = [
  { to: '/admin/assign', icon: 'bolt', label: 'Run assignment' },
  { to: '/admin/exceptions', icon: 'flag', label: 'Review exceptions' },
  { to: '/admin/add-drop', icon: 'swap_horiz', label: 'Add/Drop requests' },
  { to: '/admin/students', icon: 'group', label: 'Students' },
];

const STUDENT_RAIL = [
  { to: '/student', icon: 'home', label: 'My subjects' },
  { to: '/student/timetables', icon: 'calendar_month', label: 'Class schedule' },
  { to: '/student/add-drop?new=1', icon: 'edit_note', label: 'New add/drop request' },
  { to: '/student/progress', icon: 'donut_small', label: 'Academic progress' },
];

function initials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase();
}

function matches(item, pathname) {
  return item.end ? pathname.replace(/\/$/, '') === item.to : pathname.startsWith(item.to);
}

function readStored(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw == null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function writeStored(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ }
}

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(MOBILE_QUERY).matches);
  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY);
    const onChange = () => setIsMobile(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  return isMobile;
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = user?.role === 'admin';
  const isMobile = useIsMobile();

  const [collapsed, setCollapsed] = useState(() => readStored(COLLAPSED_KEY, false) === true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState(() => readStored(OPEN_GROUPS_KEY, {}));
  const [adminStats, setAdminStats] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const navTree = isAdmin ? ADMIN_NAV : STUDENT_NAV;
  const rail = isAdmin ? ADMIN_RAIL : STUDENT_RAIL;
  const student = user?.student_profile;

  const allLinks = [
    ...navTree.flatMap((entry) => entry.items || [entry]),
    ...(isAdmin ? [] : [{ to: '/student/profile', label: 'My Profile' }]),
  ];
  const activeItem = allLinks.find((item) => matches(item, location.pathname));
  const activeGroup = navTree.find((entry) => entry.items?.some((item) => item === activeItem))?.group;

  const toggleSidebar = () => {
    if (isMobile) {
      setDrawerOpen((o) => !o);
      return;
    }
    setCollapsed((c) => {
      writeStored(COLLAPSED_KEY, !c);
      return !c;
    });
  };

  const toggleGroup = (name) => {
    if (collapsed && !isMobile) {
      // Expanding a group only makes sense with labels showing.
      setCollapsed(false);
      writeStored(COLLAPSED_KEY, false);
      setOpenGroups((g) => ({ ...g, [name]: true }));
      return;
    }
    setOpenGroups((g) => {
      const next = { ...g, [name]: !(g[name] ?? true) };
      writeStored(OPEN_GROUPS_KEY, next);
      return next;
    });
  };

  // The group holding the current page always opens, so the active link is
  // never hidden inside a closed folder after navigating from elsewhere.
  useEffect(() => {
    if (activeGroup) setOpenGroups((g) => (g[activeGroup] ? g : { ...g, [activeGroup]: true }));
  }, [activeGroup]);

  // The mobile drawer and profile menu close themselves once a destination
  // is picked.
  useEffect(() => {
    setDrawerOpen(false);
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (e) => !menuRef.current?.contains(e.target) && setMenuOpen(false);
    const onKey = (e) => e.key === 'Escape' && setMenuOpen(false);
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    document.title = activeItem ? `${activeItem.label} · ASSAS` : 'ASSAS';
  }, [activeItem]);

  const refreshCounts = useCallback(() => {
    if (!isAdmin) return;
    api.get('/admin/dashboard/').then(setAdminStats).catch(() => {});
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    refreshCounts();
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') refreshCounts();
    }, COUNTS_POLL_MS);
    const onVisible = () => document.visibilityState === 'visible' && refreshCounts();
    window.addEventListener(COUNTS_CHANGED_EVENT, refreshCounts);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(timer);
      window.removeEventListener(COUNTS_CHANGED_EVENT, refreshCounts);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [isAdmin, refreshCounts]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const badgeFor = (item) => (item.badgeKey ? adminStats?.[item.badgeKey] || 0 : 0);

  // The teal topbar block is a context-aware shortcut: whatever is most
  // likely the next thing to do right now.
  const pendingExceptions = adminStats?.pending_exceptions || 0;
  const pendingAddDrop = adminStats?.pending_add_drop || 0;
  const quickAction = isAdmin
    ? pendingExceptions + pendingAddDrop > 0
      ? {
        to: pendingExceptions > 0 ? '/admin/exceptions' : '/admin/add-drop',
        icon: 'task_alt',
        label: `Review ${pendingExceptions + pendingAddDrop} pending`,
      }
      : { to: '/admin/assign', icon: 'bolt', label: 'Run Assignment' }
    : { to: '/student/add-drop?new=1', icon: 'edit_note', label: 'New Add/Drop' };

  const sidebarClass = [
    'sidebar',
    collapsed && !isMobile ? 'collapsed' : '',
    drawerOpen ? 'open' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={`app-layout${collapsed && !isMobile ? ' is-collapsed' : ''}`}>
      <header className="topbar">
        <div className="topbar-brand">
          <img className="topbar-logo" src="/logo-transparent.png" alt="City University Malaysia" />
          <div className="topbar-wordmark">
            <span className="topbar-wordmark-title">ASSAS</span>
            <span className="topbar-wordmark-sub">{isAdmin ? 'Admin Portal' : 'Student Portal'}</span>
          </div>
        </div>
        <div className="topbar-bar">
          <button className="topbar-toggle" onClick={toggleSidebar} aria-label="Toggle navigation">
            <span className="material-symbols-outlined">
              {isMobile ? (drawerOpen ? 'close' : 'menu') : collapsed ? 'arrow_forward' : 'arrow_back'}
            </span>
          </button>
          <div className="topbar-spacer" />
          <Link className="topbar-quick" to={quickAction.to}>
            <span className="material-symbols-outlined">{quickAction.icon}</span>
            <span className="topbar-quick-label">{quickAction.label}</span>
          </Link>
          <div className="topbar-menu" ref={menuRef}>
            <button className={`topbar-user topbar-user-btn${menuOpen ? ' open' : ''}`}
              onClick={() => setMenuOpen((o) => !o)} aria-haspopup="menu" aria-expanded={menuOpen}>
              {student?.photo ? (
                <img className="topbar-avatar" src={resolveMediaUrl(student.photo)} alt="" />
              ) : (
                <div className="topbar-avatar">{initials(user?.full_name)}</div>
              )}
              <div className="topbar-user-info">
                <span className="topbar-user-name">{user?.full_name}</span>
                <span className="topbar-user-role">
                  {isAdmin ? 'Administrator' : `${user?.student_id} · Sem ${student?.current_semester ?? '—'}`}
                </span>
              </div>
              <span className="material-symbols-outlined topbar-user-caret">expand_more</span>
            </button>
            {menuOpen && (
              <div className="topbar-dropdown" role="menu">
                {!isAdmin && (
                  <Link to="/student/profile" className="topbar-dropdown-item" role="menuitem">
                    <span className="material-symbols-outlined">person</span>My Profile
                  </Link>
                )}
                <button className="topbar-dropdown-item" role="menuitem" onClick={handleLogout}>
                  <span className="material-symbols-outlined">power_settings_new</span>Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="app-body">
        {drawerOpen && <div className="drawer-backdrop" onClick={() => setDrawerOpen(false)} />}
        <nav className={sidebarClass}>
          {student && (
            <div className="sidebar-profile">
              {student.photo ? (
                <img className="sidebar-profile-photo" src={resolveMediaUrl(student.photo)} alt="" />
              ) : (
                <div className="sidebar-profile-photo">{initials(user?.full_name)}</div>
              )}
              <div className="sidebar-profile-text">
                <div className="sidebar-profile-name">{user?.full_name}</div>
                <div className="sidebar-profile-sub">
                  {student.programme?.programme_code} · Sem {student.current_semester} · CGPA {student.cgpa}
                </div>
              </div>
            </div>
          )}

          <div className="sidebar-nav">
            {navTree.map((entry) => {
              if (!entry.group) {
                return (
                  <NavLink key={entry.to} to={entry.to} end={entry.end} className="nav-top"
                    title={collapsed ? entry.label : undefined}>
                    <span className="material-symbols-outlined">{entry.icon}</span>
                    <span className="sidebar-nav-label">{entry.label}</span>
                  </NavLink>
                );
              }

              const open = openGroups[entry.group] ?? true;
              const groupBadge = entry.items.reduce((n, item) => n + badgeFor(item), 0);
              const isActiveGroup = entry.group === activeGroup;
              return (
                <div key={entry.group} className={`nav-group${open ? ' open' : ''}`}>
                  <button className={`nav-top nav-group-toggle${isActiveGroup ? ' has-active' : ''}`}
                    onClick={() => toggleGroup(entry.group)} aria-expanded={open}
                    title={collapsed ? entry.group : undefined}>
                    <span className="material-symbols-outlined">{open ? 'folder_open' : entry.icon}</span>
                    <span className="sidebar-nav-label">{entry.group}</span>
                    {!open && groupBadge > 0 && <span className="sidebar-nav-badge">{groupBadge}</span>}
                    {groupBadge > 0 && <span className="sidebar-nav-dot" />}
                    <span className="nav-group-sign" aria-hidden="true">{open ? '−' : '+'}</span>
                  </button>
                  {open && (
                    <div className="nav-tree">
                      {entry.items.map((item) => {
                        const badge = badgeFor(item);
                        return (
                          <NavLink key={item.to} to={item.to} end={item.end} className="nav-leaf">
                            <span className="nav-leaf-dot" />
                            <span className="sidebar-nav-label">{item.label}</span>
                            {badge > 0 && <span key={badge} className="sidebar-nav-badge">{badge}</span>}
                          </NavLink>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

        </nav>

        <main className="main-content">
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </main>

        <div className="quick-rail" aria-label="Quick actions">
          {rail.map((r) => (
            <Link key={r.to} to={r.to} className="quick-rail-btn" aria-label={r.label}>
              <span className="material-symbols-outlined">{r.icon}</span>
              <span className="quick-rail-tip">{r.label}</span>
            </Link>
          ))}
          <button className="quick-rail-btn" aria-label="Back to top"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <span className="material-symbols-outlined">vertical_align_top</span>
            <span className="quick-rail-tip">Back to top</span>
          </button>
        </div>
      </div>
    </div>
  );
}
