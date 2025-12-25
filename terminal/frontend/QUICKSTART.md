# Quick Start Guide
## CU Quants Trading Terminal

### Installation

1. **Install Dependencies**
   ```bash
   cd /Users/sammy/Downloads/quant/trader/CU-Quants-Trading-Terminal/terminal/frontend
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   ```

3. **Open in Browser**
   Navigate to: `http://localhost:3000`

### First Time Setup

1. **Navigate to Settings** (Alt + S or click Settings in sidebar)
2. **Enter API Credentials**:
   - Add your Kraken API Key
   - Add your Kraken API Secret
   - Click "Save Configuration"

3. **Return to Home** (Alt + H)
   - View market overview
   - Check system status

4. **Start Trading** (Alt + T)
   - Use order entry panel
   - Monitor open positions
   - Track recent trades

### Directory Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   ├── pages/            # Main application pages
│   ├── hooks/            # Custom React hooks
│   ├── types/            # TypeScript type definitions
│   └── styles/           # Global styles and theme
├── index.html            # HTML entry point
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript configuration
└── vite.config.ts        # Vite build configuration
```

### Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

### Key Features

**Market Ticker**
- Always visible at top
- 14 instruments with live prices
- Hover to pause scrolling

**Navigation**
- Home: Market overview and statistics
- Trading: Order entry and position management
- Settings: API configuration and system info

**Keyboard Shortcuts**
- Alt + H: Home page
- Alt + T: Trading page
- Alt + S: Settings page

### Customization

**Colors** (`src/styles/global.css`):
```css
--color-black: #000000;
--color-blue: #0066CC;
--color-white: #FFFFFF;
```

**Layout** (`src/components/Layout/Layout.module.css`):
```css
--nav-width: 60px;
--ticker-height: 36px;
```

### Development Notes

- Uses **Vite** for fast HMR
- **TypeScript** for type safety
- **CSS Modules** for scoped styling
- **React Router** for navigation
- No external UI libraries (custom components)

### Troubleshooting

**Port already in use?**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

**Dependencies not installing?**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**TypeScript errors?**
```bash
# Restart TypeScript server in VS Code
Cmd + Shift + P -> "TypeScript: Restart TS Server"
```

### Next Steps

1. Integrate real Kraken API endpoints
2. Add WebSocket for live data
3. Implement order execution
4. Add charting capabilities
5. Build alert system

---

For questions: saba6682@colorado.edu
