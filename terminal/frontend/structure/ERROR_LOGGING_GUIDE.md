# Error Logging & Black Screen Debugging Guide

## 🚨 Black Screen Issues

If you're seeing a black screen when loading the app, the enhanced error logging system will help you debug it.

## What Was Added

### 1. Global Error Handlers (`src/utils/errorHandler.ts`)
Catches ALL errors before they crash the app:
- ✅ Uncaught JavaScript errors
- ✅ Unhandled promise rejections
- ✅ Console.error/warn logging
- ✅ Startup diagnostics
- ✅ Loading indicators

### 2. Error Boundary Component (`src/components/ErrorBoundary/`)
Catches React component errors and displays:
- Error name and message
- Full stack trace
- Component stack
- Reload button
- Download logs button

### 3. Enhanced Startup Logging
Logs every step of application initialization:
```
🚀 TRADING TERMINAL STARTING UP
✅ Error handlers initialized
📋 Application Information (browser, screen, etc.)
🔧 Environment (dev/prod)
📦 Browser Features (localStorage, WebSocket, etc.)
🔍 Running startup diagnostics
✅ All startup checks passed
🎨 Rendering React application
✅ React application rendered successfully
```

## How to Debug Black Screen

### Step 1: Open Developer Console
Press **F12** to open Developer Tools

### Step 2: Check Console Logs
You should see detailed startup logs. Look for:

#### ✅ **Successful Startup:**
```
🚀 TRADING TERMINAL STARTING UP
================================================================================
✅ Error handlers initialized
✅ All startup checks passed
✅ Root element found, creating React root...
✅ React application rendered successfully
✅ APPLICATION LOADED SUCCESSFULLY
```

#### ❌ **Failed Startup - Missing Root:**
```
❌ CRITICAL ERROR: Root element #root not found in DOM!
```
**Fix:** Check `index.html` has `<div id="root"></div>`

#### ❌ **Failed Startup - Module Error:**
```
❌ UNCAUGHT ERROR:
Cannot find module './pages/TradingPage'
```
**Fix:** File missing or wrong import path

#### ❌ **Failed Startup - React Error:**
```
❌ REACT ERROR CAUGHT BY ERROR BOUNDARY
Error: [error message]
Component Stack: [stack trace]
```
**Fix:** Check component code for errors

### Step 3: Enable Debug Panel
Press **Ctrl + Shift + D** to see all logs visually

### Step 4: Download Error Logs
If error screen appears, click "Download Error Logs" button

## Common Black Screen Causes

### 1. Import/Module Errors
**Symptoms:**
```
Cannot find module './components/Something'
```

**Fix:**
- Check file exists at specified path
- Check file extension (.tsx vs .ts)
- Check export statement

### 2. Missing Dependencies
**Symptoms:**
```
React is not defined
Cannot find module 'react-router-dom'
```

**Fix:**
```bash
npm install
```

### 3. Syntax Errors
**Symptoms:**
```
Unexpected token
SyntaxError
```

**Fix:**
- Check for missing brackets, semicolons
- Check for invalid JSX
- Run: `npm run build` to see all errors

### 4. Runtime Errors
**Symptoms:**
```
Cannot read property 'x' of undefined
TypeError
```

**Fix:**
- Check component logic
- Add null checks
- Use optional chaining `?.`

### 5. localStorage Issues
**Symptoms:**
```
localStorage is not available
QuotaExceededError
```

**Fix:**
- Check browser privacy settings
- Clear localStorage
- Try incognito mode

## Error Logging Features

### Browser Console Logs
All errors automatically logged with:
- 🎨 Color coding
- ⏰ Timestamps
- 📍 File locations
- 📊 Stack traces
- 🔍 Context data

### Error Boundary UI
If React crashes, you'll see:
- ⚠️ User-friendly error screen
- 📝 Error details (expandable)
- 🔄 Reload button
- 💾 Download logs button
- 🆘 Help instructions

### Loading Indicator
Shows while app initializes:
- ⏳ Loading spinner
- 📱 Status message
- 💡 Console hint

## Debugging Checklist

When you see a black screen:

- [ ] 1. Open DevTools (F12)
- [ ] 2. Check Console tab for errors
- [ ] 3. Look for startup logs
- [ ] 4. Check Network tab for failed loads
- [ ] 5. Enable debug panel (Ctrl+Shift+D)
- [ ] 6. Download error logs
- [ ] 7. Try hard refresh (Ctrl+Shift+R)
- [ ] 8. Clear cache and reload
- [ ] 9. Check `index.html` has root div
- [ ] 10. Verify `npm install` ran successfully

## Error Handler API

### In Your Code

```typescript
import { logger } from './utils/logger'

try {
  // your code
} catch (error) {
  logger.error('Category', 'Description', error)
}
```

### Error Categories

- `Startup` - App initialization
- `Global` - Uncaught errors
- `Console` - Console errors
- `API` - API errors
- `WebSocket` - Connection errors
- `UI` - Component errors

## Production Deployment

### Disable Debug Features

In production, you may want to:

```typescript
// src/utils/errorHandler.ts
export function initializeErrorHandlers(): void {
  if (import.meta.env.PROD) {
    // Simplified error handling for production
    window.addEventListener('error', (event) => {
      // Send to error tracking service
      console.error('Production error:', event.message)
    })
  } else {
    // Full debugging in development
    // ... existing code
  }
}
```

### Error Tracking Integration

Add services like:
- Sentry
- LogRocket  
- Bugsnag

```typescript
window.addEventListener('error', (event) => {
  // Send to tracking service
  Sentry.captureException(event.error)
  
  // Keep local logging
  logger.error('Global', 'Error', event.error)
})
```

## Testing Error Handling

### Trigger Test Errors

```javascript
// In browser console

// Test uncaught error
throw new Error('Test error')

// Test unhandled rejection
Promise.reject('Test rejection')

// Test component error
// Click something that triggers error in component
```

### Verify Logging

1. Trigger error
2. Check console for log entry
3. Open debug panel (Ctrl+Shift+D)
4. Verify error appears in panel
5. Download logs
6. Verify JSON contains error

## Files Modified

### New Files
- ✅ `src/utils/errorHandler.ts` - Global error handlers
- ✅ `src/components/ErrorBoundary/ErrorBoundary.tsx` - Error boundary
- ✅ `src/components/ErrorBoundary/ErrorBoundary.module.css` - Styling

### Modified Files
- ✅ `src/main.tsx` - Added error handlers and logging
- ✅ `src/App.tsx` - Added error logging and verification

## Next Steps

1. **Run the app:**
   ```bash
   npm run dev
   ```

2. **Watch startup logs in console:**
   - Should see detailed initialization logs
   - Any errors will be highlighted

3. **If black screen persists:**
   - Check console for red error messages
   - Look for specific error in startup logs
   - Download error logs
   - Share error details

4. **Report issues with:**
   - Console error messages
   - Downloaded error logs
   - Browser/OS information
   - Steps to reproduce

## Emergency Recovery

If app won't load at all:

1. **Clear all state:**
   ```javascript
   // In browser console
   localStorage.clear()
   sessionStorage.clear()
   location.reload()
   ```

2. **Reinstall dependencies:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Hard refresh:**
   - Chrome/Firefox: Ctrl+Shift+R
   - Safari: Cmd+Option+R

4. **Try different browser:**
   - Test in Chrome/Firefox/Safari
   - Test in incognito mode

## Support

With the enhanced error logging, you can now:
- ✅ See exactly where app fails
- ✅ Get detailed error messages
- ✅ Download complete logs
- ✅ Share specific error details
- ✅ Debug issues systematically

**Press F12 and Ctrl+Shift+D now to see the logging in action!**
