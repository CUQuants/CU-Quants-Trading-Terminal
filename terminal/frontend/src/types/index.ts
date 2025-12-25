// Market Ticker Data Types
export interface TickerData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
}

// Order Types
export interface Order {
  id: string
  symbol: string
  side: 'BUY' | 'SELL'
  type: 'MARKET' | 'LIMIT' | 'STOP'
  quantity: number
  price?: number
  status: 'OPEN' | 'FILLED' | 'CANCELLED' | 'PARTIAL'
  timestamp: number
}

// Position Types
export interface Position {
  symbol: string
  quantity: number
  avgPrice: number
  currentPrice: number
  pnl: number
  pnlPercent: number
}

// Market Data Types
export interface MarketData {
  symbol: string
  bid: number
  ask: number
  last: number
  volume: number
  high24h: number
  low24h: number
}

// Trade Types
export interface Trade {
  id: string
  symbol: string
  side: 'BUY' | 'SELL'
  price: number
  quantity: number
  timestamp: number
}

// Settings Types
export interface ApiSettings {
  apiKey: string
  apiSecret: string
}
