/**
 * Kraken WebSocket Service
 * Manages real-time market data and private feeds
 */

import { wsLogger } from '../utils/logger'

const KRAKEN_WS_PUBLIC = 'wss://ws.kraken.com'
const KRAKEN_WS_PRIVATE = 'wss://ws-auth.kraken.com'

export type TickerUpdate = {
  pair: string
  bid: string
  ask: string
  last: string
  volume: string
  high: string
  low: string
  change: string
  changePercent: string
}

export type OrderBookUpdate = {
  pair: string
  bids: Array<[string, string, string]> // [price, volume, timestamp]
  asks: Array<[string, string, string]>
}

export type OrderUpdate = {
  orderId: string
  status: string
  pair: string
  type: 'buy' | 'sell'
  orderType: string
  price: string
  volume: string
  volumeExecuted: string
}

type SubscriptionCallback = (data: any) => void

interface PendingSubscription {
  type: string
  pairs: string[]
}

class KrakenWebSocketService {
  private ws: WebSocket | null = null
  private privateWs: WebSocket | null = null
  private reconnectTimeout: NodeJS.Timeout | null = null
  private heartbeatInterval: NodeJS.Timeout | null = null
  private subscriptions = new Map<string, Set<SubscriptionCallback>>()
  private pendingSubscriptions: PendingSubscription[] = []
  private isConnecting = false
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  /**
   * Connect to public WebSocket feed
   */
  public connectPublic(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (this.isConnecting) {
        wsLogger.warn('Connection already in progress, rejecting duplicate connection attempt')
        reject(new Error('Connection already in progress'))
        return
      }

      wsLogger.info('Initiating WebSocket connection', { url: KRAKEN_WS_PUBLIC })
      this.isConnecting = true
      this.ws = new WebSocket(KRAKEN_WS_PUBLIC)

      this.ws.onopen = () => {
        wsLogger.info('✅ WebSocket connected successfully (public)')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.startHeartbeat()
        this.processPendingSubscriptions()
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          wsLogger.debug('WebSocket message received', { 
            dataType: Array.isArray(data) ? 'array' : typeof data,
            length: JSON.stringify(data).length 
          })
          this.handleMessage(data)
        } catch (error) {
          wsLogger.error('Failed to parse WebSocket message', error)
        }
      }

      this.ws.onerror = (error) => {
        wsLogger.error('WebSocket error occurred', error)
        this.isConnecting = false
        reject(error)
      }

      this.ws.onclose = () => {
        wsLogger.warn('WebSocket connection closed')
        this.isConnecting = false
        this.stopHeartbeat()
        this.attemptReconnect()
      }
    })
  }

  /**
   * Connect to private WebSocket feed (for order updates)
   */
  public async connectPrivate(apiKey: string, apiSecret: string): Promise<void> {
    // Get WebSocket token first
    const token = await this.getWebSocketToken(apiKey, apiSecret)
    
    return new Promise((resolve, reject) => {
      if (this.privateWs?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.privateWs = new WebSocket(KRAKEN_WS_PRIVATE)

      this.privateWs.onopen = () => {
        console.log('✅ WebSocket connected (private)')
        
        // Authenticate with token
        this.privateWs?.send(JSON.stringify({
          event: 'subscribe',
          subscription: { name: 'openOrders', token },
        }))

        resolve()
      }

      this.privateWs.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handlePrivateMessage(data)
        } catch (error) {
          console.error('Failed to parse private WebSocket message:', error)
        }
      }

      this.privateWs.onerror = (error) => {
        console.error('Private WebSocket error:', error)
        reject(error)
      }

      this.privateWs.onclose = () => {
        console.warn('Private WebSocket disconnected')
      }
    })
  }

  /**
   * Get WebSocket authentication token
   */
  private async getWebSocketToken(apiKey: string, apiSecret: string): Promise<string> {
    // This would call the GetWebSocketsToken endpoint
    // For now, return empty - implement when needed
    return ''
  }

  /**
   * Subscribe to ticker updates for specific pairs
   */
  public subscribeTicker(pairs: string[], callback: SubscriptionCallback): void {
    wsLogger.info('Subscribing to ticker updates', { pairs, pairCount: pairs.length })
    
    // Store callback first (so we don't lose it if connection is still establishing)
    pairs.forEach(pair => {
      if (!this.subscriptions.has(`ticker:${pair}`)) {
        this.subscriptions.set(`ticker:${pair}`, new Set())
      }
      this.subscriptions.get(`ticker:${pair}`)?.add(callback)
    })
    
    wsLogger.debug('Ticker callbacks registered', { 
      totalSubscriptions: this.subscriptions.size 
    })
    
    // Check if WebSocket is ready before sending
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      wsLogger.warn('Cannot subscribe yet - WebSocket not open, will retry when connected', {
        state: this.ws?.readyState,
        stateString: this.getReadyStateString(this.ws?.readyState),
        pairs,
      })
      
      // Queue subscription to send when connection opens
      this.queueSubscription('ticker', pairs)
      return
    }
    
    const subscription = {
      event: 'subscribe',
      pair: pairs,
      subscription: { name: 'ticker' },
    }

    try {
      this.ws.send(JSON.stringify(subscription))
      wsLogger.debug('Ticker subscription request sent successfully', { pairs })
    } catch (error) {
      wsLogger.error('Failed to send ticker subscription', error)
    }
  }

  /**
   * Subscribe to order book updates
   */
  public subscribeOrderBook(pairs: string[], depth: number = 10, callback: SubscriptionCallback): void {
    const subscription = {
      event: 'subscribe',
      pair: pairs,
      subscription: { name: 'book', depth },
    }

    this.ws?.send(JSON.stringify(subscription))

    pairs.forEach(pair => {
      if (!this.subscriptions.has(`book:${pair}`)) {
        this.subscriptions.set(`book:${pair}`, new Set())
      }
      this.subscriptions.get(`book:${pair}`)?.add(callback)
    })
  }

  /**
   * Subscribe to trade updates
   */
  public subscribeTrades(pairs: string[], callback: SubscriptionCallback): void {
    const subscription = {
      event: 'subscribe',
      pair: pairs,
      subscription: { name: 'trade' },
    }

    this.ws?.send(JSON.stringify(subscription))

    pairs.forEach(pair => {
      if (!this.subscriptions.has(`trade:${pair}`)) {
        this.subscriptions.set(`trade:${pair}`, new Set())
      }
      this.subscriptions.get(`trade:${pair}`)?.add(callback)
    })
  }

  /**
   * Unsubscribe from updates
   */
  public unsubscribe(type: string, pairs: string[]): void {
    wsLogger.info('Unsubscribing from updates', { type, pairs })
    
    // Check if WebSocket is ready before sending
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      wsLogger.warn('Cannot unsubscribe - WebSocket not open', {
        type,
        pairs,
        state: this.ws?.readyState,
        stateString: this.getReadyStateString(this.ws?.readyState),
      })
      
      // Still clean up local subscriptions
      pairs.forEach(pair => {
        this.subscriptions.delete(`${type}:${pair}`)
      })
      return
    }
    
    const subscription = {
      event: 'unsubscribe',
      pair: pairs,
      subscription: { name: type },
    }

    try {
      this.ws.send(JSON.stringify(subscription))
      wsLogger.debug('Unsubscribe request sent successfully', { type, pairs })
    } catch (error) {
      wsLogger.error('Failed to send unsubscribe request', error)
    }

    pairs.forEach(pair => {
      this.subscriptions.delete(`${type}:${pair}`)
    })
  }

  /**
   * Queue a subscription to be sent when WebSocket connects
   */
  private queueSubscription(type: string, pairs: string[]): void {
    wsLogger.debug('Queueing subscription for when connection opens', { type, pairs })
    this.pendingSubscriptions.push({ type, pairs })
  }

  /**
   * Process pending subscriptions after connection opens
   */
  private processPendingSubscriptions(): void {
    if (this.pendingSubscriptions.length === 0) {
      return
    }

    wsLogger.info('Processing pending subscriptions', {
      count: this.pendingSubscriptions.length,
    })

    const subscriptionsToProcess = [...this.pendingSubscriptions]
    this.pendingSubscriptions = []

    subscriptionsToProcess.forEach(sub => {
      wsLogger.debug('Sending queued subscription', sub)
      
      const subscription = {
        event: 'subscribe',
        pair: sub.pairs,
        subscription: { name: sub.type },
      }

      try {
        this.ws?.send(JSON.stringify(subscription))
      } catch (error) {
        wsLogger.error('Failed to send queued subscription', error)
        // Re-queue if failed
        this.pendingSubscriptions.push(sub)
      }
    })
  }

  /**
   * Helper to get readable WebSocket state
   */
  private getReadyStateString(state: number | undefined): string {
    if (state === undefined) return 'UNDEFINED'
    switch (state) {
      case WebSocket.CONNECTING: return 'CONNECTING (0)'
      case WebSocket.OPEN: return 'OPEN (1)'
      case WebSocket.CLOSING: return 'CLOSING (2)'
      case WebSocket.CLOSED: return 'CLOSED (3)'
      default: return `UNKNOWN (${state})`
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: any): void {
    // System messages
    if (data.event) {
      if (data.event === 'heartbeat') {
        wsLogger.debug('Heartbeat received')
        return
      }

      if (data.event === 'systemStatus') {
        wsLogger.info('System status update', {
          status: data.status,
          version: data.version,
        })
        return
      }

      if (data.event === 'subscriptionStatus') {
        if (data.status === 'subscribed') {
          wsLogger.info('Subscription confirmed', {
            channel: data.channelName,
            pair: data.pair,
          })
        } else if (data.status === 'error') {
          wsLogger.error('Subscription error', {
            errorMessage: data.errorMessage,
          })
        }
        return
      }

      wsLogger.debug('System event received', { event: data.event })
      return
    }

    // Data messages are arrays
    if (Array.isArray(data)) {
      const [channelID, messageData, channelName, pair] = data

      if (channelName === 'ticker') {
        this.handleTickerUpdate(pair, messageData)
      } else if (channelName === 'book-10' || channelName === 'book-25') {
        this.handleOrderBookUpdate(pair, messageData)
      } else if (channelName === 'trade') {
        this.handleTradeUpdate(pair, messageData)
      }
    }
  }

  /**
   * Handle private WebSocket messages
   */
  private handlePrivateMessage(data: any): void {
    if (Array.isArray(data) && data[1] === 'openOrders') {
      const callbacks = this.subscriptions.get('openOrders')
      if (callbacks) {
        callbacks.forEach(cb => cb(data[0]))
      }
    }
  }

  /**
   * Handle ticker updates
   */
  private handleTickerUpdate(pair: string, data: any): void {
    const tickerData: TickerUpdate = {
      pair,
      bid: data.b[0],
      ask: data.a[0],
      last: data.c[0],
      volume: data.v[1],
      high: data.h[1],
      low: data.l[1],
      change: String(parseFloat(data.c[0]) - parseFloat(data.o)),
      changePercent: String(((parseFloat(data.c[0]) - parseFloat(data.o)) / parseFloat(data.o)) * 100),
    }

    const callbacks = this.subscriptions.get(`ticker:${pair}`)
    if (callbacks) {
      callbacks.forEach(cb => cb(tickerData))
    }
  }

  /**
   * Handle order book updates
   */
  private handleOrderBookUpdate(pair: string, data: any): void {
    const bookData: OrderBookUpdate = {
      pair,
      bids: data.b || data.bs || [],
      asks: data.a || data.as || [],
    }

    const callbacks = this.subscriptions.get(`book:${pair}`)
    if (callbacks) {
      callbacks.forEach(cb => cb(bookData))
    }
  }

  /**
   * Handle trade updates
   */
  private handleTradeUpdate(pair: string, data: any): void {
    const callbacks = this.subscriptions.get(`trade:${pair}`)
    if (callbacks) {
      callbacks.forEach(cb => cb({ pair, trades: data }))
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ event: 'ping' }))
      }
    }, 30000) // Every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    this.reconnectAttempts++

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimeout = setTimeout(() => {
      this.connectPublic().catch(error => {
        console.error('Reconnection failed:', error)
      })
    }, delay)
  }

  /**
   * Disconnect from WebSocket
   */
  public disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    if (this.privateWs) {
      this.privateWs.close()
      this.privateWs = null
    }

    this.subscriptions.clear()
  }

  /**
   * Get connection status
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Export singleton instance
export const krakenWS = new KrakenWebSocketService()
