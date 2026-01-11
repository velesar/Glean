import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Review } from './pages/Review'
import { Tools } from './pages/Tools'
import { Jobs } from './pages/Jobs'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="review" element={<Review />} />
          <Route path="tools" element={<Tools />} />
          <Route path="jobs" element={<Jobs />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
