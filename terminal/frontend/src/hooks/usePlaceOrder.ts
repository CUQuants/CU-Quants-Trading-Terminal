import { useState, useCallback } from 'react'
import { krakenAPI } from '../services/krakenAPI'

export interface UsePlaceOrderReturn {
  placeOrder: (
    pair: string,
    type: 'buy' | 'sell',
    ordertype: 'market' | 'limit',
    volume: string,
    price?: string
  ) => Promise<{ success: boolean; txid?: string[]; error?: string }>
  isSubmitting: boolean
  lastError: string | null
}

/**
 * Hook for placing orders
 * Similar to the add_order functionality in main.py
 */
export const usePlaceOrder = (): UsePlaceOrderReturn => {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [lastError, setLastError] = useState<string | null>(null)

  const placeOrder = useCallback(
    async (
      pair: string,
      type: 'buy' | 'sell',
      ordertype: 'market' | 'limit',
      volume: string,
      price?: string
    ) => {
      if (!krakenAPI.hasCredentials()) {
        const error = 'API credentials not configured'
        setLastError(error)
        return { success: false, error }
      }

      setIsSubmitting(true)
      setLastError(null)

      try {
        const response = await krakenAPI.addOrder(pair, type, ordertype, volume, price)

        if (response.error && response.error.length > 0) {
          const error = response.error.join(', ')
          setLastError(error)
          return { success: false, error }
        }

        if (response.result) {
          return { success: true, txid: response.result.txid }
        }

        return { success: false, error: 'Unknown error' }
      } catch (err) {
        const error = err instanceof Error ? err.message : 'Failed to place order'
        setLastError(error)
        return { success: false, error }
      } finally {
        setIsSubmitting(false)
      }
    },
    []
  )

  return {
    placeOrder,
    isSubmitting,
    lastError,
  }
}
