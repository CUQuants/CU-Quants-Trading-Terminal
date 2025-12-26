import { useState, useEffect } from 'react'
import { useMarketContext } from '../../contexts/MarketContext'
import { krakenAPI } from '../../services/krakenAPI'
import styles from './Watchlist.module.css'
import { uiLogger } from '../../utils/logger'

interface WatchlistData {
  pair: string
  bid: string
  ask: string
  last: string
  spread: string
}

const Watchlist = () => {
  const { watchlistPairs, addToWatchlist, removeFromWatchlist, clearWatchlist } = useMarketContext()
  const [pairInput, setPairInput] = useState('')
  const [watchlistData, setWatchlistData] = useState<Map<string, WatchlistData>>(new Map())
  const [loading, setLoading] = useState(false)

  // Fetch data for watchlist pairs
  useEffect(() => {
    if (watchlistPairs.size === 0) {
      setWatchlistData(new Map())
      return
    }

    const fetchWatchlistData = async () => {
      setLoading(true)
      const newData = new Map<string, WatchlistData>()

      for (const pair of watchlistPairs) {
        try {
          const [tickerResult, bookResult] = await Promise.all([
            krakenAPI.getTicker(pair),
            krakenAPI.getOrderBook(pair, 1)
          ])

          if (!tickerResult.error?.length && !bookResult.error?.length) {
            const tickerKey = Object.keys(tickerResult.result || {})[0]
            const bookKey = Object.keys(bookResult.result || {})[0]

            if (tickerKey && bookKey) {
              const ticker = tickerResult.result![tickerKey]
              const book = bookResult.result![bookKey]

              const bestBid = book.bids?.[0]?.price ? parseFloat(book.bids[0].price) : 0
              const bestAsk = book.asks?.[0]?.price ? parseFloat(book.asks[0].price) : 0
              const lastPrice = parseFloat(ticker.c[0])
              const spread = bestAsk && bestBid ? ((bestAsk - bestBid) / bestBid) * 10000 : 0

              newData.set(pair, {
                pair,
                bid: bestBid.toFixed(4),
                ask: bestAsk.toFixed(4),
                last: lastPrice.toFixed(4),
                spread: spread.toFixed(2)
              })
            }
          }
        } catch (error) {
          uiLogger.error('Watchlist: Failed to fetch data for pair', { pair, error })
        }
      }

      setWatchlistData(newData)
      setLoading(false)
    }

    fetchWatchlistData()

    // Refresh watchlist data every 3 seconds (like main.py)
    const interval = setInterval(fetchWatchlistData, 3000)
    return () => clearInterval(interval)
  }, [watchlistPairs])

  const handleAdd = () => {
    if (pairInput.trim()) {
      addToWatchlist(pairInput)
      setPairInput('')
    }
  }

  const handleRemove = (pair: string) => {
    removeFromWatchlist(pair)
  }

  const handleClear = () => {
    if (window.confirm('Clear entire watchlist?')) {
      clearWatchlist()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAdd()
    }
  }

  return (
    <div className={styles.watchlist}>
      <div className={styles.header}>
        <h3 className={styles.title}>Watchlist</h3>
        <span className={styles.count}>({watchlistPairs.size} pairs)</span>
      </div>

      <div className={styles.controls}>
        <input
          type="text"
          value={pairInput}
          onChange={(e) => setPairInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="e.g., XBT/USD"
          className={styles.input}
        />
        <button onClick={handleAdd} className={styles.addButton}>
          ADD
        </button>
        <button onClick={handleClear} className={styles.clearButton} disabled={watchlistPairs.size === 0}>
          CLEAR ALL
        </button>
      </div>

      <div className={styles.listContainer}>
        {watchlistPairs.size === 0 ? (
          <div className={styles.empty}>
            No pairs in watchlist. Add a pair to get started.
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Pair</th>
                <th>Bid</th>
                <th>Ask</th>
                <th>Last</th>
                <th>Spread (bps)</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {Array.from(watchlistPairs).map(pair => {
                const data = watchlistData.get(pair)
                return (
                  <tr key={pair}>
                    <td className={styles.pairCell}>{pair}</td>
                    <td className={styles.numberCell}>{data?.bid || '---'}</td>
                    <td className={styles.numberCell}>{data?.ask || '---'}</td>
                    <td className={styles.numberCell}>{data?.last || '---'}</td>
                    <td className={styles.numberCell}>{data?.spread || '---'}</td>
                    <td>
                      <button
                        onClick={() => handleRemove(pair)}
                        className={styles.removeButton}
                      >
                        REMOVE
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
        {loading && watchlistPairs.size > 0 && (
          <div className={styles.loading}>Updating...</div>
        )}
      </div>
    </div>
  )
}

export default Watchlist
