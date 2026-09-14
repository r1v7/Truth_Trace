import axios from 'axios'

const TOKEN_KEY = 'tt.access'
const REFRESH_KEY = 'tt.refresh'

export const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'}/api`,
})

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string | null> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const refreshToken = localStorage.getItem(REFRESH_KEY)
    if (error.response?.status !== 401 || original?._retried || !refreshToken) {
      throw error
    }
    original._retried = true
    // Collapse concurrent 401s into a single refresh call.
    refreshing ??= api
      .post('/auth/refresh', { refresh_token: refreshToken })
      .then(({ data }) => {
        setTokens(data.access_token, data.refresh_token)
        return data.access_token as string
      })
      .catch(() => {
        clearTokens()
        return null
      })
      .finally(() => {
        refreshing = null
      })

    const token = await refreshing
    if (!token) throw error
    original.headers.Authorization = `Bearer ${token}`
    return api(original)
  },
)
