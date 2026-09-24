import { useState, useEffect, useCallback } from 'react'
import { Play, Square, Send, RefreshCw, Wifi, WifiOff, Terminal } from 'lucide-react'

export default function BotControls({ api, token, botStatus, onRefresh }) {
  const [loading,   setLoading]   = useState(false)
  const [msg,       setMsg]       = useState('')
  const [bcText,    setBcText]    = useState('')
  const [bcResult,  setBcResult]  = useState(null)
  const [sending,   setSending]   = useState(false)
  const [logs,      setLogs]      = useState([])

  const authH = { Authorization: `Bearer ${token}` }

  const loadEvents = useCallback(async () => {
    try {
      const res = await fetch(`${api}/events?limit=10`, { headers: authH })
      setLogs(await res.json())
    } catch {}
  }, [api, token]) // eslint-disable-line

  useEffect(() => { loadEvents() }, [loadEvents])

  const startBot = async () => {
    setLoading(true); setMsg('')
    const res = await fetch(`${api}/bot/start`, { method: 'POST', headers: authH })
    const data = await res.json()
    setMsg(data.message)
    await onRefresh()
    setLoading(false)
  }

  const stopBot = async () => {
    setLoading(true); setMsg('')
    const res = await fetch(`${api}/bot/stop`, { method: 'POST', headers: authH })
    const data = await res.json()
    setMsg(data.message)
    await onRefresh()
    setLoading(false)
  }

  const broadcast = async () => {
    if (!bcText.trim()) return
    setSending(true); setBcResult(null)
    const res = await fetch(`${api}/broadcast`, {
      method: 'POST',
      headers: { ...authH, 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: bcText }),
    })
    const data = await res.json()
    setBcResult(data)
    setSending(false)
    if (data.ok) setBcText('')
    await loadEvents()
  }

  return (
    <div className="space-y-6 animate-slide-up max-w-3xl">
      {/* Status + Start/Stop */}
      <div className="card space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Bot Status</h2>
            <p className="text-sm text-gray-400 mt-0.5">Control the bot process directly from here.</p>
          </div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium ${
            botStatus === 'running'
              ? 'bg-green-900/20 border-green-700/50 text-green-400'
              : 'bg-red-900/20 border-red-700/50 text-red-400'
          }`}>
            {botStatus === 'running' ? <Wifi size={14} /> : <WifiOff size={14} />}
            {botStatus === 'running' ? 'Online' : 'Offline'}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={startBot}
            disabled={loading || botStatus === 'running'}
            className="btn-success"
          >
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Play size={15} />}
            Start Bot
          </button>
          <button
            onClick={stopBot}
            disabled={loading || botStatus !== 'running'}
            className="btn-danger"
          >
            {loading ? <RefreshCw size={15} className="animate-spin" /> : <Square size={15} />}
            Stop Bot
          </button>
          <button onClick={() => { onRefresh(); loadEvents() }} className="btn-ghost">
            <RefreshCw size={14} /> Refresh Status
          </button>
        </div>

        {msg && (
          <div className={`text-sm px-4 py-2.5 rounded-lg border ${
            msg.toLowerCase().includes('not') || msg.toLowerCase().includes('error')
              ? 'bg-red-900/20 border-red-800/50 text-red-400'
              : 'bg-green-900/20 border-green-800/50 text-green-400'
          }`}>
            {msg}
          </div>
        )}
      </div>

      {/* Broadcast */}
      <div className="card space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-white">📢 Broadcast Message</h2>
          <p className="text-sm text-gray-400 mt-0.5">
            Send a message to <strong className="text-gray-300">all users</strong> who have started the bot.
          </p>
        </div>

        <textarea
          className="input w-full resize-none h-28"
          placeholder="Type your broadcast message here…"
          value={bcText}
          onChange={e => setBcText(e.target.value)}
        />

        <div className="flex items-center gap-3">
          <button
            onClick={broadcast}
            disabled={sending || !bcText.trim()}
            className="btn-primary"
          >
            {sending ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
            {sending ? 'Sending…' : 'Send Broadcast'}
          </button>
          {bcText && (
            <span className="text-xs text-gray-500">{bcText.length} chars</span>
          )}
        </div>

        {bcResult && (
          <div className={`text-sm px-4 py-2.5 rounded-lg border ${
            bcResult.ok
              ? 'bg-green-900/20 border-green-800/50 text-green-400'
              : 'bg-red-900/20 border-red-800/50 text-red-400'
          }`}>
            {bcResult.ok
              ? `✅ Sent to ${bcResult.sent} users. Failed: ${bcResult.failed}`
              : `❌ ${bcResult.detail || 'Broadcast failed'}`}
          </div>
        )}
      </div>

      {/* Recent bot events mini-log */}
      <div className="card space-y-3">
        <div className="flex items-center gap-2 justify-between">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Terminal size={16} className="text-gray-400" /> Recent Bot Events
          </h2>
          <button onClick={loadEvents} className="text-xs text-gray-500 hover:text-accent-blue transition-colors flex items-center gap-1">
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
        <div className="space-y-2">
          {logs.length === 0 && <p className="text-gray-600 text-sm">No events yet.</p>}
          {logs.map(e => (
            <div key={e.id} className="flex items-start gap-3 text-xs bg-dark-700/50 rounded-lg px-3 py-2">
              <span className="text-gray-600 whitespace-nowrap">
                {e.created_at ? new Date(e.created_at + 'Z').toLocaleTimeString() : ''}
              </span>
              <span className={`font-mono font-medium whitespace-nowrap ${eventColor(e.event_type)}`}>
                [{e.event_type}]
              </span>
              <span className="text-gray-400 truncate">
                {e.full_name ? `${e.full_name} — ` : ''}{e.detail || ''}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function eventColor(type) {
  const map = {
    start:        'text-blue-400',
    join_request: 'text-cyan-400',
    approved:     'text-green-400',
    rejected:     'text-red-400',
    bot_start:    'text-emerald-400',
    bot_stop:     'text-orange-400',
    broadcast:    'text-purple-400',
    error:        'text-red-500',
    banned:       'text-red-400',
  }
  return map[type] || 'text-gray-400'
}
