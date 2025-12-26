import React, { Component, ErrorInfo, ReactNode } from 'react'
import { logger } from '../../utils/logger'
import styles from './ErrorBoundary.module.css'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * Error Boundary Component
 * Catches React errors and displays them with detailed logging
 */
class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    logger.error('ErrorBoundary', 'React error caught by ErrorBoundary', {
      message: error.message,
      stack: error.stack,
    })
    
    return {
      hasError: true,
      error,
      errorInfo: null,
    }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    logger.error('ErrorBoundary', 'Component stack trace', {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      componentStack: errorInfo.componentStack,
    })

    console.error('❌ REACT ERROR CAUGHT BY ERROR BOUNDARY')
    console.error('Error:', error)
    console.error('Error Info:', errorInfo)

    this.setState({
      errorInfo,
    })
  }

  private handleReset = () => {
    logger.info('ErrorBoundary', 'User clicked reset button')
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
    // Reload the page
    window.location.reload()
  }

  private handleDownloadLogs = () => {
    logger.info('ErrorBoundary', 'User downloading error logs')
    logger.downloadLogs()
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className={styles.errorBoundary}>
          <div className={styles.errorContainer}>
            <div className={styles.errorIcon}>⚠️</div>
            <h1 className={styles.errorTitle}>Application Error</h1>
            <p className={styles.errorMessage}>
              Something went wrong. The error has been logged for debugging.
            </p>

            {this.state.error && (
              <div className={styles.errorDetails}>
                <h2>Error Details:</h2>
                <div className={styles.errorBox}>
                  <strong>{this.state.error.name}:</strong> {this.state.error.message}
                </div>
                
                {this.state.error.stack && (
                  <details className={styles.stackTrace}>
                    <summary>Stack Trace</summary>
                    <pre>{this.state.error.stack}</pre>
                  </details>
                )}

                {this.state.errorInfo && (
                  <details className={styles.stackTrace}>
                    <summary>Component Stack</summary>
                    <pre>{this.state.errorInfo.componentStack}</pre>
                  </details>
                )}
              </div>
            )}

            <div className={styles.actions}>
              <button onClick={this.handleReset} className={styles.button}>
                Reload Application
              </button>
              <button onClick={this.handleDownloadLogs} className={styles.buttonSecondary}>
                Download Error Logs
              </button>
            </div>

            <div className={styles.help}>
              <p>Need help? Try these steps:</p>
              <ol>
                <li>Press F12 to open Developer Console</li>
                <li>Check the Console tab for detailed error messages</li>
                <li>Download error logs using the button above</li>
                <li>Clear your browser cache and reload</li>
              </ol>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
