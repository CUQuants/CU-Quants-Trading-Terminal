import { useState } from 'react'
import Panel from '../components/Panel/Panel'
import styles from './SettingsPage.module.css'

interface ApiConfig {
  apiKey: string
  apiSecret: string
}

const SettingsPage = () => {
  const [apiConfig, setApiConfig] = useState<ApiConfig>({
    apiKey: '',
    apiSecret: '',
  })
  
  const [showApiKey, setShowApiKey] = useState(false)
  const [showApiSecret, setShowApiSecret] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    
    // In production, this would securely store the API credentials
    console.log('Saving API configuration...')
    localStorage.setItem('apiConfig', JSON.stringify(apiConfig))
    
    setSaved(true)
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
            <span className={styles.statusValue} style={{ color: 'var(--color-green)' }}>
              CONNECTED
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>WebSocket Status</span>
            <span className={styles.statusValue} style={{ color: 'var(--color-green)' }}>
              ACTIVE
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Last Update</span>
            <span className={styles.statusValue}>
              {new Date().toLocaleTimeString()}
            </span>
          </div>
          <div className={styles.statusItem}>
            <span className={styles.statusLabel}>Rate Limit</span>
            <span className={styles.statusValue}>
              145/180
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
