import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach Auth0 token to every request
export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// ─── User ──────────────────────────────────────────────────────────────────
export const registerUser = (data) => api.post('/users/register', data)
export const getMe = () => api.get('/users/me')
export const onLogin = () => api.post('/users/login')
export const getNotifications = () => api.get('/users/notifications')
export const markNotificationSeen = (id) => api.patch(`/users/notifications/${id}/seen`)
export const lookupHealthCard = () => api.get('/users/health-card')

// ─── Policies ──────────────────────────────────────────────────────────────
export const listMyPolicies = () => api.get('/policies/')
export const getPolicy = (id) => api.get(`/policies/${id}`)
export const uploadPolicies = (files) => {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  return api.post('/policies/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ─── Drugs ─────────────────────────────────────────────────────────────────
export const listDrugs = (params) => api.get('/drugs/', { params })
export const getDrugCoverage = (drugId) => api.get(`/drugs/${drugId}/coverage`)
export const getDrugPriorAuth = (drugId) => api.get(`/drugs/${drugId}/prior-auth`)
export const whichPlansCover = (drugName) =>
  api.get('/drugs/search/which-plans-cover', { params: { drug_name: drugName } })

// ─── Comparison ────────────────────────────────────────────────────────────
export const compareDrugPolicies = (drugName, payerNames) =>
  api.post('/compare/', { drug_name: drugName, payer_names: payerNames })
export const getCachedComparison = (drugName) => api.get(`/compare/${drugName}`)

// ─── Chat ──────────────────────────────────────────────────────────────────
export const chatHttp = (message, sessionId) =>
  api.post('/chat/', { message, session_id: sessionId })

export default api
