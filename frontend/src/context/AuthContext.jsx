import { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/client.js'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const access = localStorage.getItem('cg_access')
    if (!access) return setLoading(false)
    api
      .get('/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => {
        localStorage.removeItem('cg_access')
        localStorage.removeItem('cg_refresh')
      })
      .finally(() => setLoading(false))
  }, [])

  const saveSession = (data) => {
    localStorage.setItem('cg_access', data.access_token)
    localStorage.setItem('cg_refresh', data.refresh_token)
    setUser(data.user)
  }

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    saveSession(data)
  }

  const register = async (name, email, password) => {
    const { data } = await api.post('/auth/register', { name, email, password })
    saveSession(data)
  }

  const logout = async () => {
    const refresh = localStorage.getItem('cg_refresh')
    try {
      if (refresh) await api.post('/auth/logout', { refresh_token: refresh })
    } finally {
      localStorage.removeItem('cg_access')
      localStorage.removeItem('cg_refresh')
      setUser(null)
    }
  }

  return <AuthCtx.Provider value={{ user, loading, login, register, logout }}>{children}</AuthCtx.Provider>
}
