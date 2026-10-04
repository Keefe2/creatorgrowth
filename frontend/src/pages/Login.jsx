import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

function Shell({ title, subtitle, children, onSubmit, cta, error }) {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="card w-full max-w-md">
        <div className="text-3xl font-extrabold bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent mb-1">
          CreatorGrowth
        </div>
        <h1 className="text-xl font-bold mb-1">{title}</h1>
        <p className="text-sm text-slate-400 mb-6">{subtitle}</p>
        <form onSubmit={onSubmit} className="space-y-4">
          {children}
          {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-2.5">{error}</div>}
          <button className="btn-primary w-full">{cta}</button>
        </form>
      </div>
    </div>
  )
}

export function Field({ label, ...props }) {
  return (
    <div>
      <label className="label">{label}</label>
      <input className="input" {...props} />
    </div>
  )
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email.trim(), password)
      navigate('/')
    } catch (err) {
      if (err.response?.status === 403 && err.response?.data?.detail === 'email_not_verified') {
        navigate('/verify', { state: { email: email.trim() } })
      } else {
        setError('Invalid email or password.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title="Welcome back" subtitle="Log in to your creator HQ." onSubmit={submit} cta={busy ? 'Logging in…' : 'Log in'} error={error}>
      <Field label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
      <Field label="Password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
      <p className="text-sm text-slate-400">
        New here? <Link to="/register" className="text-accent2 font-semibold">Create an account</Link>
      </p>
    </Shell>
  )
}
