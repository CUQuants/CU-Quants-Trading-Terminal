import { useState, useMemo, useEffect } from 'react'
import styles from './MarketTicker.module.css'
import { useMarketTicker } from '../../hooks/useMarketTicker'
import { useMarketContext } from '../../contexts/MarketContext'
import type { TickerData } from '../../types'
import { uiLogger } from '../../utils/logger'

const MarketTicker = () => {
  const [isPaused, setIsPaused] = useState(false)
  const { activePairs } = useMarketContext()
  
  // Market ticker uses PUBLIC WebSocket - no credentials needed!
  // Now displays only markets from watchlist or ladders (like main.py)
  const { tickers, isConnected } = useMarketTicker(activePairs)

  useEffect(() => {
    uiLogger.info('MarketTicker: Component mounted', { 
      pairCount: activePairs.length,
    })
  }, [])

  useEffect(() => {
    uiLogger.info('MarketTicker: Connection status changed', { isConnected })
  }, [isConnected])

  useEffect(() => {
    uiLogger.debug('MarketTicker: Ticker data updated', { 
      tickerCount: tickers.size,
      hasData: tickers.size > 0 
    })
  }, [tickers])

  // Convert WebSocket ticker data to component format
  // MUST be called before any early returns (Rules of Hooks)
  const tickerData = useMemo((): TickerData[] => {
    const data: TickerData[] = []
    
    activePairs.forEach((pair: string) => {
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
  }, [tickers, activePairs])

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
