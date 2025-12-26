import { useState, useEffect } from 'react'
import { krakenWS, type OrderBookUpdate } from '../services/krakenWebSocket'

export interface UseOrderBookReturn {
  orderBook: OrderBookUpdate | null
  isLoading: boolean
  error: string | null
}

/**
 * Hook for real-time order book data via WebSocket
 * Similar to the order book functionality in main.py
 */
export const useOrderBook = (pair: string, depth: number = 10): UseOrderBookReturn => {
  const [orderBook, setOrderBook] = useState<OrderBookUpdate | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!pair) {
      setOrderBook(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    // Ensure WebSocket is connected
    if (!krakenWS.isConnected()) {
      krakenWS.connectPublic()
        .then(() => {
          subscribeToBook()
        })
        .catch(err => {
          setError(err instanceof Error ? err.message : 'WebSocket connection failed')
          setIsLoading(false)
        })
    } else {
      subscribeToBook()
    }

    function subscribeToBook() {
      krakenWS.subscribeOrderBook([pair], depth, (data: OrderBookUpdate) => {
        setOrderBook(data)
        setIsLoading(false)
      })
    }

    // Cleanup on unmount or pair change
    return () => {
      krakenWS.unsubscribe('book', [pair])
    }
  }, [pair, depth])

  return {
    orderBook,
    isLoading,
    error,
  }
}
