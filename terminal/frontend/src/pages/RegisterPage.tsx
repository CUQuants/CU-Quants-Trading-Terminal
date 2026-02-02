import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Panel from '../components/Panel/Panel'
import styles from './LoginPage.module.css'
import { uiLogger } from '../utils/logger'

const RegisterPage = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
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

    uiLogger.info('RegisterPage: Registration attempt', { email: formData.email })

    // TODO: Replace with actual backend API call
    // Placeholder: simulate registration
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Placeholder validation
      if (!formData.email || !formData.password || !formData.confirmPassword) {
        throw new Error('Please fill in all fields')
      }

      if (formData.password !== formData.confirmPassword) {
        throw new Error('Passwords do not match')
      }

      if (formData.password.length < 8) {
        throw new Error('Password must be at least 8 characters')
      }

      // Placeholder: store auth state
      localStorage.setItem('authUser', JSON.stringify({ 
        email: formData.email,
        registeredAt: new Date().toISOString()
      }))

      uiLogger.info('RegisterPage: Registration successful (placeholder)')
      navigate('/')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Registration failed'
      setError(message)
      uiLogger.error('RegisterPage: Registration failed', err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.authPage}>
      <Panel title="Register">
        <h1 className={styles.pageTitle}>Create Account</h1>
        
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
              placeholder="Min. 8 characters"
              autoComplete="new-password"
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              className={styles.input}
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </div>

          <button 
            type="submit" 
            className={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </button>

          <p className={styles.linkText}>
            Already have an account? <Link to="/login">Sign In</Link>
          </p>
        </form>

        <div className={styles.placeholderNotice}>
          ⚠️ This is a placeholder registration page. Backend authentication will be implemented later.
        </div>
      </Panel>
    </div>
  )
}

export default RegisterPage
