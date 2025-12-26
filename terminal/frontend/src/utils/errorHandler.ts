/**
 * Global Error Handler
 * Catches all uncaught errors and promise rejections
 */

import { logger } from './logger'

/**
 * Initialize global error handlers
 */
export function initializeErrorHandlers(): void {
  logger.info('ErrorHandler', '🚀 Initializing global error handlers')

  // Catch uncaught JavaScript errors
  window.addEventListener('error', (event: ErrorEvent) => {
    logger.error('Global', '❌ Uncaught error detected', {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      error: event.error ? {
        name: event.error.name,
        message: event.error.message,
        stack: event.error.stack,
      } : null,
    })

    console.error('❌ UNCAUGHT ERROR:')
    console.error('Message:', event.message)
    console.error('File:', event.filename)
    console.error('Line:', event.lineno, 'Column:', event.colno)
    console.error('Error:', event.error)
  })

  // Catch unhandled promise rejections
  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    logger.error('Global', '❌ Unhandled promise rejection', {
      reason: event.reason,
      reasonString: String(event.reason),
      reasonStack: event.reason?.stack,
    })

    console.error('❌ UNHANDLED PROMISE REJECTION:')
    console.error('Reason:', event.reason)
    
    // Prevent default browser handling
    event.preventDefault()
  })

  // Log console errors
  const originalConsoleError = console.error
  console.error = function(...args: any[]) {
    logger.error('Console', 'Console.error called', { arguments: args })
    originalConsoleError.apply(console, args)
  }

  // Log console warnings
  const originalConsoleWarn = console.warn
  console.warn = function(...args: any[]) {
    logger.warn('Console', 'Console.warn called', { arguments: args })
    originalConsoleWarn.apply(console, args)
  }

  logger.info('ErrorHandler', '✅ Global error handlers initialized successfully')
}

/**
 * Log application startup information
 */
export function logStartupInfo(): void {
  console.log('='.repeat(80))
  console.log('🚀 TRADING TERMINAL STARTING UP')
  console.log('='.repeat(80))

  logger.info('Startup', '📋 Application Information', {
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    cookiesEnabled: navigator.cookieEnabled,
    onLine: navigator.onLine,
    screen: {
      width: window.screen.width,
      height: window.screen.height,
      availWidth: window.screen.availWidth,
      availHeight: window.screen.availHeight,
      colorDepth: window.screen.colorDepth,
    },
    window: {
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio,
    },
    timestamp: new Date().toISOString(),
  })

  logger.info('Startup', '🔧 Environment', {
    mode: import.meta.env.MODE,
    dev: import.meta.env.DEV,
    prod: import.meta.env.PROD,
    baseUrl: import.meta.env.BASE_URL,
  })

  logger.info('Startup', '📦 Browser Features', {
    localStorage: typeof localStorage !== 'undefined',
    sessionStorage: typeof sessionStorage !== 'undefined',
    webSocket: typeof WebSocket !== 'undefined',
    fetch: typeof fetch !== 'undefined',
    crypto: typeof crypto !== 'undefined',
  })

  console.log('='.repeat(80))
  console.log('✅ Startup checks complete. Loading application...')
  console.log('💡 Press Ctrl+Shift+D to open debug panel')
  console.log('💡 Press F12 to open developer console')
  console.log('='.repeat(80))
}

/**
 * Check for common issues that cause black screens
 */
export function checkForCommonIssues(): void {
  logger.info('Startup', '🔍 Running startup diagnostics...')

  const issues: string[] = []

  // Check if DOM is ready
  if (document.readyState === 'loading') {
    issues.push('DOM not ready yet')
  }

  // Check if root element exists
  const root = document.getElementById('root')
  if (!root) {
    issues.push('Root element #root not found in DOM')
    logger.error('Startup', '❌ CRITICAL: Root element not found!', {
      body: document.body.innerHTML,
    })
  }

  // Check localStorage access
  try {
    localStorage.setItem('test', 'test')
    localStorage.removeItem('test')
  } catch (error) {
    issues.push('localStorage not accessible')
    logger.error('Startup', 'localStorage test failed', error)
  }

  // Check if essential modules loaded
  if (typeof React === 'undefined') {
    issues.push('React not loaded')
  }

  if (issues.length > 0) {
    logger.error('Startup', '❌ Issues detected during startup', { issues })
    console.error('❌ STARTUP ISSUES DETECTED:')
    issues.forEach(issue => console.error('  -', issue))
  } else {
    logger.info('Startup', '✅ All startup checks passed')
  }
}

/**
 * Create a loading indicator while app initializes
 */
export function showLoadingIndicator(): void {
  const root = document.getElementById('root')
  if (root && root.children.length === 0) {
    logger.info('Startup', 'Showing loading indicator')
    
    root.innerHTML = `
      <div style="
        width: 100vw;
        height: 100vh;
        background: #000;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        font-family: 'Courier New', monospace;
        color: #fff;
      ">
        <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
        <div style="font-size: 24px; color: #0066CC;">Loading Trading Terminal...</div>
        <div style="font-size: 14px; color: #666; margin-top: 10px;">Initializing components</div>
        <div style="font-size: 12px; color: #666; margin-top: 20px;">Press F12 to view console</div>
      </div>
    `
  }
}

/**
 * Remove loading indicator
 */
export function hideLoadingIndicator(): void {
  logger.info('Startup', 'Hiding loading indicator')
}
