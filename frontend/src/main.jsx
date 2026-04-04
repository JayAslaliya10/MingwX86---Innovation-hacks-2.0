import React from 'react'
import ReactDOM from 'react-dom/client'
import { Auth0Provider } from '@auth0/auth0-react'
import App from './App'
import './index.css'

const AUTH0_DOMAIN = import.meta.env.VITE_AUTH0_DOMAIN || 'your-tenant.us.auth0.com'
const AUTH0_CLIENT_ID = import.meta.env.VITE_AUTH0_CLIENT_ID || 'your-client-id'
const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE || 'https://your-api-audience'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Auth0Provider
      domain={AUTH0_DOMAIN}
      clientId={AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: AUTH0_AUDIENCE,
        scope: 'openid profile email',
      }}
    >
      <App />
    </Auth0Provider>
  </React.StrictMode>
)
