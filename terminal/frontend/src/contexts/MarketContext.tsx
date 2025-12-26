import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { uiLogger } from '../utils/logger'

interface MarketContextType {
  watchlistPairs: Set<string>
  ladderPairs: Set<string>
  activePairs: string[]
  addToWatchlist: (pair: string) => void
  removeFromWatchlist: (pair: string) => void
  clearWatchlist: () => void
  addToLadder: (pair: string) => void
  removeFromLadder: (pair: string) => void
}

const MarketContext = createContext<MarketContextType | undefined>(undefined)

export const useMarketContext = () => {
  const context = useContext(MarketContext)
  if (!context) {
    throw new Error('useMarketContext must be used within MarketProvider')
  }
  return context
}

interface MarketProviderProps {
  children: ReactNode
}

export const MarketProvider = ({ children }: MarketProviderProps) => {
  // Load watchlist from localStorage on mount
  const [watchlistPairs, setWatchlistPairs] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem('watchlistPairs')
      if (stored) {
        const pairs = JSON.parse(stored)
        uiLogger.info('MarketContext: Loaded watchlist from localStorage', { 
          count: pairs.length 
        })
        return new Set(pairs)
      }
    } catch (error) {
      uiLogger.error('MarketContext: Failed to load watchlist from localStorage', error)
    }
    return new Set<string>()
  })

  const [ladderPairs, setLadderPairs] = useState<Set<string>>(new Set())

  // Compute active pairs (union of watchlist and ladder pairs)
  const activePairs = Array.from(new Set([...watchlistPairs, ...ladderPairs]))

  // Save watchlist to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem('watchlistPairs', JSON.stringify(Array.from(watchlistPairs)))
      uiLogger.debug('MarketContext: Saved watchlist to localStorage', { 
        count: watchlistPairs.size 
      })
    } catch (error) {
      uiLogger.error('MarketContext: Failed to save watchlist to localStorage', error)
    }
  }, [watchlistPairs])

  const addToWatchlist = (pair: string) => {
    const normalizedPair = pair.trim().toUpperCase()
    if (!normalizedPair) return

    setWatchlistPairs(prev => {
      const newSet = new Set(prev)
      newSet.add(normalizedPair)
      uiLogger.info('MarketContext: Added pair to watchlist', { 
        pair: normalizedPair,
        totalWatched: newSet.size 
      })
      return newSet
    })
  }

  const removeFromWatchlist = (pair: string) => {
    setWatchlistPairs(prev => {
      const newSet = new Set(prev)
      newSet.delete(pair)
      uiLogger.info('MarketContext: Removed pair from watchlist', { 
        pair,
        totalWatched: newSet.size 
      })
      return newSet
    })
  }

  const clearWatchlist = () => {
    uiLogger.info('MarketContext: Clearing entire watchlist', { 
      previousCount: watchlistPairs.size 
    })
    setWatchlistPairs(new Set())
  }

  const addToLadder = (pair: string) => {
    const normalizedPair = pair.trim().toUpperCase()
    if (!normalizedPair) return

    setLadderPairs(prev => {
      const newSet = new Set(prev)
      newSet.add(normalizedPair)
      uiLogger.info('MarketContext: Added pair to ladder', { 
        pair: normalizedPair,
        totalLadders: newSet.size 
      })
      return newSet
    })
  }

  const removeFromLadder = (pair: string) => {
    setLadderPairs(prev => {
      const newSet = new Set(prev)
      newSet.delete(pair)
      uiLogger.info('MarketContext: Removed pair from ladder', { 
        pair,
        totalLadders: newSet.size 
      })
      return newSet
    })
  }

  useEffect(() => {
    uiLogger.info('MarketContext: Active pairs updated', {
      activePairsCount: activePairs.length,
      watchlistCount: watchlistPairs.size,
      ladderCount: ladderPairs.size,
      pairs: activePairs
    })
  }, [activePairs, watchlistPairs.size, ladderPairs.size])

  const value: MarketContextType = {
    watchlistPairs,
    ladderPairs,
    activePairs,
    addToWatchlist,
    removeFromWatchlist,
    clearWatchlist,
    addToLadder,
    removeFromLadder,
  }

  return (
    <MarketContext.Provider value={value}>
      {children}
    </MarketContext.Provider>
  )
}
