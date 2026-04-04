import { useState } from 'react'
import { whichPlansCover, getDrugCoverage, listDrugs } from '../api/client'
import NavBar from '../components/Dashboard/NavBar'
import { useAuth0 } from '@auth0/auth0-react'

export default function DrugSearch() {
  const { logout } = useAuth0()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await whichPlansCover(query)
      setResults(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const payerColor = (payer) => {
    if (payer?.includes('United')) return 'bg-blue-100 text-blue-800'
    if (payer?.includes('Cigna')) return 'bg-green-100 text-green-800'
    if (payer?.includes('Aetna')) return 'bg-purple-100 text-purple-800'
    return 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar onLogout={() => logout({ returnTo: window.location.origin })} />

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Drug Coverage Search</h1>
        <p className="text-gray-500 text-sm mb-6">
          Search to find which health plans cover a specific drug under their medical benefit.
        </p>

        <form onSubmit={handleSearch} className="flex gap-3 mb-8">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="input flex-1"
            placeholder="e.g. Adalimumab, Humira, J0135..."
          />
          <button type="submit" disabled={loading} className="btn-primary px-8">
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">
            {error}
          </div>
        )}

        {results && (
          <div>
            <h2 className="font-semibold text-gray-800 mb-4">
              Results for "{results.drug}" — {results.plans.length} plan{results.plans.length !== 1 ? 's' : ''} found
            </h2>

            {results.plans.length === 0 ? (
              <div className="card text-center text-gray-500 py-10">
                <p className="text-3xl mb-2">🔍</p>
                <p>No plans found covering this drug in our knowledge base.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {results.plans.map((plan, i) => (
                  <div key={i} className="card">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className={`badge ${payerColor(plan.payer)} mb-2`}>{plan.payer}</span>
                        <h3 className="font-semibold text-gray-900">{plan.policy_title || 'Medical Drug Policy'}</h3>
                        <p className="text-sm text-gray-500 mt-1">
                          {plan.drug_name} {plan.brand_name ? `(${plan.brand_name})` : ''}
                          {plan.hcpcs_code ? ` · HCPCS: ${plan.hcpcs_code}` : ''}
                        </p>
                      </div>
                      <span className="badge bg-green-100 text-green-800">Covered</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
