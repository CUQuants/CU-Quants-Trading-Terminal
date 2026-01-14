import { useState, useMemo } from 'react'
import Panel from '../components/Panel/Panel'
import DataTable, { Column } from '../components/DataTable/DataTable'
import type { Order, Position, Trade } from '../types'
import styles from './TradingPage.module.css'
import { useMarketContext } from '../contexts/MarketContext'
import { useMarketTicker } from '../hooks/useMarketTicker'
import { useOpenOrders } from '../hooks/useOpenOrders'
import { useTrades } from '../hooks/useTrades'

// Helper: Convert Kraken OpenOrder to Order type
function mapOpenOrderToOrder(txid: string, order: any): Order {
  return {
    id: txid,
    symbol: order.descr.pair.replace('XBT', 'BTC'),
    side: order.descr.type.toUpperCase() === 'BUY' ? 'BUY' : 'SELL',
    type: order.descr.ordertype.toUpperCase(),
    quantity: parseFloat(order.vol),
    price: parseFloat(order.price) || undefined,
    status: order.status.toUpperCase(),
    timestamp: order.opentm * 1000,
  }
}

// Helper: Compute positions from open orders and ticker data (placeholder logic)
function computePositions(orders: Order[], tickers: Map<string, any>): Position[] {
  // This is a placeholder: in real trading, positions come from account balances, not open orders
  // Here, we just show a summary per symbol for demonstration
  const posMap = new Map<string, { qty: number; avg: number; }>()
  orders.forEach(order => {
    if (order.status === 'OPEN') {
      const prev = posMap.get(order.symbol) || { qty: 0, avg: 0 }
      // Weighted average price
      const totalQty = prev.qty + order.quantity
      const avgPrice = totalQty > 0 ? ((prev.qty * prev.avg) + (order.quantity * (order.price || 0))) / totalQty : 0
      posMap.set(order.symbol, { qty: totalQty, avg: avgPrice })
    }
  })
  return Array.from(posMap.entries()).map(([symbol, { qty, avg }]) => {
    const ticker = tickers.get(symbol.replace('BTC', 'XBT'))
    const currentPrice = ticker ? parseFloat(ticker.last) : avg
    const pnl = (currentPrice - avg) * qty
    const pnlPercent = avg > 0 ? ((currentPrice - avg) / avg) * 100 : 0
    return {
      symbol,
      quantity: qty,
      avgPrice: avg,
      currentPrice,
      pnl,
      pnlPercent,
    }
  })
}

const TradingPage = () => {

  const [orderForm, setOrderForm] = useState({
    symbol: 'BTC/USD',
    side: 'BUY' as 'BUY' | 'SELL',
    type: 'LIMIT' as 'MARKET' | 'LIMIT' | 'STOP',
    quantity: '',
    price: '',
  })

  // Real-time data hooks
  const { activePairs } = useMarketContext()
  const { tickers } = useMarketTicker(activePairs)
  const { orders: openOrders } = useOpenOrders()
  const { trades: tradeMap } = useTrades(activePairs)

  // Convert open orders to Order[]
  const orders: Order[] = useMemo(() => {
    return Object.entries(openOrders).map(([txid, order]) => mapOpenOrderToOrder(txid, order))
  }, [openOrders])

  // Compute positions from open orders and ticker data
  const positions: Position[] = useMemo(() => computePositions(orders, tickers), [orders, tickers])

  // Convert trades to Trade[]
  const trades: Trade[] = useMemo(() => {
    const result: Trade[] = []
    tradeMap.forEach((tradeArr, pair) => {
      tradeArr.forEach((t, idx) => {
        result.push({
          id: `${pair}-${t.time}-${idx}`,
          symbol: pair.replace('XBT', 'BTC'),
          side: t.side === 'b' ? 'BUY' : 'SELL',
          price: parseFloat(t.price),
          quantity: parseFloat(t.volume),
          timestamp: t.time * 1000,
        })
      })
    })
    // Sort by most recent
    return result.sort((a, b) => b.timestamp - a.timestamp).slice(0, 50)
  }, [tradeMap])

  const handleSubmitOrder = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Order submitted:', orderForm)
    // In production, this would call the API
  }

  const positionColumns: Column<Position>[] = [
    { key: 'symbol', header: 'Symbol', align: 'left' },
    { key: 'quantity', header: 'Quantity', align: 'right', render: (val) => val.toFixed(4) },
    { key: 'avgPrice', header: 'Avg Price', align: 'right', render: (val) => val.toFixed(2) },
    { key: 'currentPrice', header: 'Current Price', align: 'right', render: (val) => val.toFixed(2) },
    { 
      key: 'pnl', 
      header: 'P&L', 
      align: 'right', 
      render: (val) => (
        <span style={{ color: val >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
          {val >= 0 ? '+' : ''}{val.toFixed(2)}
        </span>
      )
    },
    { 
      key: 'pnlPercent', 
      header: 'P&L %', 
      align: 'right', 
      render: (val) => (
        <span style={{ color: val >= 0 ? 'var(--color-green)' : 'var(--color-red)' }}>
          {val >= 0 ? '+' : ''}{val.toFixed(2)}%
        </span>
      )
    },
  ]

  const orderColumns: Column<Order>[] = [
    { key: 'symbol', header: 'Symbol', align: 'left' },
    { 
      key: 'side', 
      header: 'Side', 
      align: 'left', 
      render: (val) => (
        <span style={{ color: val === 'BUY' ? 'var(--color-green)' : 'var(--color-red)' }}>
          {val}
        </span>
      )
    },
    { key: 'type', header: 'Type', align: 'left' },
    { key: 'quantity', header: 'Quantity', align: 'right' },
    { key: 'price', header: 'Price', align: 'right', render: (val) => val ? val.toFixed(2) : '-' },
    { key: 'status', header: 'Status', align: 'left' },
    { 
      key: 'timestamp', 
      header: 'Time', 
      align: 'right', 
      render: (val) => new Date(val).toLocaleTimeString() 
    },
  ]

  const tradeColumns: Column<Trade>[] = [
    { 
      key: 'timestamp', 
      header: 'Time', 
      align: 'left', 
      render: (val) => new Date(val).toLocaleTimeString() 
    },
    { key: 'symbol', header: 'Symbol', align: 'left' },
    { 
      key: 'side', 
      header: 'Side', 
      align: 'left', 
      render: (val) => (
        <span style={{ color: val === 'BUY' ? 'var(--color-green)' : 'var(--color-red)' }}>
          {val}
        </span>
      )
    },
    { key: 'price', header: 'Price', align: 'right', render: (val) => val.toFixed(2) },
    { key: 'quantity', header: 'Quantity', align: 'right' },
  ]

  return (
    <div className={styles.tradingPage}>
      <h1 className={styles.pageTitle}>Trading Workspace</h1>

      <div className={styles.tradingGrid}>
        {/* Order Entry Panel */}
        <div className={styles.orderEntry}>
          <Panel title="Order Entry">
            <form onSubmit={handleSubmitOrder} className={styles.orderForm}>
              <div className={styles.formRow}>
                <label>Symbol</label>
                <select 
                /* NEED TO CHNAGE THIS to pairs we trade */
                  value={orderForm.symbol}
                  onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
                >
                  <option>BTC/USD</option>
                  <option>ETH/USD</option>
                  <option>SOL/USD</option>
                  <option>BNB/USD</option>
                </select>
              </div>

              <div className={styles.formRow}>
                <label>Side</label>
                <div className={styles.buttonGroup}>
                  <button
                    type="button"
                    className={`${styles.sideButton} ${styles.buyButton} ${orderForm.side === 'BUY' ? styles.active : ''}`}
                    onClick={() => setOrderForm({ ...orderForm, side: 'BUY' })}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    className={`${styles.sideButton} ${styles.sellButton} ${orderForm.side === 'SELL' ? styles.active : ''}`}
                    onClick={() => setOrderForm({ ...orderForm, side: 'SELL' })}
                  >
                    SELL
                  </button>
                </div>
              </div>

              <div className={styles.formRow}>
                <label>Type</label>
                <select 
                  value={orderForm.type}
                  onChange={(e) => setOrderForm({ ...orderForm, type: e.target.value as any })}
                >
                  <option>MARKET</option>
                  <option>LIMIT</option>
                  <option>STOP</option>
                </select>
              </div>

              <div className={styles.formRow}>
                <label>Quantity</label>
                <input
                  type="number"
                  step="0.0001"
                  value={orderForm.quantity}
                  onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })}
                  placeholder="0.0000"
                />
              </div>

              {orderForm.type !== 'MARKET' && (
                <div className={styles.formRow}>
                  <label>Price</label>
                  <input
                    type="number"
                    step="0.01"
                    value={orderForm.price}
                    onChange={(e) => setOrderForm({ ...orderForm, price: e.target.value })}
                    placeholder="0.00"
                  />
                </div>
              )}

              <button type="submit" className={styles.submitButton}>
                Submit Order
              </button>
            </form>
          </Panel>
        </div>

        {/* Positions */}
        <div className={styles.positions}>
          <Panel title="Open Positions">
            <DataTable 
              columns={positionColumns}
              data={positions}
              keyField="symbol"
            />
          </Panel>
        </div>
      </div>

      {/* Open Orders */}
      <Panel title="Open Orders">
        <DataTable 
          columns={orderColumns}
          data={orders}
          keyField="id"
        />
      </Panel>

      {/* Recent Trades */}
      <Panel title="Recent Trades">
        <DataTable 
          columns={tradeColumns}
          data={trades}
          keyField="id"
        />
      </Panel>
    </div>
  )
}

export default TradingPage
