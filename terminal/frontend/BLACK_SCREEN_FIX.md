# 🚨 Black Screen Debugging - QUICK START

## You're seeing a black screen? Here's what to do:

### 1. Open Developer Console
**Press F12** (or Cmd+Option+I on Mac)

### 2. Look at the Console Tab
You should now see detailed startup logs like:

```
🚀 TRADING TERMINAL STARTING UP
================================================================================
✅ Error handlers initialized
📋 Application Information { ... }
🔧 Environment { mode: "development", dev: true }
📦 Browser Features { localStorage: true, webSocket: true }
🔍 Running startup diagnostics...
✅ All startup checks passed
✅ Root element found, creating React root...
🎨 Rendering React application...
✅ React application rendered successfully
✅ APPLICATION LOADED SUCCESSFULLY
💡 Press Ctrl+Shift+D to open debug panel
```

### 3. If You See Errors

#### ❌ Red errors in console?
Look for messages like:
- `Cannot find module` → Missing file or wrong import
- `undefined is not a function` → Code error
- `Failed to fetch` → Network/API issue

#### ❌ Error Boundary Screen?
You'll see a nice error UI with:
- Error message
- Stack trace (expandable)
- "Reload Application" button
- "Download Error Logs" button

### 4. Enable Debug Panel
**Press Ctrl + Shift + D** (or click 🐛 button if visible)

This shows all logs in a visual panel:
- Color-coded by severity
- Last 100 logs
- Real-time updates
- Download button

## Common Issues & Fixes

### Issue: Port Already in Use
```
Error: Port 3000 is already in use
```
**You're already running the dev server!** 
- Open browser to `http://localhost:5173`
- Or kill the process and restart

### Issue: Cannot Find Module
```
Cannot find module './pages/TradingPage'
```
**Fix:**
```bash
# Make sure all files exist
ls src/pages/
# Should show: HomePage.tsx, TradingPage.tsx, SettingsPage.tsx
```

### Issue: Blank White/Black Screen, No Errors
**Try:**
1. Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
2. Clear cache
3. Check if JavaScript is enabled
4. Try incognito mode

### Issue: localStorage Error
```
localStorage is not available
```
**Fix:** Check browser privacy settings or use incognito mode

## What The Error Logging Does

### Before (Old Behavior)
- Black screen 😞
- No information
- Hard to debug

### After (With Error Logging) ✅
1. **Loading Indicator** shows while app starts
2. **Detailed Startup Logs** in console
3. **Error Boundary** catches React errors
4. **Visual Error Screen** with details
5. **Download Logs** button for support
6. **Debug Panel** for live monitoring

## Your Dev Server

The dev server is already running! Just open:
- **URL:** http://localhost:5173 (or check console for actual port)
- **Press F12** to see logs
- **Press Ctrl+Shift+D** for debug panel

## Still Having Issues?

### Get Error Details

1. **Open Console (F12)**
2. **Copy all red error messages**
3. **Press Ctrl+Shift+D**
4. **Click "Download" in debug panel**
5. **Share the error logs**

### Emergency Recovery

```bash
# Clear everything and start fresh
cd /Users/sammy/Downloads/quant/trader/CU-Quants-Trading-Terminal/terminal/frontend

# Clear browser state
# In browser console:
localStorage.clear()
sessionStorage.clear()

# Hard refresh
# Ctrl+Shift+R or Cmd+Shift+R

# If still issues, reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## What Was Added

✅ **Global Error Handlers** - Catch ALL errors
✅ **Error Boundary** - React error catching  
✅ **Startup Logging** - See initialization steps
✅ **Loading Indicator** - Visual feedback
✅ **Debug Panel** - Live log viewer
✅ **Error Screen** - User-friendly error display
✅ **Download Logs** - Export for debugging

## Files Created

- `src/utils/errorHandler.ts` - Error handling system
- `src/components/ErrorBoundary/` - Error UI
- `ERROR_LOGGING_GUIDE.md` - Full documentation

## Next Steps

1. **Open browser** to http://localhost:5173
2. **Press F12** to open console
3. **Look for startup logs** (should be detailed now)
4. **If errors appear**, they'll be clearly logged
5. **Press Ctrl+Shift+D** to see debug panel

---

**The black screen should now show you EXACTLY what's wrong! Check the console (F12) now.** 🔍
