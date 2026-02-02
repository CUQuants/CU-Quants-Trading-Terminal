import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Panel from '../components/Panel/Panel'
import styles from './LoginPage.module.css'
import { uiLogger } from '../utils/logger'

const LogoutPage = () => {
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(true)

  useEffect(() => {
    const performLogout = async () => {
      uiLogger.info('LogoutPage: Logging out user')

      // TODO: Replace with actual backend API call
      // Placeholder: simulate logout
      try {
        await new Promise(resolve => setTimeout(resolve, 300))
        
        // Clear auth state
        localStorage.removeItem('authUser')
        
        uiLogger.info('LogoutPage: Logout successful (placeholder)')
        setIsLoggingOut(false)
        
        // Redirect to login after a short delay
        setTimeout(() => {
          navigate('/login')
        }, 1500)
      } catch (err) {
        uiLogger.error('LogoutPage: Logout failed', err)
        setIsLoggingOut(false)
      }
    }

    performLogout()
  }, [navigate])

  return (
    <div className={styles.authPage}>
      <Panel title="Logout">
        <h1 className={styles.pageTitle}>Sign Out</h1>
        
        {isLoggingOut ? (
          <div className={styles.placeholderNotice}>
            Signing you out...
          </div>
        ) : (
          <>
            <div className={styles.successMessage}>
              You have been successfully logged out.
            </div>
            <div className={styles.placeholderNotice}>
              Redirecting to login page...
            </div>
          </>
        )}
      </Panel>
    </div>
  )
}

export default LogoutPage
