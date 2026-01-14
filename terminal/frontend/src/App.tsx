import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { MarketProvider } from './contexts/MarketContext'
import Layout from './components/Layout/Layout'
import HomePage from './pages/HomePage'
import TradingPage from './pages/TradingPage'
import SettingsPage from './pages/SettingsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import LogoutPage from './pages/LogoutPage'
import DebugPanel from './components/DebugPanel/DebugPanel'
import { uiLogger } from './utils/logger'

function App() {
  const location = useLocation()

  useEffect(() => {
    uiLogger.info('App: Route changed', { path: location.pathname })
  }, [location])

  useEffect(() => {
    uiLogger.info('App: Application component mounted')
    
    // Log component tree status
    try {
      const hasLayout = !!Layout
      const hasHomePage = !!HomePage
      const hasTradingPage = !!TradingPage
      const hasSettingsPage = !!SettingsPage
      const hasLoginPage = !!LoginPage
      const hasRegisterPage = !!RegisterPage
      const hasLogoutPage = !!LogoutPage
      
      uiLogger.info('App: Component imports verified', {
        Layout: hasLayout,
        HomePage: hasHomePage,
        TradingPage: hasTradingPage,
        SettingsPage: hasSettingsPage,
        LoginPage: hasLoginPage,
        RegisterPage: hasRegisterPage,
        LogoutPage: hasLogoutPage,
      })
    } catch (error) {
      uiLogger.error('App: Failed to verify component imports', error)
    }
    
    return () => {
      uiLogger.info('App: Application component unmounting')
    }
  }, [])

  try {
    uiLogger.debug('App: Rendering application', { path: location.pathname })
    
    return (
      <MarketProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/trading" element={<TradingPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/logout" element={<LogoutPage />} />
          </Routes>
        </Layout>
        <DebugPanel />
      </MarketProvider>
    )
  } catch (error) {
    uiLogger.error('App: Render failed', error)
    throw error
  }
}

export default App
