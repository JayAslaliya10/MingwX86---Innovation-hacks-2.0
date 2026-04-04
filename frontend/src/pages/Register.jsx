import { useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { useNavigate } from 'react-router-dom'
import { registerUser, onLogin } from '../api/client'

export default function Register() {
  const { user: auth0User } = useAuth0()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: auth0User?.name || '',
    email: auth0User?.email || '',
    phone: '',
    address: '',
    health_card_number: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const payload = {
        ...form,
        health_card_number: form.health_card_number.trim() || null,
      }
      await registerUser(payload)
      await onLogin()

      // Route based on health card presence
      if (payload.health_card_number) {
        navigate('/dashboard')
      } else {
        navigate('/upload')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="card w-full max-w-lg">
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Complete Registration</h2>
        <p className="text-gray-500 text-sm mb-6">
          Enter your details to set up your MedPolicy Tracker account.
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
            <input
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
              className="input"
              placeholder="Jane Smith"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              required
              className="input"
              placeholder="jane@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
            <input
              name="phone"
              value={form.phone}
              onChange={handleChange}
              className="input"
              placeholder="+1 (555) 000-0000"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
            <textarea
              name="address"
              value={form.address}
              onChange={handleChange}
              className="input resize-none"
              rows={2}
              placeholder="123 Main St, Phoenix, AZ 85001"
            />
          </div>

          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Health Card Number{' '}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              name="health_card_number"
              value={form.health_card_number}
              onChange={handleChange}
              className="input"
              placeholder="e.g. UHC-1001-2024"
            />
            <p className="text-xs text-gray-500 mt-1">
              If you have a health card number, your policies will be loaded automatically.
              If not, you will be asked to upload your policy documents.
            </p>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full py-3 mt-2">
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
