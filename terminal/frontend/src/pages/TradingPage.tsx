import { useState } from 'react'
import Panel from '../components/Panel/Panel'
import DataTable, { Column } from '../components/DataTable/DataTable'
import type { Order, Position, Trade } from '../types'
import styles from './TradingPage.module.css'

// Mock data
const MOCK_POSITIONS: Position[] = [
  { symbol: 'BTC/USD', quantity: 0.5, avgPrice: 41200, currentPrice: 42350.50, pnl: 575.25, pnlPercent: 1.40 },
  { symbol: 'ETH/USD', quantity: 10, avgPrice: 2300, currentPrice: 2245.75, pnl: -542.50, pnlPercent: -2.36 },
  { symbol: 'SOL/USD', quantity: 50, avgPrice: 92, currentPrice: 98.42, pnl: 321.00, pnlPercent: 6.98 },
]

const MOCK_ORDERS: Order[] = [
  { id: '1', symbol: 'BTC/USD', side: 'BUY', type: 'LIMIT', quantity: 0.25, price: 41500, status: 'OPEN', timestamp: Date.now() - 3600000 },
  { id: '2', symbol: 'ETH/USD', side: 'SELL', type: 'LIMIT', quantity: 5, price: 2300, status: 'OPEN', timestamp: Date.now() - 7200000 },
]

const MOCK_TRADES: Trade[] = [
  { id: 't1', symbol: 'BTC/USD', side: 'BUY', price: 42350.50, quantity: 0.1, timestamp: Date.now() - 600000 },
  { id: 't2', symbol: 'SOL/USD', side: 'BUY', price: 98.42, quantity: 10, timestamp: Date.now() - 1200000 },
  { id: 't3', symbol: 'ETH/USD', side: 'SELL', price: 2245.75, quantity: 2, timestamp: Date.now() - 1800000 },
]

const TradingPage = () => {
  const [orderForm, setOrderForm] = useState({
    symbol: 'BTC/USD',
    side: 'BUY' as 'BUY' | 'SELL',
    type: 'LIMIT' as 'MARKET' | 'LIMIT' | 'STOP',
    quantity: '',
    price: '',
  })

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
              data={MOCK_POSITIONS}
              keyField="symbol"
            />
          </Panel>
        </div>
      </div>

      {/* Open Orders */}
      <Panel title="Open Orders">
        <DataTable 
          columns={orderColumns}
          data={MOCK_ORDERS}
          keyField="id"
        />
      </Panel>

      {/* Recent Trades */}
      <Panel title="Recent Trades">
        <DataTable 
          columns={tradeColumns}
          data={MOCK_TRADES}
          keyField="id"
        />
      </Panel>
    </div>
  )
}

export default TradingPage
