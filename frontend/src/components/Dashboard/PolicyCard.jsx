export default function PolicyCard({ policy }) {
  const payerColor = (payer) => {
    if (payer?.includes('United')) return 'bg-blue-100 text-blue-800'
    if (payer?.includes('Cigna')) return 'bg-green-100 text-green-800'
    if (payer?.includes('Aetna')) return 'bg-purple-100 text-purple-800'
    return 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <span className={`badge ${payerColor(policy.payer)}`}>
          {policy.payer || 'Unknown Payer'}
        </span>
        <span className={`badge ${policy.source === 'system' ? 'bg-indigo-100 text-indigo-700' : 'bg-yellow-100 text-yellow-700'}`}>
          {policy.source === 'system' ? 'System' : 'Uploaded'}
        </span>
      </div>
      <h3 className="font-semibold text-gray-900 text-sm leading-snug">
        {policy.title || 'Medical Drug Policy'}
      </h3>
      {policy.drug_family && (
        <p className="text-xs text-gray-500 mt-1">Family: {policy.drug_family}</p>
      )}
      {policy.policy_type && (
        <p className="text-xs text-gray-500">Type: {policy.policy_type}</p>
      )}
      {policy.effective_date && (
        <p className="text-xs text-gray-400 mt-2">
          Effective: {new Date(policy.effective_date).toLocaleDateString()}
        </p>
      )}
    </div>
  )
}
