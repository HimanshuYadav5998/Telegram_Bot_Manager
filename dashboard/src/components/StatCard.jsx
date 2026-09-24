export default function StatCard({ title, value, color, icon, desc }) {
  const colors = {
    blue:   'from-blue-600/20 to-blue-800/10 border-blue-700/40 text-blue-400',
    purple: 'from-purple-600/20 to-purple-800/10 border-purple-700/40 text-purple-400',
    green:  'from-emerald-600/20 to-emerald-800/10 border-emerald-700/40 text-emerald-400',
    red:    'from-red-600/20 to-red-800/10 border-red-700/40 text-red-400',
    yellow: 'from-amber-600/20 to-amber-800/10 border-amber-700/40 text-amber-400',
    cyan:   'from-cyan-600/20 to-cyan-800/10 border-cyan-700/40 text-cyan-400',
  }

  return (
    <div className={`bg-gradient-to-br ${colors[color] || colors.blue} border rounded-xl p-5 shadow-lg animate-slide-up`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-3xl font-bold text-white">{value ?? '—'}</span>
      </div>
      <p className="text-sm font-semibold text-gray-200">{title}</p>
      {desc && <p className="text-xs text-gray-500 mt-0.5">{desc}</p>}
    </div>
  )
}
