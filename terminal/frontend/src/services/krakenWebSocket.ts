import { wsLogger } from '../utils/logger'

/**
 * Backend WebSocket Client - Stub Implementation
 * 
 * TODO: Connect to backend WebSocket server instead of Kraken directly
 * See: /backend/TODO.md for full implementation details
 */

const BACKEND_WS_BASE = import.meta.env.VITE_BACKEND_WS_URL || 'ws://localhost:8000/ws'

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
  bids: Array<[string, string, string]>
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

class BackendWebSocketService {
  private ws: WebSocket | null = null
  private subscriptions = new Map<string, Set<SubscriptionCallback>>()

  public connectPublic(): Promise<void> {
    wsLogger.warn('⚠️ WebSocket: Backend not implemented')
    return Promise.resolve()
  }

  public disconnect(): void {
    wsLogger.warn('⚠️ WebSocket disconnect: Backend not implemented')
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  public subscribeTicker(pairs: string[], callback: (data: TickerUpdate) => void): void {
    wsLogger.warn('⚠️ subscribeTicker: Backend not implemented', { pairs })
  }

  public unsubscribeTicker(pairs: string[]): void {
    wsLogger.warn('⚠️ unsubscribeTicker: Backend not implemented', { pairs })
  }

  public subscribeOrderBook(pairs: string[], callback: (data: OrderBookUpdate) => void): void {
    wsLogger.warn('⚠️ subscribeOrderBook: Backend not implemented', { pairs })
  }

  public unsubscribeOrderBook(pairs: string[]): void {
    wsLogger.warn('⚠️ unsubscribeOrderBook: Backend not implemented', { pairs })
  }

  public subscribeTrades(pairs: string[], callback: (data: any) => void): void {
    wsLogger.warn('⚠️ subscribeTrades: Backend not implemented', { pairs })
  }

  public unsubscribeTrades(pairs: string[]): void {
    wsLogger.warn('⚠️ unsubscribeTrades: Backend not implemented', { pairs })
  }

  public subscribeOwnTrades(callback: (data: OrderUpdate) => void): void {
    wsLogger.warn('⚠️ subscribeOwnTrades: Backend not implemented')
  }

  public unsubscribeOwnTrades(): void {
    wsLogger.warn('⚠️ unsubscribeOwnTrades: Backend not implemented')
  }

  public isConnected(): boolean {
    return false
  }
}

export const krakenWS = new BackendWebSocketService()
