import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, loadStoredToken, setAuthToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    loadStoredToken()
    const token = localStorage.getItem('token')
    if (token) {
      api
        .get('/users/me')
        .then((r) => setUser(r.data))
        .catch(() => setAuthToken(null))
        .finally(() => setReady(true))
    } else {
      setReady(true)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    setAuthToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (email, password, full_name) => {
    const { data } = await api.post('/auth/register', { email, password, full_name })
    setAuthToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    setAuthToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      ready,
      isAuthenticated: !!user,
      login,
      register,
      logout,
    }),
    [user, ready, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside provider')
  return ctx
}
