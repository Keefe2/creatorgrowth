import { useEffect, useState } from 'react'
import api from '../api/client.js'

const PLATFORMS = ['facebook', 'x', 'youtube', 'instagram']

export default function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [platform, setPlatform] = useState('facebook')
  const [name, setName] = useState('')
  const [token, setToken] = useState('')
  const [msg, setMsg] = useState('')

  const load = () => api.get('/accounts').then((r) => setAccounts(r.data)).catch(() => {})
  useEffect(load, [])

  const connect = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      await api.post('/accounts', { platform, account_name: name.trim(), access_token: token })
      setName(''); setToken('')
      setMsg('✅ Account connected. Token encrypted at rest.')
      load()
    } catch (err) {
      setMsg(err.response?.status === 409 ? 'Ye account pehle se connected hai.' : 'Connect failed.')
    }
  }

  const disconnect = async (id) => {
    if (!confirm('Disconnect this account?')) return
    await api.delete(`/accounts/${id}`)
    load()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold">Connected Accounts</h1>

      <div className="card">
        <h2 className="font-bold mb-4">🔗 Connect a new account</h2>
        <form onSubmit={connect} className="grid md:grid-cols-4 gap-3">
          <div>
            <label className="label">Platform</label>
            <select className="input" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Account name</label>
            <input className="input" required value={name} onChange={(e) => setName(e.target.value)} placeholder="My Page" />
          </div>
          <div className="md:col-span-2">
            <label className="label">Access token (encrypted, never shown again)</label>
            <input className="input" required type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="paste token" />
          </div>
          <div className="md:col-span-4">
            <button className="btn-primary">Connect</button>
          </div>
        </form>
        {msg && <div className="text-sm text-accent2 mt-3">{msg}</div>}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {accounts.map((a) => (
          <div key={a.id} className="card flex items-center gap-4">
            <div className="text-3xl">🔒</div>
            <div className="flex-1">
              <div className="font-bold">{a.account_name}</div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">{a.platform} · connected {new Date(a.created_at).toLocaleDateString()}</div>
            </div>
            <button onClick={() => disconnect(a.id)} className="btn-ghost text-red-400">Disconnect</button>
          </div>
        ))}
        {accounts.length === 0 && <p className="text-sm text-slate-500">Koi account connected nahi — upar se connect karo.</p>}
      </div>
    </div>
  )
}
