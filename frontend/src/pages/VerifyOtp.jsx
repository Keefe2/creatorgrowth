import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import api from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import { Field } from './Login.jsx'

const COOLDOWN = 60

export default function VerifyOtp() {
  const { saveSession } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const presetEmail = location.state?.email || ''
  const [email, setEmail] = useState(presetEmail)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('We sent a 6-digit code to your email. It expires in 10 minutes.')
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(COOLDOWN)
  const busyRef = useRef(false)

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const verify = async (value) => {
    const otp = (value ?? code).trim()
    if (!/^\d{6}$/.test(otp) || busyRef.current) return
    if (!email.trim()) return setError('Enter the email you registered with.')
    busyRef.current = true
    setBusy(true)
    setError('')
    try {
      const { data } = await api.post('/auth/verify-otp', { email: email.trim(), otp })
      saveSession(data)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed. Try again.')
      setCode('')
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  const onCodeChange = (e) => {
    const v = e.target.value.replace(/\D/g, '').slice(0, 6)
    setCode(v)
    if (v.length === 6) verify(v)
  }

  const resend = async () => {
    if (!email.trim()) return setError('Enter the email you registered with.')
    if (cooldown > 0 || busyRef.current) return
    setError('')
    try {
      const { data } = await api.post('/auth/resend-otp', { email: email.trim() })
      setInfo(data.message)
      setCode('')
      setCooldown(COOLDOWN)
    } catch (err) {
      if (err.response?.status === 429) setError('Please wait before requesting a new code.')
      else setError(err.response?.data?.detail || 'Could not resend the code.')
    }
  }

  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="card w-full max-w-md">
        <div className="text-3xl font-extrabold bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent mb-1">
          CreatorGrowth
        </div>
        <h1 className="text-xl font-bold mb-1">Check your email</h1>
        <p className="text-sm text-slate-400 mb-6">
          Enter the 6-digit code to verify your account
          {email ? (
            <> sent to <span className="text-slate-200 font-semibold">{email}</span>.</>
          ) : (
            '.'
          )}
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            verify()
          }}
          className="space-y-4"
        >
          {!presetEmail && (
            <Field
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          )}
          <Field
            label="Verification code"
            inputMode="numeric"
            autoComplete="one-time-code"
            required
            value={code}
            onChange={onCodeChange}
            placeholder="123456"
            maxLength={6}
            className="input tracking-[0.4em] text-center text-2xl font-bold"
          />
          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-2.5">
              {error}
            </div>
          )}
          {!error && info && (
            <div className="text-sm text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-2.5">
              {info}
            </div>
          )}
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? 'Verifying…' : 'Verify'}
          </button>
          <button
            type="button"
            onClick={resend}
            disabled={cooldown > 0}
            className="w-full text-sm font-semibold text-accent2 disabled:text-slate-500 disabled:cursor-not-allowed py-2"
          >
            {cooldown > 0
              ? `Resend code in 0:${String(cooldown).padStart(2, '0')}`
              : 'Resend code'}
          </button>
          <p className="text-sm text-slate-400">
            Wrong email?{' '}
            <Link to="/register" className="text-accent2 font-semibold">
              Start over
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
