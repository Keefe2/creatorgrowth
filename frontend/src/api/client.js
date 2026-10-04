import axios from 'axios'

// Production mein Render se aata hai (VITE_API_URL), local dev mein Vite proxy '/api' use hota hai.
const API_BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({ baseURL: API_BASE })

function getTokens() {
  return {
    access: localStorage.getItem('cg_access'),
    refresh: localStorage.getItem('cg_refresh'),
  }
}

api.interceptors.request.use((config) => {
  const { access } = getTokens()
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

let refreshing = null
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retried && getTokens().refresh) {
      original._retried = true
      refreshing =
        refreshing ||
        axios
          .post(`${API_BASE}/auth/refresh`, { refresh_token: getTokens().refresh })
          .then((r) => {
            localStorage.setItem('cg_access', r.data.access_token)
            localStorage.setItem('cg_refresh', r.data.refresh_token)
            return r.data.access_token
          })
          .catch(() => {
            localStorage.removeItem('cg_access')
            localStorage.removeItem('cg_refresh')
            window.location.href = '/login'
            throw new Error('session expired')
          })
          .finally(() => {
            refreshing = null
          })
      const token = await refreshing
      original.headers.Authorization = `Bearer ${token}`
      return api(original)
    }
    throw error
  }
)

export default api
