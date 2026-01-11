import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import type { User } from '../types'
import {
  getToken,
  clearToken,
  getCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  getSetupStatus,
} from '../api'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  needsSetup: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [needsSetup, setNeedsSetup] = useState(false)

  const checkAuth = useCallback(async () => {
    setIsLoading(true)
    try {
      // Check if setup is needed
      const setupStatus = await getSetupStatus()
      setNeedsSetup(setupStatus.needs_setup)

      // Check if we have a token
      const token = getToken()
      if (token) {
        const currentUser = await getCurrentUser()
        setUser(currentUser)
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
      clearToken()
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (username: string, password: string) => {
    await apiLogin(username, password)
    await checkAuth()
  }

  const register = async (username: string, email: string, password: string) => {
    await apiRegister(username, email, password)
    // After registration, log them in
    await login(username, password)
  }

  const logout = async () => {
    await apiLogout()
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    needsSetup,
    login,
    register,
    logout,
    checkAuth,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
