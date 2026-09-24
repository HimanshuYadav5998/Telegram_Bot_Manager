import { useState } from 'react'
import { Bot, Lock, Eye, EyeOff, Shield } from 'lucide-react'

export default function LoginPage({ onLogin }) {
  const [password, setPassword] = useState('')
  const [show,     setShow]     = useState(false)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (res.ok) {
        const { token } = await res.json()
        localStorage.setItem('dash_token', token)
        onLogin(token)
      } else {
        const data = await res.json()
        setError(data.detail || 'Incorrect password')
      }
    } catch {
      setError('Cannot connect to the API server. Make sure api.py is running.')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-purple-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md animate-slide-up">
        {/* Logo card */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20 mb-4">
            <Bot size={30} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Bot Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Admin Access Only</p>
        </div>

        {/* Login form */}
        <div className="card border-dark-600">
          <div className="flex items-center gap-2 mb-6">
            <Shield size={16} className="text-accent-blue" />
            <h2 className="font-semibold text-gray-200">Sign In</h2>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5 flex items-center gap-1.5">
                <Lock size={12} /> Dashboard Password
              </label>
              <div className="relative">
                <input
                  type={show ? 'text' : 'password'}
                  className="input w-full pr-10"
                  placeholder="Enter your password…"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="text-sm text-red-400 bg-red-900/20 border border-red-800/50 rounded-lg px-3 py-2.5">
                ⚠️ {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !password}
              className="btn-primary w-full justify-center py-2.5"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                  </svg>
                  Verifying…
                </span>
              ) : 'Sign In'}
            </button>
          </form>

          <p className="text-xs text-gray-600 text-center mt-5">
            Set your password in Settings after your first login with the default password.
          </p>
        </div>

        <p className="text-center text-xs text-gray-700 mt-6">
          Default password: <code className="text-gray-500">admin123</code> — change it immediately in Settings.
        </p>
      </div>
    </div>
  )
}
