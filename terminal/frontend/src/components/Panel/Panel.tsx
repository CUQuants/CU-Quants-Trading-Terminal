import styles from './Panel.module.css'
import { ReactNode } from 'react'

interface PanelProps {
  title: string
  children: ReactNode
  className?: string
  headerActions?: ReactNode
}

const Panel = ({ title, children, className, headerActions }: PanelProps) => {
  return (
    <div className={`${styles.panel} ${className || ''}`}>
      <div className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        {headerActions && (
          <div className={styles.actions}>{headerActions}</div>
        )}
      </div>
      <div className={styles.content}>
        {children}
      </div>
    </div>
  )
}

export default Panel
