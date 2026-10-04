import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import Layout from './components/Layout.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Studio from './pages/Studio.jsx'
import Accounts from './pages/Accounts.jsx'
import Analytics from './pages/Analytics.jsx'
import Comments from './pages/Comments.jsx'

function Guard({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen grid place-items-center text-slate-400">Loading…</div>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/*"
        element={
          <Guard>
            <Layout />
          </Guard>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="studio" element={<Studio />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="comments" element={<Comments />} />
      </Route>
    </Routes>
  )
}
