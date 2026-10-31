import { Suspense, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { Bell, Bot, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Sun, UserRound } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useNotifications } from '../lib/queries'
import { Loading, Modal } from '../components/ui'
import { AssistantPanel, NotificationsList } from '../components/panels'
import { NAV } from './nav'

const ROLE_LABEL = { STUDENT: 'Student', MENTOR: 'Alumni mentor', ADMIN: 'IIC administrator' } as const

function readPref(key: string, fallback: string) {
  try { return localStorage.getItem(key) ?? fallback } catch { return fallback }
}
function savePref(key: string, value: string) {
  try { localStorage.setItem(key, value) } catch { /* storage unavailable */ }
}

export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') ?? 'sangam-light')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    savePref('sangam.theme', theme)
  }, [theme])
  return { theme, toggle: () => setTheme((t) => (t === 'sangam-dark' ? 'sangam-light' : 'sangam-dark')) }
}

/** Two streams meeting: the Sangam mark. */
export function Brand({ compact = false, light = false }: { compact?: boolean; light?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden>
        <rect width="32" height="32" rx="9" fill={light ? 'rgba(255,255,255,.08)' : '#10303F'} />
        <path d="M5 10c6 0 8 6 14 6h8" fill="none" stroke="#4FB3A2" strokeWidth="2.8" strokeLinecap="round" />
        <path d="M5 22c6 0 8-6 14-6" fill="none" stroke="#E39B1B" strokeWidth="2.8" strokeLinecap="round" />
      </svg>
      {!compact && <span className={`font-display text-xl font-semibold tracking-tight ${light ? 'text-white' : ''}`}>Sangam</span>}
    </span>
  )
}

export function AppShell() {
  const { me, role, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const [collapsed, setCollapsed] = useState(() => readPref('sangam.sidebar', 'open') === 'collapsed')
  const [panel, setPanel] = useState<'notifications' | 'assistant' | null>(null)
  const location = useLocation()
  const unread = useNotifications({ unread: true })
  const items = role ? NAV[role] : []
  const unreadCount = unread.data?.count ?? 0

  useEffect(() => { savePref('sangam.sidebar', collapsed ? 'collapsed' : 'open') }, [collapsed])
  useEffect(() => {
    const drawer = document.getElementById('app-drawer') as HTMLInputElement | null
    if (drawer) drawer.checked = false
    setPanel(null)
  }, [location.pathname])

  return (
    <div className="drawer lg:drawer-open">
      <input id="app-drawer" type="checkbox" className="drawer-toggle" aria-label="Toggle navigation" />
      <div className="drawer-content flex min-h-screen flex-col">
        <header className="bg-base-200/85 sticky top-0 z-30 flex h-16 items-center gap-2 px-4 backdrop-blur sm:px-8">
          <label htmlFor="app-drawer" className="btn btn-ghost btn-sm btn-square lg:hidden" aria-label="Open navigation"><Menu size={20} /></label>
          <Link to="/dashboard" className="lg:hidden"><Brand /></Link>
          <button className="btn btn-ghost btn-sm btn-square hidden lg:inline-flex" onClick={() => setCollapsed((c) => !c)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
          </button>
          <div className="flex-1" />
          <button className="btn btn-ghost btn-sm hidden gap-2 sm:inline-flex" onClick={() => setPanel('assistant')}><Bot size={18} />Ask Sangam</button>
          <button className="btn btn-ghost btn-sm btn-square sm:hidden" onClick={() => setPanel('assistant')} aria-label="Ask Sangam"><Bot size={19} /></button>
          <button className="btn btn-ghost btn-sm btn-square" onClick={() => setPanel('notifications')} aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}>
            <span className="indicator">
              {unreadCount > 0 && <span className="indicator-item bg-accent text-accent-content grid min-w-4 place-items-center rounded-full px-1 text-[10px] font-bold tabular-nums">{unreadCount > 9 ? '9+' : unreadCount}</span>}
              <Bell size={19} />
            </span>
          </button>
          <button className="btn btn-ghost btn-sm btn-square" onClick={toggle} aria-label={theme === 'sangam-dark' ? 'Use light theme' : 'Use dark theme'}>
            {theme === 'sangam-dark' ? <Sun size={19} /> : <Moon size={19} />}
          </button>
          <div className="dropdown dropdown-end">
            <button tabIndex={0} className="btn btn-ghost btn-sm gap-2 rounded-full pr-3 pl-1" aria-label="Account menu">
              <span className="bg-primary text-primary-content grid size-7 place-items-center rounded-full text-sm font-semibold">{me?.display_name.slice(0, 1).toUpperCase()}</span>
              <span className="hidden max-w-40 truncate text-sm font-medium md:inline">{me?.display_name}</span>
            </button>
            <ul tabIndex={0} className="dropdown-content menu bg-base-100 rounded-box border-base-300 z-40 mt-2 w-64 border p-2 shadow-xl">
              <li className="pointer-events-none px-3 py-2">
                <span className="block p-0 font-semibold">{me?.display_name}</span>
                <span className="text-base-content/60 block p-0 text-xs">{me?.email}</span>
                <span className="text-primary block p-0 text-xs font-medium">{role ? ROLE_LABEL[role] : 'No role assigned'}</span>
              </li>
              <li><Link to="/profile"><UserRound size={16} />My profile</Link></li>
              <li><button onClick={logout}><LogOut size={16} />Sign out</button></li>
            </ul>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 pt-4 pb-12 sm:px-8">
          <Suspense fallback={<Loading />}><Outlet /></Suspense>
        </main>
      </div>

      <div className="drawer-side z-40">
        <label htmlFor="app-drawer" aria-label="Close navigation" className="drawer-overlay" />
        <aside className={`bg-neutral text-neutral-content flex min-h-full flex-col transition-[width] duration-200 ${collapsed ? 'w-64 lg:w-[4.75rem]' : 'w-64'}`}>
          <Link to="/dashboard" className={`flex h-16 items-center ${collapsed ? 'px-5 lg:justify-center lg:px-0' : 'px-5'}`}>
            <Brand light compact={collapsed} />
            {collapsed && <span className="font-display ml-2.5 text-xl font-semibold text-white lg:hidden">Sangam</span>}
          </Link>
          <nav aria-label="Primary" className="flex-1 px-3 py-2">
            <ul className="flex flex-col gap-0.5">
              {items.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink to={to} end={to === '/dashboard'} title={collapsed ? label : undefined}
                    className={({ isActive }) => `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[0.9rem] transition-colors ${collapsed ? 'lg:justify-center lg:px-0' : ''} ${
                      isActive ? 'bg-white/10 font-semibold text-white' : 'text-neutral-content/70 hover:bg-white/5 hover:text-white'}`}>
                    {({ isActive }) => (
                      <>
                        {isActive && <span className="absolute top-2 bottom-2 left-0 w-1 rounded-full bg-[#4fb3a2]" aria-hidden />}
                        <Icon size={19} strokeWidth={isActive ? 2.2 : 1.8} aria-hidden />
                        <span className={collapsed ? 'lg:sr-only' : ''}>{label}</span>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className={`text-neutral-content/45 px-6 py-5 text-xs ${collapsed ? 'lg:hidden' : ''}`}>IITM BS mentoring, run by IIC</div>
        </aside>
      </div>

      <Modal variant="sheet" open={panel === 'notifications'} onClose={() => setPanel(null)} title="Notifications"
        subtitle={<Link to="/notifications" className="link link-hover">Open full page</Link>}>
        <NotificationsList pageSize={20} />
      </Modal>
      <Modal variant="sheet" open={panel === 'assistant'} onClose={() => setPanel(null)} title="Ask Sangam">
        <AssistantPanel />
      </Modal>
    </div>
  )
}
