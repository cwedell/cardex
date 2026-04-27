import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CarDataProvider, CarDataContext } from './context/CarDataContext'
import { DashboardPage }   from './pages/DashboardPage'
import { SpotPage }        from './pages/SpotPage'
import { CollectionPage }  from './pages/CollectionPage'
import { ProfilePage }     from './pages/ProfilePage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { ChallengesPage }  from './pages/ChallengesPage'
import { initUser }        from './lib/storage'
import { useContext }      from 'react'
import { AlertCircle }     from 'lucide-react'

// Ensure the default user is seeded on first load
initUser()

function AppRoutes() {
  const { loading, error } = useContext(CarDataContext)

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-zinc-400 text-sm">Loading Cardex…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
        <div className="max-w-sm text-center">
          <AlertCircle className="mx-auto mb-3 text-red-400" size={36} />
          <h1 className="text-lg font-bold mb-2">Setup Required</h1>
          <p className="text-zinc-400 text-sm whitespace-pre-wrap leading-relaxed">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/"            element={<DashboardPage />}   />
          <Route path="/spot"        element={<SpotPage />}        />
          <Route path="/collection"  element={<CollectionPage />}  />
          <Route path="/challenges"  element={<ChallengesPage />}  />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/profile"     element={<ProfilePage />}     />
          <Route path="*"            element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </HashRouter>
  )
}

export default function App() {
  return (
    <CarDataProvider>
      <AppRoutes />
    </CarDataProvider>
  )
}
