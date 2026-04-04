import { useState } from 'react'
import { compareDrugPolicies } from '../api/client'
import NavBar from '../components/Dashboard/NavBar'
import { useAuth0 } from '@auth0/auth0-react'

const PAYERS = ['UnitedHealthcare', 'Cigna', 'Aetna']

export default function Comparison() {
  const { logout } = useAuth0()
  const [drugName, setDrugName] = useState('')
  const [selectedPayers, setSelectedPayers] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const togglePayer = (p) =>
    setSelectedPayers((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    )

  const handleCompare = async (e) => {
    e.preventDefault()
    if (!drugName.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await compareDrugPolicies(
        drugName,
        selectedPayers.length ? selectedPayers : null
      )
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const payerColor = (payer) => {
    if (payer?.includes('United')) return 'text-blue-700'
    if (payer?.includes('Cigna')) return 'text-green-700'
    if (payer?.includes('Aetna')) return 'text-purple-700'
    return 'text-gray-700'
  }

  const payers = result?.rows?.[0]?.values ? Object.keys(result.rows[0].values) : []

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar onLogout={() => logout({ returnTo: window.location.origin })} />

      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Policy Comparison</h1>
        <p className="text-gray-500 text-sm mb-6">
          Compare how different health plans cover the same drug side-by-side.
        </p>

        <form onSubmit={handleCompare} className="card mb-8">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Drug Name</label>
              <input
                value={drugName}
                onChange={(e) => setDrugName(e.target.value)}
                className="input"
                placeholder="e.g. Adalimumab or Humira"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Filter Payers (optional)</label>
              <div className="flex gap-2">
                {PAYERS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => togglePayer(p)}
                    className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors
                      ${selectedPayers.includes(p)
                        ? 'bg-brand-600 text-white border-brand-600'
                        : 'bg-white text-gray-600 border-gray-300 hover:border-brand-400'
                      }`}
                  >
                    {p.replace('UnitedHealthcare', 'UHC')}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <button type="submit" disabled={loading || !drugName.trim()} className="btn-primary mt-4 px-8">
            {loading ? 'Comparing...' : 'Compare Policies'}
          </button>
        </form>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">
            {error}
          </div>
        )}

        {result && (
          <div className="card overflow-x-auto">
            <h2 className="font-semibold text-gray-900 mb-4">
              Comparison: <span className="text-brand-600">{result.drug_name}</span>
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 pr-6 font-semibold text-gray-700 w-48">Criteria</th>
                  {payers.map((p) => (
                    <th key={p} className={`text-left py-3 px-4 font-semibold ${payerColor(p)}`}>
                      {p}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i} className={`border-b ${i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}`}>
                    <td className="py-3 pr-6 font-medium text-gray-700">{row.field}</td>
                    {payers.map((p) => (
                      <td key={p} className="py-3 px-4 text-gray-600">
                        {row.values[p] ?? '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-gray-400 mt-4">
              Generated: {new Date(result.generated_at).toLocaleString()}
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
