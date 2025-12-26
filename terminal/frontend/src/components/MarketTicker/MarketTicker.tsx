import { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import styles from './MarketTicker.module.css'
import { useMarketTicker } from '../../hooks/useMarketTicker'
import { krakenAPI } from '../../services/krakenAPI'
import type { TickerData } from '../../types'
import { uiLogger } from '../../utils/logger'

// 14 trading pairs to display on ticker
const TICKER_PAIRS = [
  'XBT/USD',  // Bitcoin
  'ETH/USD',  // Ethereum
  'SOL/USD',  // Solana
  'XRP/USD',  // Ripple
  'ADA/USD',  // Cardano
  'DOT/USD',  // Polkadot
  'MATIC/USD', // Polygon
  'LINK/USD', // Chainlink
  'UNI/USD',  // Uniswap
  'ATOM/USD', // Cosmos
  'AVAX/USD', // Avalanche
  'LTC/USD',  // Litecoin
  'BCH/USD',  // Bitcoin Cash
  'ALGO/USD', // Algorand
]

const MarketTicker = () => {
  const [isPaused, setIsPaused] = useState(false)
  const [hasApiCredentials, setHasApiCredentials] = useState(false)
  
  // Check for API credentials on mount and periodically
  useEffect(() => {
    const checkCredentials = () => {
      const hasCredentials = krakenAPI.hasCredentials()
      setHasApiCredentials(hasCredentials)
      uiLogger.info('MarketTicker: API credentials check', { hasCredentials })
    }
    
    // Check immediately
    checkCredentials()
    
    // Check every 2 seconds in case credentials are added
    const interval = setInterval(checkCredentials, 2000)
    
    return () => clearInterval(interval)
  }, [])
  
  // ALWAYS call hooks - never conditionally
  // Pass empty array when no credentials to prevent WebSocket connection
  const { tickers, isConnected } = useMarketTicker(hasApiCredentials ? TICKER_PAIRS : [])

  useEffect(() => {
    uiLogger.info('MarketTicker: Component mounted', { 
      pairCount: TICKER_PAIRS.length,
      hasApiCredentials,
    })
  }, [hasApiCredentials])

  useEffect(() => {
    if (hasApiCredentials) {
      uiLogger.info('MarketTicker: Connection status changed', { isConnected })
    }
  }, [isConnected, hasApiCredentials])

  useEffect(() => {
    if (hasApiCredentials) {
      uiLogger.debug('MarketTicker: Ticker data updated', { 
        tickerCount: tickers.size,
        hasData: tickers.size > 0 
      })
    }
  }, [tickers, hasApiCredentials])

  // Convert WebSocket ticker data to component format
  // MUST be called before any early returns (Rules of Hooks)
  const tickerData = useMemo((): TickerData[] => {
    const data: TickerData[] = []
    
    TICKER_PAIRS.forEach(pair => {
      const wsData = tickers.get(pair)
      
      if (wsData) {
        data.push({
          symbol: pair,
          name: pair.split('/')[0],
          price: parseFloat(wsData.last),
          change: parseFloat(wsData.change),
          changePercent: parseFloat(wsData.changePercent),
        })
      } else {
        // Show loading state
        data.push({
          symbol: pair,
          name: pair.split('/')[0],
          price: 0,
          change: 0,
          changePercent: 0,
        })
      }
    })
    
    return data
  }, [tickers])

  // If no API credentials, show warning message (AFTER all hooks)
  if (!hasApiCredentials) {
    return (
      <div className={styles.tickerContainer}>
        <div className={styles.noCredentials}>
          <span className={styles.warningIcon}>⚠️</span>
          <span className={styles.warningText}>
            Connect your API in <Link to="/settings" className={styles.settingsLink}>Settings</Link> to view market data
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.tickerContainer}>
      {!isConnected && (
        <div className={styles.connectionStatus}>
          Connecting to market data...
        </div>
      )}
      <div 
        className={`${styles.tickerTrack} ${isPaused ? styles.paused : ''}`}
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Duplicate items for seamless loop */}
        {[...tickerData, ...tickerData].map((item, index) => (
          <div key={`${item.symbol}-${index}`} className={styles.tickerItem}>
            <span className={styles.symbol}>{item.symbol}</span>
            <span className={styles.price}>
              {item.price > 0 ? item.price.toFixed(2) : '---'}
            </span>
            <span className={item.change >= 0 ? styles.changePositive : styles.changeNegative}>
              {item.price > 0 ? (
                <>{item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}</>
              ) : (
                '---'
              )}
            </span>
            <span className={item.changePercent >= 0 ? styles.changePositive : styles.changeNegative}>
              {item.price > 0 ? (
                <>({item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%)</>
              ) : (
                '---'
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MarketTicker
