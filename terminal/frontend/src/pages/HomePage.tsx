import Panel from '../components/Panel/Panel'
import Watchlist from '../components/Watchlist/Watchlist'
import styles from './HomePage.module.css'

const HomePage = () => {
  return (
    <div className={styles.homePage}>
      <h1 className={styles.pageTitle}>Market Overview</h1>
      
      <div className={styles.mainLayout}>
        <div className={styles.watchlistPanel}>
          <Watchlist />
        </div>

        <div className={styles.contentPanel}>
          <Panel title="Getting Started">
            <div className={styles.instructions}>
              <h3>Welcome to CU Quants Trading Terminal</h3>
              <ul>
                <li><strong>Add markets to your watchlist</strong></li>
                <li><strong>Markets in watchlist appear in the ticker</strong> - Real-time updates via WebSocket</li>
                <li><strong>Load pairs in ladders</strong> - View detailed order book depth</li>
                <li><strong>Your watchlist persists</strong> - Saved to localStorage automatically</li>
              </ul>
              
              <h4>Quick Start:</h4>
              <ol>
                <li>Add a trading pair to your watchlist (e.g., XBT/USD, ETH/USD)</li>
                <li>View real-time bid/ask/spread data</li>
                <li><strong>Add API credentials in Settings to enable trading</strong></li>
              </ol>


            </div>
          </Panel>

          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>WebSocket Status</div>
              <div className={styles.statValue} style={{ color: 'var(--color-green)' }}>ACTIVE</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Watched Markets</div>
              <div className={styles.statValue}>Dynamic</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Update Interval</div>
              <div className={styles.statValue}>Real-time</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>System Status</div>
              <div className={styles.statValue} style={{ color: 'var(--color-green)' }}>ONLINE</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage
