import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { setAuthToken } from './api/client'

import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import DrugSearch from './pages/DrugSearch'
import Comparison from './pages/Comparison'
import ProtectedRoute from './components/Auth/ProtectedRoute'
import Loading from './components/Auth/Loading'

export default function App() {
  const { isLoading, isAuthenticated, getAccessTokenSilently } = useAuth0()

  // Keep axios token fresh
  useEffect(() => {
    if (!isAuthenticated) return
    const syncToken = async () => {
      try {
        const token = await getAccessTokenSilently()
        setAuthToken(token)
      } catch (e) {
        console.error('Token refresh failed', e)
      }
    }
    syncToken()
    const interval = setInterval(syncToken, 5 * 60 * 1000) // refresh every 5 min
    return () => clearInterval(interval)
  }, [isAuthenticated, getAccessTokenSilently])

  if (isLoading) return <Loading />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/dashboard"
          element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
        />
        <Route
          path="/upload"
          element={<ProtectedRoute requiresNoHealthCard><Upload /></ProtectedRoute>}
        />
        <Route
          path="/drugs"
          element={<ProtectedRoute><DrugSearch /></ProtectedRoute>}
        />
        <Route
          path="/compare"
          element={<ProtectedRoute><Comparison /></ProtectedRoute>}
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
