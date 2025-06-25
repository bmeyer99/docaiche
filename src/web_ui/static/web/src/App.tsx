import './App.css'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from './context/ToastProvider'
import ErrorBoundary from './components/layout/ErrorBoundary'
import AppLayout from './components/layout/AppLayout'
import ConfigurationPage from './components/configuration/ConfigurationPage'

// Temporary placeholder components until full implementation
const DashboardPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold text-gray-900 mb-4">Dashboard</h1>
    <p className="text-gray-600">Dashboard implementation coming soon...</p>
  </div>
)

const SearchPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold text-gray-900 mb-4">Search Management</h1>
    <p className="text-gray-600">Search management implementation coming soon...</p>
  </div>
)

const ContentPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold text-gray-900 mb-4">Content Management</h1>
    <p className="text-gray-600">Content management implementation coming soon...</p>
  </div>
)

const NotFoundPage = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold text-gray-900 mb-4">404 - Page Not Found</h1>
    <p className="text-gray-600">The page you're looking for doesn't exist.</p>
  </div>
)

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <Router>
          <Routes>
            {/* Root redirect to dashboard */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* All routes use the AppLayout wrapper */}
            <Route path="/" element={<AppLayout />}>
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="search" element={<SearchPage />} />
              <Route path="content" element={<ContentPage />} />
              
              {/* Configuration routes - support both /config and /configuration */}
              <Route path="config" element={<ConfigurationPage />} />
              <Route path="configuration" element={<ConfigurationPage />} />
              
              {/* 404 fallback */}
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </Router>
      </ToastProvider>
    </ErrorBoundary>
  )
}

export default App
