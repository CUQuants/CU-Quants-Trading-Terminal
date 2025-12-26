/**
 * Centralized Logging Utility for Trading Terminal
 * Provides structured logging with levels and timestamps
 */

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

interface LogEntry {
  timestamp: string
  level: LogLevel
  category: string
  message: string
  data?: any
}

class Logger {
  private static instance: Logger
  private logHistory: LogEntry[] = []
  private maxHistorySize = 1000
  private isDevelopment = import.meta.env.DEV

  private constructor() {}

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger()
    }
    return Logger.instance
  }

  /**
   * Format timestamp for logs
   */
  private getTimestamp(): string {
    const now = new Date()
    return now.toISOString()
  }

  /**
   * Get color for log level
   */
  private getColor(level: LogLevel): string {
    switch (level) {
      case LogLevel.DEBUG:
        return 'color: #888'
      case LogLevel.INFO:
        return 'color: #0066CC'
      case LogLevel.WARN:
        return 'color: #FFA500'
      case LogLevel.ERROR:
        return 'color: #FF0000'
    }
  }

  /**
   * Core logging method
   */
  private log(level: LogLevel, category: string, message: string, data?: any): void {
    const entry: LogEntry = {
      timestamp: this.getTimestamp(),
      level,
      category,
      message,
      data,
    }

    // Add to history
    this.logHistory.push(entry)
    if (this.logHistory.length > this.maxHistorySize) {
      this.logHistory.shift()
    }

    // Console output
    const prefix = `[${entry.timestamp}] [${level}] [${category}]`
    const style = this.getColor(level)

    if (data !== undefined) {
      console.log(`%c${prefix} ${message}`, style, data)
    } else {
      console.log(`%c${prefix} ${message}`, style)
    }
  }

  /**
   * Debug level - detailed information for debugging
   */
  public debug(category: string, message: string, data?: any): void {
    if (this.isDevelopment) {
      this.log(LogLevel.DEBUG, category, message, data)
    }
  }

  /**
   * Info level - general information
   */
  public info(category: string, message: string, data?: any): void {
    this.log(LogLevel.INFO, category, message, data)
  }

  /**
   * Warning level - potential issues
   */
  public warn(category: string, message: string, data?: any): void {
    this.log(LogLevel.WARN, category, message, data)
  }

  /**
   * Error level - errors and exceptions
   */
  public error(category: string, message: string, data?: any): void {
    this.log(LogLevel.ERROR, category, message, data)
  }

  /**
   * Get log history
   */
  public getHistory(): LogEntry[] {
    return [...this.logHistory]
  }

  /**
   * Clear log history
   */
  public clearHistory(): void {
    this.logHistory = []
    console.clear()
  }

  /**
   * Export logs as JSON
   */
  public exportLogs(): string {
    return JSON.stringify(this.logHistory, null, 2)
  }

  /**
   * Download logs to file
   */
  public downloadLogs(): void {
    const logs = this.exportLogs()
    const blob = new Blob([logs], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `trading-terminal-logs-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
}

// Export singleton instance
export const logger = Logger.getInstance()

// Convenience exports for specific categories
export const apiLogger = {
  debug: (msg: string, data?: any) => logger.debug('API', msg, data),
  info: (msg: string, data?: any) => logger.info('API', msg, data),
  warn: (msg: string, data?: any) => logger.warn('API', msg, data),
  error: (msg: string, data?: any) => logger.error('API', msg, data),
}

export const wsLogger = {
  debug: (msg: string, data?: any) => logger.debug('WebSocket', msg, data),
  info: (msg: string, data?: any) => logger.info('WebSocket', msg, data),
  warn: (msg: string, data?: any) => logger.warn('WebSocket', msg, data),
  error: (msg: string, data?: any) => logger.error('WebSocket', msg, data),
}

export const uiLogger = {
  debug: (msg: string, data?: any) => logger.debug('UI', msg, data),
  info: (msg: string, data?: any) => logger.info('UI', msg, data),
  warn: (msg: string, data?: any) => logger.warn('UI', msg, data),
  error: (msg: string, data?: any) => logger.error('UI', msg, data),
}
