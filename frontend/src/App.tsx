import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import Overview from './pages/Overview'
import DiscoverJobs from './pages/DiscoverJobs'
import Agents from './pages/Agents'
import Applications from './pages/Applications'
import ResumeStudio from './pages/ResumeStudio'
import Automation from './pages/Automation'
import Analytics from './pages/Analytics'
import SettingsPage from './pages/Settings'
import Discovery from './pages/Discovery'
import AutoApply from './pages/AutoApply'

// Backend-backed workflow pages. They are not in the primary sidebar, but they
// hold working API flows (preparation, cover letters, follow-ups, profile) that
// the primary pages deep-link into, so they stay reachable.
import Apply from './pages/Apply'
import CoverLetter from './pages/CoverLetter'
import FollowUps from './pages/FollowUps'
import Profile from './pages/Profile'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/discover" element={<DiscoverJobs />} />
        {/* Superseded by /discover; kept as a redirect for existing links. */}
        <Route path="/jobs" element={<Navigate to="/discover" replace />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/applications" element={<Applications />} />
        <Route path="/resumes" element={<ResumeStudio />} />
        <Route path="/automation" element={<Automation />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/discovery" element={<Discovery />} />
        <Route path="/auto-apply" element={<AutoApply />} />

        <Route path="/apply" element={<Apply />} />
        <Route path="/cover-letter" element={<CoverLetter />} />
        <Route path="/follow-ups" element={<FollowUps />} />
        <Route path="/profile" element={<Profile />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

export default App