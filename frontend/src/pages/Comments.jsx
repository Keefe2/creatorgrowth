import { useEffect, useState } from 'react'
import api from '../api/client.js'

const PLATFORMS = ['facebook', 'x', 'youtube', 'instagram']

export default function Comments() {
  const [tasks, setTasks] = useState([])
  const [platform, setPlatform] = useState('facebook')
  const [postRef, setPostRef] = useState('')
  const [text, setText] = useState('')
  const [msg, setMsg] = useState('')

  const load = () => api.get('/comments/queue').then((r) => setTasks(r.data)).catch(() => {})
  useEffect(load, [])

  const queue = async (e) => {
    e.preventDefault()
    try {
      await api.post('/comments/queue', { platform, post_ref: postRef.trim(), comment_text: text.trim() })
      setPostRef(''); setText('')
      setMsg('✅ Queued.')
      load()
    } catch {
      setMsg('Queue failed.')
    }
  }

  const done = async (id) => {
    await api.post(`/comments/queue/${id}/done`)
    load()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold">Comment Queue</h1>

      <div className="card">
        <h2 className="font-bold mb-4">💬 Queue a reply</h2>
        <form onSubmit={queue} className="grid md:grid-cols-3 gap-3">
          <div>
            <label className="label">Platform</label>
            <select className="input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="label">Post reference (URL or ID)</label>
            <input className="input" required value={postRef} onChange={(e) => setPostRef(e.target.value)} placeholder="https://…" />
          </div>
          <div className="md:col-span-3">
            <label className="label">Reply text</label>
            <textarea className="input" required value={text} onChange={(e) => setText(e.target.value)} placeholder="Your reply…" />
          </div>
          <div className="md:col-span-3">
            <button className="btn-primary">Queue reply</button>
          </div>
        </form>
        {msg && <div className="text-sm text-accent2 mt-3">{msg}</div>}
      </div>

      <div className="card">
        <h2 className="font-bold mb-4">Queue ({tasks.length})</h2>
        <div className="space-y-3">
          {tasks.map((t) => (
            <div key={t.id} className="border border-edge rounded-xl p-4 flex items-start gap-4">
              <div className="flex-1">
                <div className="flex gap-2 items-center">
                  <span className="badge bg-accent/20 text-accent2">{t.platform}</span>
                  <span className={`badge ${t.status === 'done' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>{t.status}</span>
                </div>
                <div className="text-sm mt-1 truncate text-slate-400">{t.post_ref}</div>
                <div className="mt-1">{t.comment_text}</div>
              </div>
              {t.status !== 'done' && <button onClick={() => done(t.id)} className="btn-ghost">Mark done</button>}
            </div>
          ))}
          {tasks.length === 0 && <p className="text-sm text-slate-500">Queue khaali hai.</p>}
        </div>
      </div>
    </div>
  )
}
