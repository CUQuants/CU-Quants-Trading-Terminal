import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Panel from '../components/Panel/Panel'
import styles from './LoginPage.module.css'
import { uiLogger } from '../utils/logger'

const LoginPage = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    uiLogger.info('LoginPage: Login attempt', { email: formData.email })

    // TODO: Replace with actual backend API call
    // Placeholder: simulate login
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Placeholder validation
      if (!formData.email || !formData.password) {
        throw new Error('Please fill in all fields')
      }

      // Placeholder: store auth state
      localStorage.setItem('authUser', JSON.stringify({ 
        email: formData.email,
        loggedInAt: new Date().toISOString()
      }))

      uiLogger.info('LoginPage: Login successful (placeholder)')
      navigate('/')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed'
      setError(message)
      uiLogger.error('LoginPage: Login failed', err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.authPage}>
      <Panel title="Login">
        <h1 className={styles.pageTitle}>Sign In</h1>
        
        <form className={styles.authForm} onSubmit={handleSubmit}>
          {error && <div className={styles.errorMessage}>{error}</div>}
          
          <div className={styles.formGroup}>
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              className={styles.input}
              value={formData.email}
              onChange={handleChange}
              placeholder="your@email.com"
              autoComplete="email"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              className={styles.input}
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          <button 
            type="submit" 
            className={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>

          <p className={styles.linkText}>
            Don't have an account? <Link to="/register">Register</Link>
          </p>
        </form>

        <div className={styles.placeholderNotice}>
          ⚠️ This is a placeholder login page. Backend authentication will be implemented later.
        </div>
      </Panel>
    </div>
  )
}

export default LoginPage
