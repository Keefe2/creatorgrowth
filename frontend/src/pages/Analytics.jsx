import { useState } from 'react'
import api from '../api/client.js'

const PLATFORMS = ['facebook', 'x', 'youtube', 'instagram']

export default function Analytics() {
  const [platform, setPlatform] = useState('facebook')
  const [followers, setFollowers] = useState('')
  const [impressions, setImpressions] = useState('')
  const [engagement, setEngagement] = useState('')
  const [msg, setMsg] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.post('/analytics/snapshot', {
        platform,
        followers: Number(followers),
        impressions: Number(impressions),
        engagement: Number(engagement),
      })
      setFollowers(''); setImpressions(''); setEngagement('')
      setMsg('✅ Snapshot recorded — dashboard update ho gaya.')
    } catch {
      setMsg('Failed. Numbers check karo.')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold">Analytics</h1>
      <div className="card">
        <h2 className="font-bold mb-4">📈 Record a snapshot</h2>
        <p className="text-sm text-slate-400 mb-4">
          Roz ka data yahan record karo — dashboard automatically aggregate karega. (Platform APIs connect hone par ye auto-sync hoga.)
        </p>
        <form onSubmit={submit} className="grid md:grid-cols-4 gap-3">
          <div>
            <label className="label">Platform</label>
            <select className="input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Followers</label>
            <input className="input" type="number" min="0" required value={followers} onChange={(e) => setFollowers(e.target.value)} />
          </div>
          <div>
            <label className="label">Impressions</label>
            <input className="input" type="number" min="0" required value={impressions} onChange={(e) => setImpressions(e.target.value)} />
          </div>
          <div>
            <label className="label">Engagement</label>
            <input className="input" type="number" min="0" required value={engagement} onChange={(e) => setEngagement(e.target.value)} />
          </div>
          <div className="md:col-span-4">
            <button className="btn-primary">Record snapshot</button>
          </div>
        </form>
        {msg && <div className="text-sm text-accent2 mt-3">{msg}</div>}
      </div>
    </div>
  )
}
