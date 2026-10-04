import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const links = [
  { to: '/', label: '📊 Dashboard', end: true },
  { to: '/studio', label: '✨ Content Studio' },
  { to: '/accounts', label: '🔗 Accounts' },
  { to: '/analytics', label: '📈 Analytics' },
  { to: '/comments', label: '💬 Comments' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const doLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 border-r border-edge bg-panel/60 p-5 flex flex-col gap-2 sticky top-0 h-screen">
        <div className="mb-6">
          <div className="text-2xl font-extrabold bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
            CreatorGrowth
          </div>
          <div className="text-xs text-slate-500 mt-1">Grow everywhere, from one place.</div>
        </div>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) =>
              `px-4 py-2.5 rounded-xl text-sm font-medium transition ${
                isActive ? 'bg-accent/20 text-white border border-accent/40' : 'text-slate-400 hover:bg-edge/50'
              }`
            }
          >
            {l.label}
          </NavLink>
        ))}
        <div className="mt-auto pt-4 border-t border-edge">
          <div className="text-sm font-semibold truncate">{user?.name}</div>
          <div className="text-xs text-slate-500 truncate mb-3">{user?.email}</div>
          <button onClick={doLogout} className="btn-ghost w-full">
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 max-w-6xl">
        <Outlet />
      </main>
    </div>
  )
}
