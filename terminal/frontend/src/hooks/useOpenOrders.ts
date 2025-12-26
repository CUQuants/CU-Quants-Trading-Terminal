import { useState, useEffect, useCallback } from 'react'
import { krakenAPI, type OpenOrder } from '../services/krakenAPI'

export interface UseOpenOrdersReturn {
  orders: Record<string, OpenOrder>
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
  cancelOrder: (txid: string) => Promise<boolean>
  cancelAll: () => Promise<boolean>
}

/**
 * Hook for managing open orders
 * Similar to the open orders functionality in main.py
 */
export const useOpenOrders = (autoRefresh = true, interval = 3000): UseOpenOrdersReturn => {
  const [orders, setOrders] = useState<Record<string, OpenOrder>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!krakenAPI.hasCredentials()) {
      setError('API credentials not configured')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await krakenAPI.getOpenOrders()
      
      if (response.error && response.error.length > 0) {
        setError(response.error.join(', '))
        setOrders({})
      } else if (response.result) {
        setOrders(response.result.open || {})
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch open orders')
      setOrders({})
    } finally {
      setIsLoading(false)
    }
  }, [])

  const cancelOrder = useCallback(async (txid: string): Promise<boolean> => {
    try {
      const response = await krakenAPI.cancelOrder(txid)
      
      if (response.error && response.error.length > 0) {
        setError(response.error.join(', '))
        return false
      }
      
      // Refresh orders after cancellation
      await refresh()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel order')
      return false
    }
  }, [refresh])

  const cancelAll = useCallback(async (): Promise<boolean> => {
    try {
      const response = await krakenAPI.cancelAllOrders()
      
      if (response.error && response.error.length > 0) {
        setError(response.error.join(', '))
        return false
      }
      
      // Refresh orders after cancellation
      await refresh()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel all orders')
      return false
    }
  }, [refresh])

  // Auto-refresh on mount and interval
  useEffect(() => {
    refresh()

    if (autoRefresh) {
      const timer = setInterval(refresh, interval)
      return () => clearInterval(timer)
    }
  }, [refresh, autoRefresh, interval])

  return {
    orders,
    isLoading,
    error,
    refresh,
    cancelOrder,
    cancelAll,
  }
}
