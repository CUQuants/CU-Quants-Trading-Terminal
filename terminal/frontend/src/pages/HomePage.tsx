import Panel from '../components/Panel/Panel'
import DataTable, { Column } from '../components/DataTable/DataTable'
import type { MarketData } from '../types'
import styles from './HomePage.module.css'

// Mock market data
const MARKET_DATA: MarketData[] = [
  { symbol: 'BTC/USD', bid: 42348.50, ask: 42352.50, last: 42350.50, volume: 1245678, high24h: 43200, low24h: 41800 },
  { symbol: 'ETH/USD', bid: 2244.75, ask: 2246.75, last: 2245.75, volume: 8765432, high24h: 2280, low24h: 2210 },
  { symbol: 'SOL/USD', bid: 98.40, ask: 98.44, last: 98.42, volume: 5432109, high24h: 102, low24h: 95 },
  { symbol: 'BNB/USD', bid: 315.18, ask: 315.22, last: 315.20, volume: 987654, high24h: 320, low24h: 310 },
  { symbol: 'XRP/USD', bid: 0.6232, ask: 0.6236, last: 0.6234, volume: 12345678, high24h: 0.64, low24h: 0.61 },
]

interface VolatilityData {
  symbol: string
  vol24h: number
  vol7d: number
  vol30d: number
}

const VOLATILITY_DATA: VolatilityData[] = [
  { symbol: 'BTC/USD', vol24h: 3.2, vol7d: 12.5, vol30d: 28.4 },
  { symbol: 'ETH/USD', vol24h: 4.8, vol7d: 15.2, vol30d: 32.1 },
  { symbol: 'SOL/USD', vol24h: 8.2, vol7d: 22.7, vol30d: 45.3 },
  { symbol: 'BNB/USD', vol24h: 2.9, vol7d: 10.1, vol30d: 24.8 },
  { symbol: 'XRP/USD', vol24h: 5.1, vol7d: 18.4, vol30d: 38.9 },
]

const HomePage = () => {
  const marketColumns: Column<MarketData>[] = [
    { key: 'symbol', header: 'Symbol', align: 'left' },
    { key: 'last', header: 'Last', align: 'right', render: (val) => val.toFixed(2) },
    { key: 'bid', header: 'Bid', align: 'right', render: (val) => val.toFixed(2) },
    { key: 'ask', header: 'Ask', align: 'right', render: (val) => val.toFixed(2) },
    { key: 'volume', header: 'Volume', align: 'right', render: (val) => val.toLocaleString() },
    { key: 'high24h', header: '24h High', align: 'right', render: (val) => val.toFixed(2) },
    { key: 'low24h', header: '24h Low', align: 'right', render: (val) => val.toFixed(2) },
  ]

  const volatilityColumns: Column<VolatilityData>[] = [
    { key: 'symbol', header: 'Symbol', align: 'left' },
    { key: 'vol24h', header: '24h Vol %', align: 'right', render: (val) => `${val.toFixed(2)}%` },
    { key: 'vol7d', header: '7d Vol %', align: 'right', render: (val) => `${val.toFixed(2)}%` },
    { key: 'vol30d', header: '30d Vol %', align: 'right', render: (val) => `${val.toFixed(2)}%` },
  ]

  return (
    <div className={styles.homePage}>
      <h1 className={styles.pageTitle}>Market Overview</h1>
      
      <Panel title="Market Summary">
        <DataTable 
          columns={marketColumns}
          data={MARKET_DATA}
          keyField="symbol"
        />
      </Panel>

      <Panel title="Volatility Snapshot">
        <DataTable 
          columns={volatilityColumns}
          data={VOLATILITY_DATA}
          keyField="symbol"
        />
      </Panel>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total Volume 24h</div>
          <div className={styles.statValue}>$2.84B</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Active Markets</div>
          <div className={styles.statValue}>14</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Avg Spread</div>
          <div className={styles.statValue}>0.08%</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>System Status</div>
          <div className={styles.statValue} style={{ color: 'var(--color-green)' }}>ONLINE</div>
        </div>
      </div>
    </div>
  )
}

export default HomePage
