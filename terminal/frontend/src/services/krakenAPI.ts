import CryptoJS from 'crypto-js'
import { apiLogger } from '../utils/logger'

// Kraken API Configuration
const KRAKEN_API_BASE = 'https://api.kraken.com'
const KRAKEN_WS_PUBLIC = 'wss://ws.kraken.com'
const KRAKEN_WS_PRIVATE = 'wss://ws-auth.kraken.com'

// API Rate Limiting
const API_RATE_LIMIT = {
  maxCalls: 15,
  windowMs: 3000,
  callTimestamps: [] as number[],
}

export interface KrakenAPIConfig {
  apiKey: string
  apiSecret: string
}

export interface KrakenResponse<T = any> {
  error: string[]
  result?: T
}

export interface OrderBookEntry {
  price: string
  volume: string
  timestamp: number
}

export interface OrderBook {
  asks: OrderBookEntry[]
  bids: OrderBookEntry[]
}

export interface TickerInfo {
  a: [string, string, string] // ask [price, whole lot volume, lot volume]
  b: [string, string, string] // bid [price, whole lot volume, lot volume]
  c: [string, string] // last trade closed [price, lot volume]
  v: [string, string] // volume [today, last 24 hours]
  p: [string, string] // volume weighted average price [today, last 24 hours]
  t: [number, number] // number of trades [today, last 24 hours]
  l: [string, string] // low [today, last 24 hours]
  h: [string, string] // high [today, last 24 hours]
  o: string // today's opening price
}

export interface OpenOrder {
  refid: string
  userref: number
  status: string
  opentm: number
  starttm: number
  expiretm: number
  descr: {
    pair: string
    type: 'buy' | 'sell'
    ordertype: string
    price: string
    price2: string
    leverage: string
    order: string
    close: string
  }
  vol: string
  vol_exec: string
  cost: string
  fee: string
  price: string
  stopprice: string
  limitprice: string
  misc: string
  oflags: string
}

class KrakenAPIService {
  private apiKey: string | null = null
  private apiSecret: string | null = null

  constructor() {
    this.loadCredentials()
  }

  /**
   * Load API credentials from localStorage
   */
  private loadCredentials(): void {
    apiLogger.debug('Loading API credentials from localStorage')
    try {
      const stored = localStorage.getItem('apiConfig')
      if (stored) {
        const config = JSON.parse(stored)
        this.apiKey = config.apiKey
        this.apiSecret = config.apiSecret
        apiLogger.info('API credentials loaded successfully', {
          hasApiKey: !!this.apiKey,
          hasApiSecret: !!this.apiSecret,
        })
      } else {
        apiLogger.warn('No stored API credentials found')
      }
    } catch (error) {
      apiLogger.error('Failed to load API credentials', error)
    }
  }

  /**
   * Set API credentials
   */
  public setCredentials(apiKey: string, apiSecret: string): void {
    apiLogger.info('Setting new API credentials', {
      apiKeyLength: apiKey.length,
      apiSecretLength: apiSecret.length,
    })
    this.apiKey = apiKey
    this.apiSecret = apiSecret
  }

  /**
   * Check if credentials are configured
   */
  public hasCredentials(): boolean {
    const hasCredentials = !!(this.apiKey && this.apiSecret)
    apiLogger.debug('Checking credentials', { hasCredentials })
    return hasCredentials
  }

  /**
   * Generate API signature for private endpoints (similar to main.py _sign method)
   */
  private generateSignature(path: string, nonce: string, postData: string): string {
    if (!this.apiSecret) {
      throw new Error('API secret not configured')
    }

    // Create SHA256 hash of nonce + postdata
    const message = nonce + postData
    const hash = CryptoJS.SHA256(message)

    // Create HMAC SHA512 of path + hash
    const hmacDigest = CryptoJS.HmacSHA512(
      path + hash.toString(CryptoJS.enc.Latin1),
      CryptoJS.enc.Base64.parse(this.apiSecret)
    )

    return hmacDigest.toString(CryptoJS.enc.Base64)
  }

  /**
   * Rate limiting - check if we can make a request
   */
  private async checkRateLimit(): Promise<void> {
    const now = Date.now()
    
    // Remove timestamps outside the window
    API_RATE_LIMIT.callTimestamps = API_RATE_LIMIT.callTimestamps.filter(
      timestamp => now - timestamp < API_RATE_LIMIT.windowMs
    )

    // Check if we're at the limit
    if (API_RATE_LIMIT.callTimestamps.length >= API_RATE_LIMIT.maxCalls) {
      const oldestCall = API_RATE_LIMIT.callTimestamps[0]
      const waitTime = API_RATE_LIMIT.windowMs - (now - oldestCall)
      
      if (waitTime > 0) {
        apiLogger.warn(`Rate limit reached, waiting ${waitTime}ms`, {
          callCount: API_RATE_LIMIT.callTimestamps.length,
          maxCalls: API_RATE_LIMIT.maxCalls,
        })
        await new Promise(resolve => setTimeout(resolve, waitTime))
      }
    }

    // Record this call
    API_RATE_LIMIT.callTimestamps.push(now)
    apiLogger.debug('Rate limit check passed', {
      currentCalls: API_RATE_LIMIT.callTimestamps.length,
      maxCalls: API_RATE_LIMIT.maxCalls,
    })
  }

  /**
   * Make a request to Kraken API (similar to main.py _request method)
   */
  private async request<T>(
    endpoint: string,
    data?: Record<string, any>,
    isPrivate = false
  ): Promise<KrakenResponse<T>> {
    apiLogger.info(`Making ${isPrivate ? 'private' : 'public'} API request`, {
      endpoint,
      data: isPrivate ? '***' : data,
    })
    
    await this.checkRateLimit()

    if (isPrivate) {
      if (!this.apiKey || !this.apiSecret) {
        apiLogger.error('Cannot make private request - credentials not configured')
        throw new Error('API credentials not configured')
      }

      const urlPath = `/0/private/${endpoint}`
      const url = KRAKEN_API_BASE + urlPath
      
      const nonce = Date.now() * 1000
      const postData = new URLSearchParams({
        nonce: nonce.toString(),
        ...data,
      }).toString()

      const signature = this.generateSignature(urlPath, nonce.toString(), postData)

      apiLogger.debug('Sending private request', {
        url,
        nonce,
        signatureLength: signature.length,
      })

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'API-Key': this.apiKey,
          'API-Sign': signature,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: postData,
      })

      const result = await response.json()
      
      if (result.error && result.error.length > 0) {
        apiLogger.error('API request returned errors', {
          endpoint,
          errors: result.error,
        })
      } else {
        apiLogger.info('Private API request successful', { endpoint })
      }
      
      return result
    } else {
      // Public endpoint
      const url = `${KRAKEN_API_BASE}/0/public/${endpoint}`
      const params = new URLSearchParams(data).toString()
      const fullUrl = params ? `${url}?${params}` : url

      apiLogger.debug('Sending public request', { url: fullUrl })

      const response = await fetch(fullUrl)
      const result = await response.json()
      
      if (result.error && result.error.length > 0) {
        apiLogger.error('Public API request returned errors', {
          endpoint,
          errors: result.error,
        })
      } else {
        apiLogger.info('Public API request successful', { endpoint })
      }
      
      return result
    }
  }

  /**
   * Get order book for a pair
   */
  public async getOrderBook(pair: string, count = 10): Promise<KrakenResponse<Record<string, OrderBook>>> {
    return this.request('Depth', { pair, count }, false)
  }

  /**
   * Get ticker information
   */
  public async getTicker(pair: string): Promise<KrakenResponse<Record<string, TickerInfo>>> {
    return this.request('Ticker', { pair }, false)
  }

  /**
   * Get multiple tickers at once
   */
  public async getTickers(pairs: string[]): Promise<KrakenResponse<Record<string, TickerInfo>>> {
    return this.request('Ticker', { pair: pairs.join(',') }, false)
  }

  /**
   * Get open orders
   */
  public async getOpenOrders(): Promise<KrakenResponse<{ open: Record<string, OpenOrder> }>> {
    return this.request('OpenOrders', {}, true)
  }

  /**
   * Place a new order
   */
  public async addOrder(
    pair: string,
    type: 'buy' | 'sell',
    ordertype: 'market' | 'limit' | 'stop-loss' | 'take-profit',
    volume: string,
    price?: string,
    price2?: string
  ): Promise<KrakenResponse<{ descr: { order: string }; txid: string[] }>> {
    const orderData: Record<string, any> = {
      pair,
      type,
      ordertype,
      volume,
    }

    if (price) orderData.price = price
    if (price2) orderData.price2 = price2

    return this.request('AddOrder', orderData, true)
  }

  /**
   * Cancel an order
   */
  public async cancelOrder(txid: string): Promise<KrakenResponse<{ count: number }>> {
    return this.request('CancelOrder', { txid }, true)
  }

  /**
   * Cancel all orders
   */
  public async cancelAllOrders(): Promise<KrakenResponse<{ count: number }>> {
    return this.request('CancelAll', {}, true)
  }

  /**
   * Get account balance
   */
  public async getBalance(): Promise<KrakenResponse<Record<string, string>>> {
    return this.request('Balance', {}, true)
  }

  /**
   * Get trade balance (includes margin info)
   */
  public async getTradeBalance(): Promise<KrakenResponse<{
    eb: string // equivalent balance
    tb: string // trade balance
    m: string // margin amount of open positions
    n: string // unrealized net profit/loss of open positions
    c: string // cost basis of open positions
    v: string // current floating valuation of open positions
    e: string // equity = trade balance + unrealized net profit/loss
    mf: string // free margin
  }>> {
    return this.request('TradeBalance', {}, true)
  }

  /**
   * Get closed orders
   */
  public async getClosedOrders(): Promise<KrakenResponse<{
    closed: Record<string, OpenOrder>
    count: number
  }>> {
    return this.request('ClosedOrders', {}, true)
  }

  /**
   * Get trades history
   */
  public async getTradesHistory(): Promise<KrakenResponse<{
    trades: Record<string, {
      ordertxid: string
      pair: string
      time: number
      type: 'buy' | 'sell'
      ordertype: string
      price: string
      cost: string
      fee: string
      vol: string
      margin: string
      misc: string
    }>
    count: number
  }>> {
    return this.request('TradesHistory', {}, true)
  }
}

// Export singleton instance
export const krakenAPI = new KrakenAPIService()
