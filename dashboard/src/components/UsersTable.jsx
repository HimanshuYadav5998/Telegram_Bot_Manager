import { useState, useEffect, useCallback } from 'react'
import { Search, RefreshCw, Ban, CheckCircle, UserX } from 'lucide-react'

export default function UsersTable({ api, token }) {
  const [users,   setUsers]   = useState([])
  const [search,  setSearch]  = useState('')
  const [loading, setLoading] = useState(true)
  const [action,  setAction]  = useState(null) // { userId, type }

  const authH = { Authorization: `Bearer ${token}` }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${api}/users?search=${encodeURIComponent(search)}`, { headers: authH })
      setUsers(await res.json())
    } catch {}
    setLoading(false)
  }, [api, search, token]) // eslint-disable-line

  useEffect(() => { load() }, [load])

  const setStatus = async (userId, status) => {
    setAction({ userId, type: status })
    await fetch(`${api}/users/${userId}/status`, {
      method: 'POST',
      headers: { ...authH, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    await load()
    setAction(null)
  }

  const statusBadge = (s) => {
    if (s === 'banned') return <span className="badge-red">Banned</span>
    return <span className="badge-green">Active</span>
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-9 w-full"
            placeholder="Search by name, username, or ID…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <button onClick={load} className="btn-ghost">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
        <span className="text-sm text-gray-500">{users.length} users</span>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-dark-700 border-b border-dark-600">
                <th className="text-left px-5 py-3 text-gray-400 font-medium">User</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Username</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">User ID</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">First Seen</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Status</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    <RefreshCw size={18} className="animate-spin inline mr-2" />
                    Loading users…
                  </td>
                </tr>
              )}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    No users found.
                  </td>
                </tr>
              )}
              {users.map(u => (
                <tr key={u.user_id} className="border-b border-dark-700 hover:bg-dark-700/40 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                        {(u.full_name || '?')[0].toUpperCase()}
                      </div>
                      <span className="font-medium text-gray-200 truncate max-w-[150px]">
                        {u.full_name || '—'}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-gray-400">
                    {u.username ? (
                      <a
                        href={`https://t.me/${u.username}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent-blue hover:underline"
                      >
                        @{u.username}
                      </a>
                    ) : '—'}
                  </td>
                  <td className="px-5 py-3 font-mono text-gray-400 text-xs">{u.user_id}</td>
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {u.first_seen ? new Date(u.first_seen + 'Z').toLocaleString() : '—'}
                  </td>
                  <td className="px-5 py-3">{statusBadge(u.status)}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      {u.status !== 'banned' ? (
                        <button
                          onClick={() => setStatus(u.user_id, 'banned')}
                          disabled={action?.userId === u.user_id}
                          className="btn bg-red-900/30 hover:bg-red-800/50 text-red-400 text-xs py-1 px-2.5 border border-red-800/50"
                        >
                          {action?.userId === u.user_id && action.type === 'banned'
                            ? <RefreshCw size={11} className="animate-spin" />
                            : <Ban size={11} />
                          }
                          Ban
                        </button>
                      ) : (
                        <button
                          onClick={() => setStatus(u.user_id, 'active')}
                          disabled={action?.userId === u.user_id}
                          className="btn bg-green-900/30 hover:bg-green-800/50 text-green-400 text-xs py-1 px-2.5 border border-green-800/50"
                        >
                          {action?.userId === u.user_id && action.type === 'active'
                            ? <RefreshCw size={11} className="animate-spin" />
                            : <CheckCircle size={11} />
                          }
                          Unban
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
