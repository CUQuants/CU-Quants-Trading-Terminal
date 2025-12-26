import { useState, useEffect } from 'react'
import { krakenWS, type TickerUpdate } from '../services/krakenWebSocket'
import { uiLogger } from '../utils/logger'

export interface UseMarketTickerReturn {
  tickers: Map<string, TickerUpdate>
  isConnected: boolean
  error: string | null
  subscribe: (pairs: string[]) => void
  unsubscribe: (pairs: string[]) => void
}

/**
 * Hook for real-time market ticker data via WebSocket
 * Similar to the ticker functionality in main.py
 */
export const useMarketTicker = (initialPairs: string[] = []): UseMarketTickerReturn => {
  const [tickers, setTickers] = useState<Map<string, TickerUpdate>>(new Map())
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [subscribedPairs, setSubscribedPairs] = useState<Set<string>>(new Set(initialPairs))

  useEffect(() => {
    uiLogger.info('useMarketTicker: Initializing', { 
      initialPairsCount: initialPairs.length,
      initialPairs 
    })
    
    // Always connect to public WebSocket (no credentials needed)
    // This matches main.py which uses public endpoints without authentication
    krakenWS.connectPublic()
      .then(() => {
        uiLogger.info('useMarketTicker: WebSocket connected successfully')
        setIsConnected(true)
        setError(null)
        
        // Subscribe to initial pairs if provided
        if (initialPairs.length > 0) {
          uiLogger.info('useMarketTicker: Subscribing to initial pairs', { 
            pairs: initialPairs 
          })
          krakenWS.subscribeTicker(initialPairs, (data: TickerUpdate) => {
            uiLogger.debug('useMarketTicker: Ticker update received', { 
              pair: data.pair,
              last: data.last 
            })
            setTickers(prev => new Map(prev).set(data.pair, data))
          })
        }
      })
      .catch(err => {
        uiLogger.error('useMarketTicker: WebSocket connection failed', err)
        setError(err instanceof Error ? err.message : 'WebSocket connection failed')
        setIsConnected(false)
      })

    // Cleanup on unmount
    return () => {
      uiLogger.info('useMarketTicker: Cleaning up', { 
        subscribedPairsCount: subscribedPairs.size 
      })
      if (subscribedPairs.size > 0) {
        krakenWS.unsubscribe('ticker', Array.from(subscribedPairs))
      }
    }
  }, []) // Only run on mount

  const subscribe = (pairs: string[]) => {
    uiLogger.info('useMarketTicker: Manual subscribe requested', { pairs })
    krakenWS.subscribeTicker(pairs, (data: TickerUpdate) => {
      setTickers(prev => new Map(prev).set(data.pair, data))
    })
    
    setSubscribedPairs(prev => {
      const updated = new Set(prev)
      pairs.forEach(p => updated.add(p))
      return updated
    })
  }

  const unsubscribe = (pairs: string[]) => {
    krakenWS.unsubscribe('ticker', pairs)
    
    setSubscribedPairs(prev => {
      const updated = new Set(prev)
      pairs.forEach(p => updated.delete(p))
      return updated
    })
    
    setTickers(prev => {
      const updated = new Map(prev)
      pairs.forEach(p => updated.delete(p))
      return updated
    })
  }

  return {
    tickers,
    isConnected,
    error,
    subscribe,
    unsubscribe,
  }
}
