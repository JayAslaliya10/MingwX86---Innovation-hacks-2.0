export default function NotificationBanner({ notification, onDismiss }) {
  const changeColor = (cls) => {
    if (cls === 'coverage') return 'border-red-300 bg-red-50'
    if (cls === 'pa') return 'border-yellow-300 bg-yellow-50'
    if (cls === 'step_therapy') return 'border-orange-300 bg-orange-50'
    return 'border-blue-300 bg-blue-50'
  }

  const changeIcon = (cls) => {
    if (cls === 'coverage') return '⚠️'
    if (cls === 'pa') return '🔒'
    if (cls === 'step_therapy') return '📋'
    return '📢'
  }

  return (
    <div className={`border rounded-xl px-4 py-3 flex items-start justify-between gap-4 ${changeColor(notification.change_class)}`}>
      <div className="flex items-start gap-3">
        <span className="text-lg mt-0.5">{changeIcon(notification.change_class)}</span>
        <div>
          <p className="text-sm font-semibold text-gray-800">
            Policy Update: {notification.policy_title || 'Unknown Policy'}
            {notification.payer_name && (
              <span className="font-normal text-gray-600"> · {notification.payer_name}</span>
            )}
          </p>
          <p className="text-xs text-gray-600 mt-0.5">{notification.diff_summary || 'Policy has been updated.'}</p>
          {notification.effective_from && (
            <p className="text-xs text-gray-500 mt-1">
              Effective: {new Date(notification.effective_from).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
      <button onClick={onDismiss} className="text-gray-400 hover:text-gray-700 text-sm flex-shrink-0">
        ✕
      </button>
    </div>
  )
}
