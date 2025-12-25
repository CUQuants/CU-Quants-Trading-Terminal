import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import styles from './Sidebar.module.css'

interface NavItem {
  path: string
  label: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Home', icon: '⌂' },
  { path: '/trading', label: 'Trading', icon: '⚡' },
  { path: '/settings', label: 'Settings', icon: '⚙' },
]

const Sidebar = () => {
  const [isExpanded, setIsExpanded] = useState(false)
  const location = useLocation()

  return (
    <nav 
      className={`${styles.sidebar} ${isExpanded ? styles.expanded : ''}`}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <div className={styles.navItems}>
        {NAV_ITEMS.map(item => {
          const isActive = location.pathname === item.path
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              <span className={styles.icon}>{item.icon}</span>
              <span className={styles.label}>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export default Sidebar
