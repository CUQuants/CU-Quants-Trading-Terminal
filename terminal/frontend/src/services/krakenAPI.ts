import { apiLogger } from '../utils/logger'

/**
 * Backend API Client - Stub Implementation
 * 
 * TODO: Implement backend server to handle Kraken API calls
 * See: /backend/TODO.md for full implementation details
 */

const BACKEND_API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000/api'

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
  a: [string, string, string]
  b: [string, string, string]
  c: [string, string]
  v: [string, string]
  p: [string, string]
  t: [number, number]
  l: [string, string]
  h: [string, string]
  o: string
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

class BackendAPIService {
  public async setCredentials(apiKey: string, apiSecret: string): Promise<boolean> {
    apiLogger.warn('⚠️ Backend not implemented - storing credentials in localStorage (INSECURE)')
    localStorage.setItem('apiConfig', JSON.stringify({ apiKey, apiSecret }))
    return true
  }

  public hasCredentials(): boolean {
    return !!localStorage.getItem('apiConfig')
  }

  public async getOrderBook(pair: string, count = 10): Promise<KrakenResponse<Record<string, OrderBook>>> {
    apiLogger.warn('⚠️ getOrderBook: Backend not implemented')
    return { error: [], result: { [pair]: { asks: [], bids: [] } } }
  }

  public async getTicker(pair: string): Promise<KrakenResponse<Record<string, TickerInfo>>> {
    apiLogger.warn('⚠️ getTicker: Backend not implemented')
    return { error: [], result: {} }
  }

  public async getTickers(pairs: string[]): Promise<KrakenResponse<Record<string, TickerInfo>>> {
    apiLogger.warn('⚠️ getTickers: Backend not implemented')
    return { error: [], result: {} }
  }

  public async getOpenOrders(): Promise<KrakenResponse<{ open: Record<string, OpenOrder> }>> {
    apiLogger.warn('⚠️ getOpenOrders: Backend not implemented')
    return { error: [], result: { open: {} } }
  }

  public async addOrder(pair: string, type: 'buy' | 'sell', ordertype: string, volume: string, price?: string): Promise<KrakenResponse<{ descr: { order: string }; txid: string[] }>> {
    apiLogger.warn('⚠️ addOrder: Backend not implemented', { pair, type, ordertype, volume })
    return { error: ['Backend not implemented'], result: undefined }
  }

  public async cancelOrder(txid: string): Promise<KrakenResponse<{ count: number }>> {
    apiLogger.warn('⚠️ cancelOrder: Backend not implemented')
    return { error: ['Backend not implemented'], result: undefined }
  }

  public async cancelAllOrders(): Promise<KrakenResponse<{ count: number }>> {
    apiLogger.warn('⚠️ cancelAllOrders: Backend not implemented')
    return { error: ['Backend not implemented'], result: undefined }
  }

  public async getBalance(): Promise<KrakenResponse<Record<string, string>>> {
    apiLogger.warn('⚠️ getBalance: Backend not implemented')
    return { error: [], result: {} }
  }

  public async getTradeBalance(): Promise<KrakenResponse<any>> {
    apiLogger.warn('⚠️ getTradeBalance: Backend not implemented')
    return { error: [], result: undefined }
  }

  public async getClosedOrders(): Promise<KrakenResponse<{ closed: Record<string, OpenOrder>; count: number }>> {
    apiLogger.warn('⚠️ getClosedOrders: Backend not implemented')
    return { error: [], result: { closed: {}, count: 0 } }
  }

  public async getTradesHistory(): Promise<KrakenResponse<any>> {
    apiLogger.warn('⚠️ getTradesHistory: Backend not implemented')
    return { error: [], result: { trades: {}, count: 0 } }
  }
}

export const krakenAPI = new BackendAPIService()
