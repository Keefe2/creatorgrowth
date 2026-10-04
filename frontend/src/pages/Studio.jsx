import { useEffect, useState } from 'react'
import api from '../api/client.js'

const PLATFORMS = ['facebook', 'x', 'youtube', 'instagram']
const TONES = ['viral', 'bold', 'playful', 'professional']
const STATUS_STYLE = {
  draft: 'bg-slate-500/20 text-slate-300',
  scheduled: 'bg-amber-500/20 text-amber-300',
  published: 'bg-emerald-500/20 text-emerald-300',
  failed: 'bg-red-500/20 text-red-300',
}

export default function Studio() {
  const [posts, setPosts] = useState([])
  const [topic, setTopic] = useState('')
  const [tone, setTone] = useState('viral')
  const [platform, setPlatform] = useState('facebook')
  const [language, setLanguage] = useState('ur')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [targets, setTargets] = useState(['facebook'])
  const [scheduledAt, setScheduledAt] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = () => api.get('/content').then((r) => setPosts(r.data)).catch(() => {})
  useEffect(load, [])

  const toggleTarget = (p) =>
    setTargets((t) => (t.includes(p) ? t.filter((x) => x !== p) : [...t, p]))

  const generate = async () => {
    if (topic.trim().length < 3) return setMsg('Topic kam se kam 3 characters ka ho.')
    setBusy(true)
    setMsg('')
    try {
      const { data } = await api.post('/content/generate', { topic, tone, platform, language })
      setTitle(data.title)
      setBody(data.body + '\n\n' + data.hashtags.join(' '))
      setMsg('✨ Draft tayyar hai — edit karo phir save ya schedule karo.')
    } catch {
      setMsg('Generation failed.')
    } finally {
      setBusy(false)
    }
  }

  const save = async (schedule) => {
    if (!body.trim() || targets.length === 0) return setMsg('Body aur kam se kam 1 platform zaroori hai.')
    setBusy(true)
    setMsg('')
    try {
      if (schedule) {
        if (!scheduledAt) return setMsg('Schedule ke liye date/time select karo.')
        await api.post('/content/schedule', {
          title, body, platforms: targets, scheduled_at: new Date(scheduledAt).toISOString(),
        })
        setMsg('⏰ Scheduled! Background worker waqt par publish karega.')
      } else {
        await api.post('/content?ai=' + (title ? 'true' : 'false'), { title, body, platforms: targets })
        setMsg('💾 Draft save ho gaya.')
      }
      setTitle(''); setBody(''); setScheduledAt('')
      load()
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Save failed.')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    if (!confirm('Delete this post?')) return
    await api.delete(`/content/${id}`)
    load()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold">Content Studio</h1>

      <div className="card space-y-4">
        <h2 className="font-bold">🤖 AI Generator</h2>
        <div className="grid md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
            <label className="label">Topic</label>
            <input className="input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Subah jaldi uthne ke fayde" />
          </div>
          <div>
            <label className="label">Tone</label>
            <select className="input" value={tone} onChange={(e) => setTone(e.target.value)}>
              {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Platform style</label>
            <select className="input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select className="input w-40" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="ur">Urdu</option>
            <option value="en">English</option>
          </select>
          <button onClick={generate} disabled={busy} className="btn-primary">{busy ? 'Generating…' : 'Generate'}</button>
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="font-bold">📝 Editor</h2>
        <div>
          <label className="label">Title</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Post title" />
        </div>
        <div>
          <label className="label">Body</label>
          <textarea className="input min-h-[140px]" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Post body…" />
        </div>
        <div>
          <label className="label">Target platforms</label>
          <div className="flex gap-2 flex-wrap">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                onClick={() => toggleTarget(p)}
                className={`btn-ghost ${targets.includes(p) ? '!border-accent !bg-accent/20 text-white' : ''}`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <input type="datetime-local" className="input w-64" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
          <button onClick={() => save(false)} disabled={busy} className="btn-ghost">💾 Save draft</button>
          <button onClick={() => save(true)} disabled={busy} className="btn-primary">⏰ Schedule</button>
        </div>
        {msg && <div className="text-sm text-accent2">{msg}</div>}
      </div>

      <div className="card">
        <h2 className="font-bold mb-4">Your posts ({posts.length})</h2>
        <div className="space-y-3">
          {posts.map((p) => (
            <div key={p.id} className="border border-edge rounded-xl p-4 flex gap-4 items-start">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`badge ${STATUS_STYLE[p.status]}`}>{p.status}</span>
                  <span className="text-xs text-slate-500">{p.platforms.join(', ')}</span>
                  {p.scheduled_at && <span className="text-xs text-slate-500">⏰ {new Date(p.scheduled_at).toLocaleString()}</span>}
                </div>
                <div className="font-semibold mt-1 truncate">{p.title || '(no title)'}</div>
                <div className="text-sm text-slate-400 line-clamp-2 whitespace-pre-line">{p.body}</div>
                {p.error && <div className="text-xs text-red-400 mt-1">{p.error}</div>}
              </div>
              <button onClick={() => remove(p.id)} className="btn-ghost text-red-400">Delete</button>
            </div>
          ))}
          {posts.length === 0 && <p className="text-sm text-slate-500">Abhi koi post nahi — upar se generate karo.</p>}
        </div>
      </div>
    </div>
  )
}
