import { Link, useLocation } from 'react-router-dom'

export default function NavBar({ user, onLogout }) {
  const location = useLocation()
  const isActive = (path) => location.pathname === path

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-16">
        <div className="flex items-center gap-8">
          <Link to="/dashboard" className="font-bold text-brand-900 text-lg">
            MedPolicy<span className="text-brand-600">Tracker</span>
          </Link>
          <div className="hidden sm:flex items-center gap-1">
            {[
              { path: '/dashboard', label: 'Dashboard' },
              { path: '/drugs', label: 'Drug Search' },
              { path: '/compare', label: 'Compare' },
            ].map(({ path, label }) => (
              <Link
                key={path}
                to={path}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors
                  ${isActive(path)
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
              >
                {label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user && (
            <span className="text-sm text-gray-600 hidden sm:block">{user.full_name}</span>
          )}
          <button onClick={onLogout} className="btn-secondary text-sm py-1.5">
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  )
}
