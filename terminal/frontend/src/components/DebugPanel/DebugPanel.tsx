import { useState, useEffect } from 'react'
import { logger } from '../../utils/logger'
import styles from './DebugPanel.module.css'

/**
 * Debug Panel Component
 * Displays recent logs in a collapsible panel
 * Press Ctrl+Shift+D to toggle
 */
const DebugPanel = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [logs, setLogs] = useState(logger.getHistory())

  useEffect(() => {
    // Update logs every second
    const interval = setInterval(() => {
      setLogs(logger.getHistory())
    }, 1000)

    // Keyboard shortcut: Ctrl+Shift+D
    const handleKeyboard = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault()
        setIsOpen(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyboard)

    return () => {
      clearInterval(interval)
      window.removeEventListener('keydown', handleKeyboard)
    }
  }, [])

  const handleClear = () => {
    logger.clearHistory()
    setLogs([])
  }

  const handleDownload = () => {
    logger.downloadLogs()
  }

  if (!isOpen) {
    return (
      <div className={styles.toggleButton} onClick={() => setIsOpen(true)}>
        🐛 Debug
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>Debug Console</h3>
        <div className={styles.actions}>
          <button onClick={handleClear} className={styles.button}>Clear</button>
          <button onClick={handleDownload} className={styles.button}>Download</button>
          <button onClick={() => setIsOpen(false)} className={styles.button}>Close</button>
        </div>
      </div>
      
      <div className={styles.logContainer}>
        {logs.slice(-100).reverse().map((log, index) => (
          <div key={index} className={`${styles.logEntry} ${styles[log.level.toLowerCase()]}`}>
            <span className={styles.timestamp}>{new Date(log.timestamp).toLocaleTimeString()}</span>
            <span className={styles.level}>{log.level}</span>
            <span className={styles.category}>{log.category}</span>
            <span className={styles.message}>{log.message}</span>
            {log.data && (
              <pre className={styles.data}>{JSON.stringify(log.data, null, 2)}</pre>
            )}
          </div>
        ))}
        
        {logs.length === 0 && (
          <div className={styles.empty}>No logs yet. Start using the application!</div>
        )}
      </div>
      
      <div className={styles.footer}>
        <span>{logs.length} total logs</span>
        <span>Press Ctrl+Shift+D to toggle</span>
      </div>
    </div>
  )
}

export default DebugPanel
