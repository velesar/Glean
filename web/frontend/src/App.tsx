import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Review } from './pages/Review'
import { Tools } from './pages/Tools'
import { Jobs } from './pages/Jobs'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="review" element={<Review />} />
        <Route path="tools" element={<Tools />} />
        <Route path="jobs" element={<Jobs />} />
      </Route>
    </Routes>
  )
}

export default App
