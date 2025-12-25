import { ReactNode } from 'react'
import MarketTicker from '../MarketTicker/MarketTicker'
import Sidebar from '../Sidebar/Sidebar'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import styles from './Layout.module.css'

interface LayoutProps {
  children: ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  // Enable keyboard shortcuts
  useKeyboardShortcuts()

  return (
    <div className={styles.layout}>
      <MarketTicker />
      <Sidebar />
      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  )
}

export default Layout
