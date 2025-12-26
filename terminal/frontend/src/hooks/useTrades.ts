import { useEffect, useRef, useState } from 'react'
import { krakenWS } from '../services/krakenWebSocket'

export interface TradeUpdate {
  pair: string
  trades: Array<{
    price: string
    volume: string
    time: number
    side: 'b' | 's'
    orderType: string
    misc: string
  }>
}

export interface UseTradesReturn {
  trades: Map<string, TradeUpdate['trades']>
  subscribe: (pairs: string[]) => void
  unsubscribe: (pairs: string[]) => void
}

/**
 * Hook for real-time trade updates via WebSocket
 */
export const useTrades = (initialPairs: string[] = []): UseTradesReturn => {
  const [trades, setTrades] = useState<Map<string, TradeUpdate['trades']>>(new Map())
  const subscribedPairs = useRef<Set<string>>(new Set(initialPairs))

  useEffect(() => {
    if (initialPairs.length > 0) {
      initialPairs.forEach(pair => {
        krakenWS.subscribeTrades([pair], (data: TradeUpdate) => {
          setTrades(prev => new Map(prev).set(data.pair, data.trades))
        })
      })
    }
    return () => {
      if (initialPairs.length > 0) {
        krakenWS.unsubscribe('trade', initialPairs)
      }
    }
  }, [])

  const subscribe = (pairs: string[]) => {
    pairs.forEach(pair => {
      krakenWS.subscribeTrades([pair], (data: TradeUpdate) => {
        setTrades(prev => new Map(prev).set(data.pair, data.trades))
      })
      subscribedPairs.current.add(pair)
    })
  }

  const unsubscribe = (pairs: string[]) => {
    krakenWS.unsubscribe('trade', pairs)
    pairs.forEach(pair => {
      subscribedPairs.current.delete(pair)
      setTrades(prev => {
        const updated = new Map(prev)
        updated.delete(pair)
        return updated
      })
    })
  }

  return {
    trades,
    subscribe,
    unsubscribe,
  }
}
