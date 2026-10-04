import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client.js'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const PLATFORM_COLOR = { facebook: '#1877f2', x: '#e7e9ea', youtube: '#ff0000', instagram: '#e1306c' }

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get('/analytics/dashboard')
      .then((r) => setData(r.data))
      .catch(() => setError('Could not load dashboard.'))
  }, [])

  if (error) return <div className="card text-red-400">{error}</div>
  if (!data) return <div className="text-slate-400">Loading dashboard…</div>

  const chartData = data.by_platform.map((p) => ({
    name: p.platform,
    impressions: p.impressions,
    engagement: p.engagement,
  }))

  const stats = [
    { label: 'Followers', value: data.totals.followers, icon: '👥' },
    { label: 'Impressions', value: data.totals.impressions, icon: '👁️' },
    { label: 'Engagement', value: data.totals.engagement, icon: '🔥' },
    { label: 'Scheduled', value: data.scheduled_count, icon: '⏰' },
    { label: 'Published', value: data.published_count, icon: '🚀' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold">Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">Your entire creator business at a glance.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="card">
            <div className="text-2xl">{s.icon}</div>
            <div className="text-2xl font-extrabold mt-2">{s.value.toLocaleString()}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wider">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="font-bold mb-4">Impressions vs Engagement by platform</h2>
        {chartData.length === 0 ? (
          <p className="text-sm text-slate-400">
            No data yet. <Link to="/analytics" className="text-accent2 font-semibold">Record your first snapshot →</Link>
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3d" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1f2a3d', borderRadius: 12 }} />
              <Bar dataKey="impressions" fill="#7c5cff" radius={[6, 6, 0, 0]} />
              <Bar dataKey="engagement" fill="#22d3ee" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {[
          { to: '/studio', t: '✨ New post', d: 'Generate AI copy and schedule it.' },
          { to: '/accounts', t: '🔗 Connect account', d: 'Link Facebook, X, YouTube, Instagram.' },
          { to: '/comments', t: '💬 Comment queue', d: 'Line up replies and engagement.' },
        ].map((c) => (
          <Link key={c.to} to={c.to} className="card hover:border-accent/60 transition">
            <div className="font-bold">{c.t}</div>
            <div className="text-sm text-slate-400 mt-1">{c.d}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
