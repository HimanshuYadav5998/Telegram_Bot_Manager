import { useState, useEffect } from 'react'
import { Plus, Trash2, Link as LinkIcon, Power, Video, FileText } from 'lucide-react'

export default function Previews({ authHeaders }) {
  const [previews, setPreviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState('file_id') // or 'url'
  const [newContent, setNewContent] = useState('')

  const fetchPreviews = async () => {
    try {
      const res = await fetch('/api/previews', { headers: authHeaders })
      if (!res.ok) throw new Error('Failed to fetch previews')
      setPreviews(await res.json())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPreviews()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch('/api/previews', {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName, type: newType, content: newContent })
      })
      if (!res.ok) throw new Error('Failed to create preview')
      setShowAdd(false)
      setNewName('')
      setNewContent('')
      fetchPreviews()
    } catch (e) {
      alert(e.message)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this preview?')) return
    try {
      await fetch(`/api/previews/${id}`, {
        method: 'DELETE',
        headers: authHeaders
      })
      fetchPreviews()
    } catch (e) {
      alert(e.message)
    }
  }

  const handleToggle = async (id, currentState) => {
    try {
      await fetch(`/api/previews/${id}/toggle`, {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentState })
      })
      fetchPreviews()
    } catch (e) {
      alert(e.message)
    }
  }

  const copyLink = (id) => {
    // Generate a placeholder bot link. 
    // In production, the user would replace <YourBotUsername> with their actual bot username.
    const link = `https://t.me/<YourBotUsername>?start=${id}`
    navigator.clipboard.writeText(link)
    alert(`Copied: ${link}\\n\\nNote: Replace <YourBotUsername> with your actual bot username!`)
  }

  if (loading) return <div className="text-gray-400">Loading previews...</div>

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">Content Previews</h2>
          <p className="text-sm text-gray-400">Manage 15-minute preview links for your content</p>
        </div>
        <button 
          onClick={() => setShowAdd(!showAdd)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={16} /> New Preview
        </button>
      </div>

      {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">{error}</div>}

      {showAdd && (
        <form onSubmit={handleCreate} className="card p-5 space-y-4 border border-blue-500/30">
          <h3 className="font-semibold text-white">Create New Preview</h3>
          
          <div>
            <label className="block text-sm text-gray-400 mb-1">Preview Name (e.g. Ben 10 Video)</label>
            <input 
              required
              type="text"
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-4 py-2 text-white"
              value={newName}
              onChange={e => setNewName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Content Type</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-white cursor-pointer">
                <input type="radio" checked={newType === 'file_id'} onChange={() => setNewType('file_id')} className="accent-blue-500" />
                <Video size={16} className="text-blue-400" /> Telegram File ID (Video/Photo)
              </label>
              <label className="flex items-center gap-2 text-white cursor-pointer">
                <input type="radio" checked={newType === 'url'} onChange={() => setNewType('url')} className="accent-blue-500" />
                <FileText size={16} className="text-green-400" /> External URL
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              {newType === 'file_id' ? 'Telegram File ID (paste from @RawDataBot)' : 'Full URL (e.g. https://...)'}
            </label>
            <input 
              required
              type="text"
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-4 py-2 text-white font-mono text-sm"
              value={newContent}
              onChange={e => setNewContent(e.target.value)}
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="submit" className="btn-primary flex-1">Generate Unique Link</button>
            <button type="button" onClick={() => setShowAdd(false)} className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-colors">Cancel</button>
          </div>
        </form>
      )}

      <div className="card overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-dark-600 bg-dark-900/50">
              <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Name</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Created</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-600">
            {previews.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-4 py-8 text-center text-gray-500">No previews created yet.</td>
              </tr>
            ) : previews.map(p => (
              <tr key={p.id} className="hover:bg-dark-700/50 transition-colors">
                <td className="px-4 py-3 font-medium text-white">{p.name}</td>
                <td className="px-4 py-3 text-gray-300">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${p.type === 'file_id' ? 'bg-blue-500/10 text-blue-400' : 'bg-green-500/10 text-green-400'}`}>
                    {p.type === 'file_id' ? <Video size={12}/> : <FileText size={12}/>}
                    {p.type === 'file_id' ? 'File ID' : 'URL'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">{new Date(p.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <span className={`badge-${p.is_active ? 'green' : 'red'}`}>
                    {p.is_active ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button 
                      onClick={() => copyLink(p.id)}
                      className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-blue-400/10 rounded transition-colors"
                      title="Copy Preview Link"
                    >
                      <LinkIcon size={16} />
                    </button>
                    <button 
                      onClick={() => handleToggle(p.id, p.is_active)}
                      className={`p-1.5 rounded transition-colors ${p.is_active ? 'text-green-400 hover:bg-green-400/10' : 'text-gray-500 hover:text-white hover:bg-dark-600'}`}
                      title={p.is_active ? "Disable" : "Enable"}
                    >
                      <Power size={16} />
                    </button>
                    <button 
                      onClick={() => handleDelete(p.id)}
                      className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded transition-colors"
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
