import { useState, useEffect } from 'react'
import styles from './MarketTicker.module.css'
import type { TickerData } from '../../types'

// Mock data for 14 trading instruments
const MOCK_TICKER_DATA: TickerData[] = [
  { symbol: 'BTC/USD', name: 'Bitcoin', price: 42350.50, change: 1250.30, changePercent: 3.04 },
  { symbol: 'ETH/USD', name: 'Ethereum', price: 2245.75, change: -45.25, changePercent: -1.98 },
  { symbol: 'SOL/USD', name: 'Solana', price: 98.42, change: 5.67, changePercent: 6.11 },
  { symbol: 'BNB/USD', name: 'Binance Coin', price: 315.20, change: 8.90, changePercent: 2.90 },
  { symbol: 'XRP/USD', name: 'Ripple', price: 0.6234, change: -0.0156, changePercent: -2.44 },
  { symbol: 'ADA/USD', name: 'Cardano', price: 0.5678, change: 0.0234, changePercent: 4.30 },
  { symbol: 'AVAX/USD', name: 'Avalanche', price: 37.89, change: 1.23, changePercent: 3.36 },
  { symbol: 'DOGE/USD', name: 'Dogecoin', price: 0.0892, change: 0.0012, changePercent: 1.36 },
  { symbol: 'MATIC/USD', name: 'Polygon', price: 0.8456, change: -0.0234, changePercent: -2.69 },
  { symbol: 'DOT/USD', name: 'Polkadot', price: 6.78, change: 0.34, changePercent: 5.28 },
  { symbol: 'LINK/USD', name: 'Chainlink', price: 14.56, change: -0.78, changePercent: -5.08 },
  { symbol: 'UNI/USD', name: 'Uniswap', price: 6.23, change: 0.45, changePercent: 7.78 },
  { symbol: 'ATOM/USD', name: 'Cosmos', price: 9.87, change: 0.23, changePercent: 2.39 },
  { symbol: 'LTC/USD', name: 'Litecoin', price: 72.34, change: -1.89, changePercent: -2.55 },
]

const MarketTicker = () => {
  const [tickerData, setTickerData] = useState<TickerData[]>(MOCK_TICKER_DATA)
  const [isPaused, setIsPaused] = useState(false)

  // Simulate live price updates
  useEffect(() => {
    const interval = setInterval(() => {
      setTickerData(prev => prev.map(item => {
        const randomChange = (Math.random() - 0.5) * item.price * 0.001
        const newPrice = item.price + randomChange
        const newChange = newPrice - (item.price - item.change)
        const newChangePercent = (newChange / (item.price - item.change)) * 100
        
        return {
          ...item,
          price: newPrice,
          change: newChange,
          changePercent: newChangePercent
        }
      }))
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className={styles.tickerContainer}>
      <div 
        className={`${styles.tickerTrack} ${isPaused ? styles.paused : ''}`}
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Duplicate items for seamless loop */}
        {[...tickerData, ...tickerData].map((item, index) => (
          <div key={`${item.symbol}-${index}`} className={styles.tickerItem}>
            <span className={styles.symbol}>{item.symbol}</span>
            <span className={styles.price}>{item.price.toFixed(2)}</span>
            <span className={item.change >= 0 ? styles.changePositive : styles.changeNegative}>
              {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}
            </span>
            <span className={item.changePercent >= 0 ? styles.changePositive : styles.changeNegative}>
              ({item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MarketTicker
