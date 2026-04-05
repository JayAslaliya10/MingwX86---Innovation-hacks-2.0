import { useAuth0 } from '@auth0/auth0-react'
import { Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getMe } from '../../api/client'
import Loading from './Loading'

export default function ProtectedRoute({ children, requiresNoHealthCard = false }) {
  const { isAuthenticated, isLoading } = useAuth0()
  const [user, setUser] = useState(null)
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    if (isLoading) return          // still waiting for Auth0
    if (!isAuthenticated) {
      setFetching(false)           // not logged in — stop spinner, redirect to login
      return
    }
    getMe()
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setFetching(false))
  }, [isAuthenticated, isLoading])

  if (isLoading || fetching) return <Loading />
  if (!isAuthenticated) return <Navigate to="/login" replace />

  // User not registered yet → go register
  if (!user) return <Navigate to="/register" replace />

  // Health card users cannot access upload page
  if (requiresNoHealthCard && user.health_card_number) {
    return <Navigate to="/dashboard" replace />
  }

  // Users without health card must upload before dashboard
  if (!requiresNoHealthCard && !user.health_card_number) {
    // Check if they've uploaded at least one policy
    // (simple flag check — backend handles this)
  }

  return children
}
