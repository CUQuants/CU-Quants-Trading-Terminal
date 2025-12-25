// Keyboard shortcut hook for power users
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  alt?: boolean
  shift?: boolean
  action: () => void
}

export const useKeyboardShortcuts = () => {
  const navigate = useNavigate()

  useEffect(() => {
    const shortcuts: KeyboardShortcut[] = [
      // Navigation shortcuts
      { key: 'h', alt: true, action: () => navigate('/') },
      { key: 't', alt: true, action: () => navigate('/trading') },
      { key: 's', alt: true, action: () => navigate('/settings') },
      
      // Trading shortcuts
      { key: 'b', ctrl: true, action: () => console.log('Quick buy') },
      { key: 's', ctrl: true, action: () => console.log('Quick sell') },
    ]

    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey
        const altMatch = shortcut.alt ? event.altKey : !event.altKey
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
        
        if (
          event.key.toLowerCase() === shortcut.key &&
          ctrlMatch &&
          altMatch &&
          shiftMatch
        ) {
          event.preventDefault()
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [navigate])
}
