import { useAuth0 } from '@auth0/auth0-react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { loginWithRedirect, isAuthenticated, isLoading } = useAuth0()
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard')
  }, [isAuthenticated, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-900 to-brand-700">
      <div className="bg-white rounded-2xl shadow-xl p-10 w-full max-w-md text-center">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-900">MedPolicy Tracker</h1>
          <p className="text-gray-500 mt-2 text-sm">Anton Rx | Innovation Hacks 2.0</p>
        </div>
        <p className="text-gray-600 mb-8 text-sm leading-relaxed">
          AI-powered medical benefit drug policy tracking across UnitedHealthcare,
          Cigna, and Aetna.
        </p>
        <button
          onClick={() => loginWithRedirect()}
          disabled={isLoading}
          className="btn-primary w-full text-base py-3"
        >
          {isLoading ? 'Loading...' : 'Sign In'}
        </button>
        <p className="mt-4 text-sm text-gray-500">
          New user?{' '}
          <button
            onClick={() => loginWithRedirect({ screen_hint: 'signup' })}
            className="text-brand-600 font-medium hover:underline"
          >
            Create account
          </button>
        </p>
      </div>
    </div>
  )
}
