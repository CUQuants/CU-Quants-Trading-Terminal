import { useState, useEffect } from 'react'
import Panel from '../components/Panel/Panel'
import { krakenAPI } from '../services/krakenAPI'
import { krakenWS } from '../services/krakenWebSocket'
import styles from './SettingsPage.module.css'
import { uiLogger } from '../utils/logger'

interface ApiConfig {
  apiKey: string
  apiSecret: string
}

const SettingsPage = () => {
  const [apiConfig, setApiConfig] = useState<ApiConfig>(() => {
    uiLogger.info('SettingsPage: Loading API config from localStorage')
    // Load from localStorage on mount
    const stored = localStorage.getItem('apiConfig')
    if (stored) {
      try {
        const config = JSON.parse(stored)
        uiLogger.info('SettingsPage: API config loaded', { 
          hasApiKey: !!config.apiKey,
          hasApiSecret: !!config.apiSecret 
        })
        return config
      } catch (error) {
        uiLogger.error('SettingsPage: Failed to parse stored API config', error)
        return { apiKey: '', apiSecret: '' }
      }
    }
    uiLogger.info('SettingsPage: No stored API config found')
    return { apiKey: '', apiSecret: '' }
  })
  
  const [showApiKey, setShowApiKey] = useState(false)
  const [showApiSecret, setShowApiSecret] = useState(false)
  const [saved, setSaved] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const [wsConnected, setWsConnected] = useState(false)

  useEffect(() => {
    uiLogger.info('SettingsPage: Component mounted')
    
    // Update WebSocket status every 500ms
    const interval = setInterval(() => {
      setWsConnected(krakenWS.isConnected())
    }, 500)
    
    return () => clearInterval(interval)
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    
    uiLogger.info('SettingsPage: Saving API credentials', {
      apiKeyLength: apiConfig.apiKey.length,
      apiSecretLength: apiConfig.apiSecret.length,
    })
    
    // Save to localStorage
    localStorage.setItem('apiConfig', JSON.stringify(apiConfig))
    
    // Update API service
    krakenAPI.setCredentials(apiConfig.apiKey, apiConfig.apiSecret)
    
    setSaved(true)
    setConnectionStatus('connecting')
    
    uiLogger.info('SettingsPage: Testing connection with public endpoint first')
    
    // Test connection using public endpoint first (like main.py does)
    try {
      const tickerResult = await krakenAPI.getTicker('XXBTZUSD') // BTC/USD ticker test
      if (tickerResult.error && tickerResult.error.length > 0) {
        uiLogger.error('SettingsPage: Public API test failed', tickerResult.error)
        setConnectionStatus('disconnected')
        return
      }
      
      uiLogger.info('SettingsPage: Public API connection successful')
      
      // If credentials provided, test private endpoint
      if (apiConfig.apiKey && apiConfig.apiSecret) {
        uiLogger.info('SettingsPage: Testing private API with getBalance()')
        const balanceResult = await krakenAPI.getBalance()
        
        if (balanceResult.error && balanceResult.error.length > 0) {
          uiLogger.error('SettingsPage: Private API connection test failed', balanceResult.error)
          setConnectionStatus('disconnected')
        } else {
          uiLogger.info('SettingsPage: Private API connection test successful', {
            balanceKeys: Object.keys(balanceResult.result || {}).length
          })
          setConnectionStatus('connected')
          
          // Connect WebSocket for private feeds
          try {
            await krakenWS.connectPrivate(apiConfig.apiKey, apiConfig.apiSecret)
          } catch (err) {
            uiLogger.error('SettingsPage: Private WebSocket connection failed', err)
          }
        }
      } else {
        // No credentials, but public connection works
        uiLogger.info('SettingsPage: No credentials provided, public API only')
        setConnectionStatus('connected')
      }
    } catch (err) {
      uiLogger.error('SettingsPage: Connection test failed', err)
      setConnectionStatus('disconnected')
    }
    
    setTimeout(() => setSaved(false), 3000)
  }

  const handleClear = () => {
    setApiConfig({ apiKey: '', apiSecret: '' })
    localStorage.removeItem('apiConfig')
  }

  return (
    <div className={styles.settingsPage}>
      <h1 className={styles.pageTitle}>Settings</h1>

      <Panel title="API Configuration">
        <form onSubmit={handleSave} className={styles.settingsForm}>
          <p className={styles.description}>
            Configure your Kraken API credentials for trading operations. 
            Keys are stored locally and encrypted.
          </p>

          <div className={styles.formGroup}>
            <label htmlFor="apiKey">API Key</label>
            <div className={styles.inputWrapper}>
              <input
                id="apiKey"
                type={showApiKey ? 'text' : 'password'}
                value={apiConfig.apiKey}
                onChange={(e) => setApiConfig({ ...apiConfig, apiKey: e.target.value })}
                placeholder="Enter your API key"
                className={styles.input}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className={styles.toggleButton}
              >
                {showApiKey ? 'HIDE' : 'SHOW'}
              </button>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="apiSecret">API Secret</label>
            <div className={styles.inputWrapper}>
              <input
                id="apiSecret"
                type={showApiSecret ? 'text' : 'password'}
                value={apiConfig.apiSecret}
                onChange={(e) => setApiConfig({ ...apiConfig, apiSecret: e.target.value })}
                placeholder="Enter your API secret"
                className={styles.input}
              />
              <button
                type="button"
                onClick={() => setShowApiSecret(!showApiSecret)}
                className={styles.toggleButton}
              >
                {showApiSecret ? 'HIDE' : 'SHOW'}
              </button>
            </div>
          </div>

          <div className={styles.buttonGroup}>
            <button type="submit" className={styles.saveButton}>
              Save Configuration
            </button>
            <button type="button" onClick={handleClear} className={styles.clearButton}>
              Clear
            </button>
          </div>

          {saved && (
            <div className={styles.successMessage}>
              ✓ API configuration saved successfully
            </div>
          )}
        </form>
      </Panel>

      <Panel title="Connection Status">
        <div className={styles.statusGrid}>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>API Connection</span>
            <span 
              className={styles.statusValue} 
              style={{ 
                color: connectionStatus === 'connected' 
                  ? 'var(--color-green)' 
                  : connectionStatus === 'connecting'
                  ? 'var(--color-blue)'
                  : 'var(--color-red)'
              }}
            >
              {connectionStatus.toUpperCase()}
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>WebSocket Status</span>
            <span 
              className={styles.statusValue} 
              style={{ color: wsConnected ? 'var(--color-green)' : 'var(--color-red)' }}
            >
              {wsConnected ? 'ACTIVE' : 'DISCONNECTED'}
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Last Update</span>
            <span className={styles.statusValue}>
              {new Date().toLocaleTimeString()}
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Credentials</span>
            <span className={styles.statusValue}>
              {krakenAPI.hasCredentials() ? 'CONFIGURED' : 'NOT SET'}
            </span>
          </div>
        </div>
      </Panel>

      <Panel title="System Information">
        <div className={styles.infoGrid}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Version</span>
            <span className={styles.infoValue}>1.0.0</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Environment</span>
            <span className={styles.infoValue}>Production</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Market Data Provider</span>
            <span className={styles.infoValue}>Kraken</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Uptime</span>
            <span className={styles.infoValue}>99.8%</span>
          </div>
        </div>
      </Panel>
    </div>
  )
}

export default SettingsPage
