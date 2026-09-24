import { useState, useEffect, useCallback } from 'react'
import { Bot, BarChart3, Users, Bell, Settings, RefreshCw, LogOut, Video } from 'lucide-react'
import StatCard from './components/StatCard'
import UsersTable from './components/UsersTable'
import BotControls from './components/BotControls'
import ActivityFeed from './components/ActivityFeed'
import JoinRequests from './components/JoinRequests'
import LoginPage from './components/LoginPage'
import Previews from './components/Previews'

const API = '/api'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard',     icon: BarChart3 },
  { id: 'users',     label: 'Users',         icon: Users     },
  { id: 'requests',  label: 'Join Requests', icon: Bell      },
  { id: 'previews',  label: 'Content Previews', icon: Video  },
  { id: 'controls',  label: 'Bot Controls',  icon: Bot       },
  { id: 'activity',  label: 'Activity',      icon: RefreshCw },
  { id: 'settings',  label: 'Settings',      icon: Settings  },
]

export default function App() {
  const [token,   setToken]   = useState(() => localStorage.getItem('dash_token'))
  const [page,    setPage]    = useState('dashboard')
  const [stats,   setStats]   = useState(null)
  const [botStatus, setBotStatus] = useState('unknown')
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  const logout = () => {
    localStorage.removeItem('dash_token')
    setToken(null)
  }

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const [sRes, bRes] = await Promise.all([
        fetch(`${API}/stats`,      { headers: authHeaders }),
        fetch(`${API}/bot/status`, { headers: authHeaders }),
      ])
      if (sRes.status === 401 || bRes.status === 401) { logout(); return }
      setStats(await sRes.json())
      const b = await bRes.json()
      setBotStatus(b.status)
      setLastRefresh(new Date())
    } catch {}
  }, [token]) // eslint-disable-line

  useEffect(() => {
    fetchStats()
    const timer = setInterval(fetchStats, 8000)
    return () => clearInterval(timer)
  }, [fetchStats])

  // Not logged in → show login page
  if (!token) return <LoginPage onLogin={setToken} />

  return (
    <div className="flex h-screen bg-dark-900 overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="w-64 bg-dark-800 border-r border-dark-600 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-dark-600">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Bot size={22} className="text-white" />
            </div>
            <div>
              <p className="font-bold text-white text-sm leading-tight">Bot Dashboard</p>
              <p className="text-xs text-gray-500">Admin Panel</p>
            </div>
          </div>
        </div>

        {/* Bot status pill */}
        <div className="px-6 py-3 border-b border-dark-600">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${
              botStatus === 'running'     ? 'bg-green-400 animate-pulse' :
              botStatus === 'restarting'  ? 'bg-amber-400 animate-pulse' :
              'bg-red-500'
            }`} />
            <span className="text-xs text-gray-400">
              Bot is{' '}
              <span className={
                botStatus === 'running'    ? 'text-green-400' :
                botStatus === 'restarting' ? 'text-amber-400' :
                'text-red-400'
              }>
                {botStatus}
              </span>
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                page === id
                  ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30'
                  : 'text-gray-400 hover:bg-dark-700 hover:text-gray-200'
              }`}
            >
              <Icon size={17} />
              {label}
              {id === 'requests' && stats?.pending > 0 && (
                <span className="ml-auto text-xs px-1.5 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800">
                  {stats.pending}
                </span>
              )}
            </button>
          ))}
        </nav>

        {/* Footer / logout */}
        <div className="px-5 py-4 border-t border-dark-600 space-y-2">
          <p className="text-xs text-gray-600">
            Refreshed: {lastRefresh.toLocaleTimeString()}
          </p>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-red-900/20 hover:text-red-400 transition-all"
          >
            <LogOut size={15} /> Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 bg-dark-900/80 backdrop-blur border-b border-dark-600 px-8 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">
            {NAV_ITEMS.find(n => n.id === page)?.label}
          </h1>
          <div className="flex items-center gap-3">
            {stats && <span className="text-xs text-gray-500">{stats.total_users} users</span>}
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-xs font-bold">
              A
            </div>
          </div>
        </header>

        <div className="p-8 animate-fade-in">
          {page === 'dashboard' && <DashboardPage stats={stats} botStatus={botStatus} />}
          {page === 'users'     && <UsersTable api={API} token={token} />}
          {page === 'requests'  && <JoinRequests api={API} token={token} onRefresh={fetchStats} />}
          {page === 'previews'  && <Previews authHeaders={authHeaders} />}
          {page === 'controls'  && <BotControls api={API} token={token} botStatus={botStatus} onRefresh={fetchStats} />}
          {page === 'activity'  && <ActivityFeed api={API} token={token} />}
          {page === 'settings'  && <SettingsPage api={API} token={token} />}
        </div>
      </main>
    </div>
  )
}

// ── Dashboard overview ─────────────────────────────────────────────────────────
function DashboardPage({ stats, botStatus }) {
  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <RefreshCw size={20} className="animate-spin mr-2" /> Loading stats…
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-slide-up">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Users"    value={stats.total_users}    color="blue"   icon="👤" desc="Users who started the bot" />
        <StatCard title="/start Clicks"  value={stats.total_starts}   color="purple" icon="🖱️" desc="Total /start command hits" />
        <StatCard title="Join Requests"  value={stats.total_requests} color="cyan"   icon="📨" desc="Channel join requests" />
        <StatCard title="Approved"       value={stats.approved}       color="green"  icon="✅" desc="Auto & manually approved" />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard title="Pending"      value={stats.pending}      color="yellow" icon="⏳" desc="Awaiting action" />
        <StatCard title="Rejected"     value={stats.rejected}     color="red"    icon="❌" desc="Rejected requests" />
        <StatCard title="Banned Users" value={stats.banned_users} color="red"    icon="🚫" desc="Banned from bot" />
      </div>

      <div className={`card flex items-center gap-4 border ${
        botStatus === 'running'
          ? 'border-green-800/50 bg-green-900/10'
          : 'border-red-800/50 bg-red-900/10'
      }`}>
        <div className={`w-3 h-3 rounded-full ${
          botStatus === 'running' ? 'bg-green-400 animate-pulse' : 'bg-red-500'
        }`} />
        <div>
          <p className="font-semibold text-white">
            Bot is currently{' '}
            <span className={botStatus === 'running' ? 'text-green-400' : 'text-red-400'}>
              {botStatus}
            </span>
          </p>
          <p className="text-sm text-gray-400">
            {botStatus === 'running'
              ? 'The bot is actively listening for messages and join requests.'
              : 'Go to Bot Controls to start it.'}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Settings page ──────────────────────────────────────────────────────────────
function SettingsPage({ api, token }) {
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  const [config,      setConfig]      = useState({ channel_link: '', bot_token: '' })
  const [rawToken,    setRawToken]    = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [saving,      setSaving]      = useState(false)
  const [savePwdBusy, setSavePwdBusy] = useState(false)
  const [msg,         setMsg]         = useState('')
  const [pwdMsg,      setPwdMsg]      = useState('')

  useEffect(() => {
    fetch(`${api}/config`, { headers })
      .then(r => r.json())
      .then(d => setConfig(d))
      .catch(() => {})
  }, [api]) // eslint-disable-line

  const saveConfig = async () => {
    setSaving(true); setMsg('')
    const body = { channel_link: config.channel_link }
    if (rawToken) body.bot_token = rawToken
    const res = await fetch(`${api}/config`, {
      method: 'PUT', headers,
      body: JSON.stringify(body),
    })
    setMsg(res.ok ? '✅ Settings saved!' : '❌ Failed to save')
    setSaving(false)
    setTimeout(() => setMsg(''), 3000)
  }

  const savePassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      setPwdMsg('❌ Password must be at least 6 characters')
      return
    }
    setSavePwdBusy(true); setPwdMsg('')
    const res = await fetch(`${api}/auth/change-password`, {
      method: 'POST', headers,
      body: JSON.stringify({ new_password: newPassword }),
    })
    setPwdMsg(res.ok ? '✅ Password changed! You will need to log in again.' : '❌ Failed')
    setNewPassword('')
    setSavePwdBusy(false)
    if (res.ok) setTimeout(() => {
      localStorage.removeItem('dash_token')
      window.location.reload()
    }, 2000)
  }

  return (
    <div className="max-w-2xl space-y-6 animate-slide-up">
      {/* Bot Config */}
      <div className="card space-y-5">
        <h2 className="text-lg font-semibold text-white">⚙️ Bot Configuration</h2>

        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Channel Invite Link</label>
          <input
            className="input w-full"
            value={config.channel_link || ''}
            onChange={e => setConfig(c => ({ ...c, channel_link: e.target.value }))}
            placeholder="https://t.me/+YOUR_INVITE_LINK"
          />
          <p className="text-xs text-gray-600 mt-1">
            Changing this updates the link sent to every user who runs /start — instantly, no restart needed.
          </p>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Bot Token</label>
          <input
            className="input w-full font-mono text-sm"
            type="password"
            value={rawToken}
            onChange={e => setRawToken(e.target.value)}
            placeholder="Paste new token to change (leave blank to keep current)"
          />
          <p className="text-xs text-gray-600 mt-1">
            Current token ends in: <code className="text-accent-blue">{config.bot_token}</code>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={saveConfig} disabled={saving} className="btn-primary">
            {saving ? <RefreshCw size={14} className="animate-spin" /> : null}
            Save Changes
          </button>
          {msg && <span className="text-sm">{msg}</span>}
        </div>
      </div>

      {/* Change Password */}
      <div className="card space-y-4 border-yellow-800/30">
        <h2 className="text-lg font-semibold text-white">🔒 Change Dashboard Password</h2>
        <p className="text-sm text-gray-400">
          Set a strong password only you know. Minimum 6 characters.
        </p>

        <div>
          <label className="block text-sm text-gray-400 mb-1.5">New Password</label>
          <input
            className="input w-full"
            type="password"
            value={newPassword}
            onChange={e => setNewPassword(e.target.value)}
            placeholder="New dashboard password…"
          />
        </div>

        <div className="flex items-center gap-3">
          <button onClick={savePassword} disabled={savePwdBusy} className="btn-warning">
            {savePwdBusy ? <RefreshCw size={14} className="animate-spin" /> : '🔒'}
            Change Password
          </button>
          {pwdMsg && <span className="text-sm">{pwdMsg}</span>}
        </div>
      </div>
    </div>
  )
}
