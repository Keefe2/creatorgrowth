import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { Field } from './Login.jsx'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (password.length < 8) return setError('Password must be at least 8 characters.')
    setBusy(true)
    setError('')
    try {
      const trimmedEmail = email.trim()
      await register(name.trim(), trimmedEmail, password)
      navigate('/verify', { state: { email: trimmedEmail } })
    } catch (err) {
      setError(err.response?.status === 409 ? 'Email already registered.' : 'Registration failed. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="card w-full max-w-md">
        <div className="text-3xl font-extrabold bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent mb-1">
          CreatorGrowth
        </div>
        <h1 className="text-xl font-bold mb-1">Create your account</h1>
        <p className="text-sm text-slate-400 mb-6">One login for every platform you grow on.</p>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          <Field label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          <Field label="Password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min. 8 characters" />
          {error && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-2.5">{error}</div>}
          <button className="btn-primary w-full">{busy ? 'Creating…' : 'Create account'}</button>
          <p className="text-sm text-slate-400">
            Already have an account? <Link to="/login" className="text-accent2 font-semibold">Log in</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
