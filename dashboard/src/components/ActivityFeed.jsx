import { useState, useEffect, useCallback, useRef } from 'react'
import { RefreshCw, Activity } from 'lucide-react'

const EVENT_META = {
  start:             { label: 'Bot Started',      color: 'text-blue-400',    bg: 'bg-blue-900/20',    dot: 'bg-blue-400',    icon: '🖱️' },
  join_request:      { label: 'Join Request',      color: 'text-cyan-400',    bg: 'bg-cyan-900/20',    dot: 'bg-cyan-400',    icon: '📨' },
  approved:          { label: 'Approved',          color: 'text-green-400',   bg: 'bg-green-900/20',   dot: 'bg-green-400',   icon: '✅' },
  rejected:          { label: 'Rejected',          color: 'text-red-400',     bg: 'bg-red-900/20',     dot: 'bg-red-400',     icon: '❌' },
  bot_start:         { label: 'Bot Started',       color: 'text-emerald-400', bg: 'bg-emerald-900/20', dot: 'bg-emerald-400', icon: '▶️' },
  bot_stop:          { label: 'Bot Stopped',       color: 'text-orange-400',  bg: 'bg-orange-900/20',  dot: 'bg-orange-400',  icon: '⏹️' },
  broadcast:         { label: 'Broadcast',         color: 'text-purple-400',  bg: 'bg-purple-900/20',  dot: 'bg-purple-400',  icon: '📢' },
  error:             { label: 'Error',             color: 'text-red-500',     bg: 'bg-red-900/30',     dot: 'bg-red-500',     icon: '⚠️' },
  config_change:     { label: 'Config Changed',    color: 'text-yellow-400',  bg: 'bg-yellow-900/20',  dot: 'bg-yellow-400',  icon: '⚙️' },
  user_status_change:{ label: 'User Status',       color: 'text-amber-400',   bg: 'bg-amber-900/20',   dot: 'bg-amber-400',   icon: '👤' },
}

export default function ActivityFeed({ api, token }) {
  const [events,  setEvents]  = useState([])
  const [loading, setLoading] = useState(true)
  const [filter,  setFilter]  = useState('all')
  const bottomRef = useRef(null)

  const authH = { Authorization: `Bearer ${token}` }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${api}/events?limit=100`, { headers: authH })
      setEvents(await res.json())
    } catch {}
    setLoading(false)
  }, [api, token]) // eslint-disable-line

  useEffect(() => { load() }, [load])

  // Auto-poll every 5 seconds
  useEffect(() => {
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [load])

  const types     = ['all', ...Object.keys(EVENT_META)]
  const displayed = filter === 'all' ? events : events.filter(e => e.event_type === filter)

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-accent-blue" />
          <span className="font-semibold text-white">Live Activity Feed</span>
          <span className="badge-blue text-xs">{displayed.length} events</span>
        </div>
        <button onClick={load} className="btn-ghost text-xs">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {types.slice(0, 8).map(t => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-all border ${
              filter === t
                ? 'bg-accent-blue border-accent-blue text-white'
                : 'bg-dark-700 border-dark-600 text-gray-400 hover:text-gray-200'
            }`}
          >
            {t === 'all' ? '🌐 All' : `${EVENT_META[t]?.icon} ${t.replace('_', ' ')}`}
          </button>
        ))}
      </div>

      {/* Feed */}
      <div className="card p-0 max-h-[600px] overflow-y-auto">
        {loading && events.length === 0 && (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <RefreshCw size={18} className="animate-spin mr-2" /> Loading events…
          </div>
        )}
        {!loading && displayed.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            No events yet. Send /start to your bot on Telegram.
          </div>
        )}
        <div className="divide-y divide-dark-700">
          {displayed.map(e => {
            const meta = EVENT_META[e.event_type] || {
              label: e.event_type, color: 'text-gray-400', bg: 'bg-dark-700', dot: 'bg-gray-500', icon: '•'
            }
            return (
              <div key={e.id} className={`flex items-start gap-4 px-5 py-3.5 hover:bg-dark-700/30 transition-colors`}>
                <div className="flex-shrink-0 flex flex-col items-center gap-1.5 pt-0.5">
                  <div className={`w-2 h-2 rounded-full ${meta.dot}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-semibold ${meta.color}`}>
                      {meta.icon} {meta.label}
                    </span>
                    {e.full_name && (
                      <span className="text-sm text-gray-300 font-medium">{e.full_name}</span>
                    )}
                    {e.username && (
                      <a
                        href={`https://t.me/${e.username}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-accent-blue hover:underline"
                      >
                        @{e.username}
                      </a>
                    )}
                    {e.user_id && (
                      <span className="text-xs text-gray-600 font-mono">#{e.user_id}</span>
                    )}
                  </div>
                  {e.detail && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{e.detail}</p>
                  )}
                </div>
                <time className="flex-shrink-0 text-xs text-gray-600 whitespace-nowrap">
                  {e.created_at ? new Date(e.created_at + 'Z').toLocaleString() : ''}
                </time>
              </div>
            )
          })}
        </div>
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
