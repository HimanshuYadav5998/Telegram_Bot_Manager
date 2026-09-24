import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react'

const STATUS_BADGE = {
  pending:  <span className="badge-yellow">Pending</span>,
  approved: <span className="badge-green">Approved</span>,
  rejected: <span className="badge-red">Rejected</span>,
}

export default function JoinRequests({ api, token, onRefresh }) {
  const [requests, setRequests] = useState([])
  const [filter,   setFilter]   = useState('all')
  const [loading,  setLoading]  = useState(true)
  const [acting,   setActing]   = useState(null)

  const authH = { Authorization: `Bearer ${token}` }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const url = filter === 'all' ? `${api}/join-requests` : `${api}/join-requests?status=${filter}`
      const res = await fetch(url, { headers: authH })
      setRequests(await res.json())
    } catch {}
    setLoading(false)
  }, [api, filter, token]) // eslint-disable-line

  useEffect(() => { load() }, [load])

  const act = async (userId, action) => {
    setActing(`${userId}-${action}`)
    await fetch(`${api}/join-requests/${userId}/${action}`, { method: 'POST', headers: authH })
    await Promise.all([load(), onRefresh()])
    setActing(null)
  }

  const FILTERS = ['all', 'pending', 'approved', 'rejected']

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Filter tabs */}
      <div className="flex items-center gap-2">
        {FILTERS.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition-all ${
              filter === f
                ? 'bg-accent-blue text-white'
                : 'bg-dark-700 text-gray-400 hover:text-gray-200'
            }`}
          >
            {f}
          </button>
        ))}
        <button onClick={load} className="ml-auto btn-ghost text-xs">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
        <span className="text-sm text-gray-500">{requests.length} requests</span>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-dark-700 border-b border-dark-600">
                <th className="text-left px-5 py-3 text-gray-400 font-medium">User</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Username</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">User ID</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Requested</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Status</th>
                <th className="text-left px-5 py-3 text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    <RefreshCw size={18} className="animate-spin inline mr-2" /> Loading…
                  </td>
                </tr>
              )}
              {!loading && requests.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500">
                    No join requests found.
                  </td>
                </tr>
              )}
              {requests.map(r => (
                <tr key={r.id} className="border-b border-dark-700 hover:bg-dark-700/40 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
                        {(r.full_name || '?')[0].toUpperCase()}
                      </div>
                      <span className="font-medium text-gray-200 truncate max-w-[140px]">
                        {r.full_name || '—'}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-gray-400">
                    {r.username
                      ? <a href={`https://t.me/${r.username}`} target="_blank" rel="noreferrer" className="text-accent-blue hover:underline">@{r.username}</a>
                      : '—'}
                  </td>
                  <td className="px-5 py-3 font-mono text-gray-400 text-xs">{r.user_id}</td>
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {r.created_at ? new Date(r.created_at + 'Z').toLocaleString() : '—'}
                  </td>
                  <td className="px-5 py-3">{STATUS_BADGE[r.status] || r.status}</td>
                  <td className="px-5 py-3">
                    {r.status === 'pending' && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => act(r.user_id, 'approve')}
                          disabled={!!acting}
                          className="btn bg-green-900/30 hover:bg-green-800/50 text-green-400 text-xs py-1 px-2.5 border border-green-800/50"
                        >
                          {acting === `${r.user_id}-approve`
                            ? <RefreshCw size={11} className="animate-spin" />
                            : <CheckCircle size={11} />}
                          Approve
                        </button>
                        <button
                          onClick={() => act(r.user_id, 'reject')}
                          disabled={!!acting}
                          className="btn bg-red-900/30 hover:bg-red-800/50 text-red-400 text-xs py-1 px-2.5 border border-red-800/50"
                        >
                          {acting === `${r.user_id}-reject`
                            ? <RefreshCw size={11} className="animate-spin" />
                            : <XCircle size={11} />}
                          Reject
                        </button>
                      </div>
                    )}
                    {r.status !== 'pending' && (
                      <span className="text-gray-600 text-xs italic">No action</span>
                    )}
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
