import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary/ErrorBoundary'
import './styles/global.css'
import { 
  initializeErrorHandlers, 
  logStartupInfo, 
  checkForCommonIssues,
  showLoadingIndicator,
  hideLoadingIndicator 
} from './utils/errorHandler'
import { logger } from './utils/logger'

// Initialize error handlers FIRST
try {
  console.log('🚀 Initializing error handlers...')
  initializeErrorHandlers()
  console.log('✅ Error handlers initialized')
} catch (error) {
  console.error('❌ Failed to initialize error handlers:', error)
}

// Show loading indicator
try {
  showLoadingIndicator()
} catch (error) {
  console.error('❌ Failed to show loading indicator:', error)
}

// Log startup info
try {
  logStartupInfo()
  checkForCommonIssues()
} catch (error) {
  console.error('❌ Failed to log startup info:', error)
}

// Render application
try {
  logger.info('Startup', '🎨 Rendering React application...')
  
  const rootElement = document.getElementById('root')
  
  if (!rootElement) {
    const errorMsg = '❌ CRITICAL ERROR: Root element #root not found in DOM!'
    console.error(errorMsg)
    logger.error('Startup', errorMsg)
    document.body.innerHTML = `
      <div style="
        width: 100vw;
        height: 100vh;
        background: #000;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        font-family: 'Courier New', monospace;
      ">
        <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
        <div style="font-size: 24px; color: #FF0000;">Critical Error</div>
        <div style="font-size: 16px; color: #888; margin-top: 10px;">Root element not found</div>
        <div style="font-size: 14px; color: #666; margin-top: 20px;">Check index.html for &lt;div id="root"&gt;&lt;/div&gt;</div>
      </div>
    `
    throw new Error('Root element not found')
  }

  logger.info('Startup', '✅ Root element found, creating React root...')
  
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <ErrorBoundary>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ErrorBoundary>
    </React.StrictMode>,
  )
  
  logger.info('Startup', '✅ React application rendered successfully')
  hideLoadingIndicator()
  
  console.log('✅ APPLICATION LOADED SUCCESSFULLY')
  console.log('💡 Press Ctrl+Shift+D to open debug panel')
  
} catch (error) {
  const errorMsg = '❌ CRITICAL ERROR: Failed to render React application'
  console.error(errorMsg, error)
  logger.error('Startup', errorMsg, error)
  
  // Show error screen
  document.body.innerHTML = `
    <div style="
      width: 100vw;
      height: 100vh;
      background: #000;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      font-family: 'Courier New', monospace;
      padding: 20px;
    ">
      <div style="font-size: 48px; margin-bottom: 20px;">❌</div>
      <div style="font-size: 24px; color: #FF0000; text-align: center;">Failed to Load Application</div>
      <div style="font-size: 14px; color: #888; margin-top: 10px; max-width: 600px; text-align: center;">
        ${error instanceof Error ? error.message : String(error)}
      </div>
      <div style="margin-top: 30px;">
        <button onclick="window.location.reload()" style="
          background: #0066CC;
          color: #fff;
          border: 1px solid #fff;
          padding: 15px 30px;
          font-size: 16px;
          font-family: 'Courier New', monospace;
          cursor: pointer;
        ">Reload Page</button>
      </div>
      <div style="font-size: 12px; color: #666; margin-top: 20px;">
        Press F12 to open Developer Console for details
      </div>
    </div>
  `
}
