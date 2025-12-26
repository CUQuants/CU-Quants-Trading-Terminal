import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout/Layout'
import HomePage from './pages/HomePage'
import TradingPage from './pages/TradingPage'
import SettingsPage from './pages/SettingsPage'
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
      
      uiLogger.info('App: Component imports verified', {
        Layout: hasLayout,
        HomePage: hasHomePage,
        TradingPage: hasTradingPage,
        SettingsPage: hasSettingsPage,
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
      <>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/trading" element={<TradingPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Layout>
        <DebugPanel />
      </>
    )
  } catch (error) {
    uiLogger.error('App: Render failed', error)
    throw error
  }
}

export default App
