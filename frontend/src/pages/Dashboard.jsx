import { useEffect, useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { useNavigate } from 'react-router-dom'
import { getMe, onLogin, getNotifications, markNotificationSeen, listMyPolicies } from '../api/client'
import NotificationBanner from '../components/PolicyUpdates/NotificationBanner'
import PolicyCard from '../components/Dashboard/PolicyCard'
import NavBar from '../components/Dashboard/NavBar'

export default function Dashboard() {
  const { logout } = useAuth0()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [policies, setPolicies] = useState([])
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      try {
        const [meRes, loginRes] = await Promise.all([getMe(), onLogin()])
        setUser(meRes.data)

        const [policiesRes, notifRes] = await Promise.all([
          listMyPolicies(),
          getNotifications(),
        ])
        setPolicies(policiesRes.data)
        setNotifications(notifRes.data.filter((n) => !n.seen))
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const dismissNotification = async (id) => {
    await markNotificationSeen(id)
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar user={user} onLogout={() => logout({ returnTo: window.location.origin })} />

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user?.full_name?.split(' ')[0]}
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {user?.health_card_number
              ? `Health Card: ${user.health_card_number}`
              : 'Uploaded policy account'}
          </p>
        </div>

        {/* Policy Update Notifications */}
        {notifications.length > 0 && (
          <div className="mb-6 space-y-3">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Policy Updates ({notifications.length})
            </h2>
            {notifications.map((n) => (
              <NotificationBanner
                key={n.id}
                notification={n}
                onDismiss={() => dismissNotification(n.id)}
              />
            ))}
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <button
            onClick={() => navigate('/drugs')}
            className="card hover:shadow-md transition-shadow text-left cursor-pointer"
          >
            <div className="text-2xl mb-2">💊</div>
            <h3 className="font-semibold text-gray-900">Search Drugs</h3>
            <p className="text-sm text-gray-500 mt-1">Find which plans cover a drug</p>
          </button>
          <button
            onClick={() => navigate('/compare')}
            className="card hover:shadow-md transition-shadow text-left cursor-pointer"
          >
            <div className="text-2xl mb-2">📊</div>
            <h3 className="font-semibold text-gray-900">Compare Policies</h3>
            <p className="text-sm text-gray-500 mt-1">Side-by-side policy comparison</p>
          </button>
          <button
            onClick={() => {/* chatbot placeholder */}}
            className="card hover:shadow-md transition-shadow text-left cursor-pointer opacity-60"
          >
            <div className="text-2xl mb-2">🤖</div>
            <h3 className="font-semibold text-gray-900">AI Assistant</h3>
            <p className="text-sm text-gray-500 mt-1">Ask anything about your coverage</p>
          </button>
        </div>

        {/* My Policies */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            My Policies ({policies.length})
          </h2>
          {policies.length === 0 ? (
            <div className="card text-center text-gray-500 py-12">
              <p className="text-4xl mb-3">📋</p>
              <p>No policies loaded yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {policies.map((p) => (
                <PolicyCard key={p.id} policy={p} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
