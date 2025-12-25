# Bloomberg-Style Trading Terminal - Complete Implementation
## Project Structure & File Guide

## 📁 Complete Directory Structure

```
frontend/
├── index.html                          # HTML entry point
├── package.json                        # Dependencies and scripts
├── tsconfig.json                       # TypeScript configuration
├── tsconfig.node.json                  # TypeScript config for Vite
├── vite.config.ts                      # Vite build tool configuration
├── .gitignore                          # Git ignore rules
├── README.md                           # Main documentation
├── QUICKSTART.md                       # Quick start guide
│
└── src/
    ├── main.tsx                        # React application entry
    ├── App.tsx                         # Root app component with routing
    ├── vite-env.d.ts                   # Vite type declarations
    │
    ├── components/                     # Reusable UI components
    │   ├── Layout/
    │   │   ├── Layout.tsx              # Main app shell with ticker + sidebar
    │   │   └── Layout.module.css       # Layout styles
    │   │
    │   ├── MarketTicker/
    │   │   ├── MarketTicker.tsx        # Top horizontal scrolling ticker
    │   │   └── MarketTicker.module.css # Ticker animation and styling
    │   │
    │   ├── Sidebar/
    │   │   ├── Sidebar.tsx             # Left navigation bar
    │   │   └── Sidebar.module.css      # Sidebar hover expand styles
    │   │
    │   ├── DataTable/
    │   │   ├── DataTable.tsx           # Generic table component
    │   │   └── DataTable.module.css    # Professional table styling
    │   │
    │   └── Panel/
    │       ├── Panel.tsx               # Section container component
    │       └── Panel.module.css        # Panel header/content styles
    │
    ├── pages/                          # Main application pages
    │   ├── HomePage.tsx                # Market overview dashboard
    │   ├── HomePage.module.css         # Home page styles
    │   ├── TradingPage.tsx             # Order entry and positions
    │   ├── TradingPage.module.css      # Trading page styles
    │   ├── SettingsPage.tsx            # API configuration
    │   └── SettingsPage.module.css     # Settings page styles
    │
    ├── hooks/                          # Custom React hooks
    │   └── useKeyboardShortcuts.ts     # Keyboard navigation hook
    │
    ├── types/                          # TypeScript type definitions
    │   └── index.ts                    # All interface definitions
    │
    └── styles/                         # Global styles
        └── global.css                  # Theme, colors, reset styles
```

---

## 📄 File Descriptions

### Configuration Files

**`package.json`**
- React, React Router, TypeScript dependencies
- Vite dev server and build scripts
- ESLint configuration

**`tsconfig.json`**
- TypeScript compiler options
- Module resolution settings
- Strict type checking enabled

**`vite.config.ts`**
- Vite plugin configuration
- Dev server port: 3000
- React plugin with fast refresh

---

### Entry Points

**`index.html`**
- Single-page app HTML shell
- Mounts React at `#root`
- Loads `src/main.tsx`

**`src/main.tsx`**
- ReactDOM render
- Router provider setup
- Global CSS import

**`src/App.tsx`**
- React Router configuration
- Route definitions (/, /trading, /settings)
- Layout wrapper

---

### Layout Components

**`Layout.tsx`**
- Main app shell structure
- Renders MarketTicker (top)
- Renders Sidebar (left)
- Main content area with children
- Keyboard shortcut initialization

**`MarketTicker.tsx`**
- Fixed top bar (36px height)
- Displays 14 instruments
- Auto-scroll animation
- Pause on hover
- Live price simulation

**`Sidebar.tsx`**
- Fixed left navigation (60px default)
- Expands to 200px on hover
- Home, Trading, Settings links
- Blue active indicator
- React Router integration

---

### Reusable Components

**`DataTable.tsx`**
- Generic table with configurable columns
- Type-safe with TypeScript generics
- Custom render functions per column
- Row click handlers
- Empty state handling
- Alignment options (left/right/center)

**`Panel.tsx`**
- Section container with header
- Title and optional header actions
- Consistent styling across pages
- Blue header separator line

---

### Pages

**`HomePage.tsx`**
- Market summary table (bid/ask/volume)
- Volatility snapshot table
- Statistics cards (4-column grid)
- System status indicators

**`TradingPage.tsx`**
- Order entry form (symbol, side, type, quantity, price)
- Open positions table with P&L
- Open orders table
- Recent trades table
- Color-coded buy/sell buttons
- Green/red P&L indicators

**`SettingsPage.tsx`**
- API key/secret configuration
- Masked input fields with show/hide toggle
- Connection status dashboard
- System information panel
- LocalStorage integration

---

### Hooks

**`useKeyboardShortcuts.ts`**
- Alt + H: Home navigation
- Alt + T: Trading navigation
- Alt + S: Settings navigation
- Ctrl + B/S: Quick buy/sell (placeholders)
- Prevents default browser behavior

---

### Types

**`types/index.ts`**
- `TickerData`: Market ticker information
- `Order`: Order structure
- `Position`: Trading position
- `MarketData`: Market quotes
- `Trade`: Executed trade
- `ApiSettings`: API credentials

---

### Styles

**`global.css`**
- CSS variables for colors and spacing
- Black/blue/white color scheme
- Monospace font for numbers
- Table default styling
- Scrollbar customization
- Input/button resets
- Focus states for accessibility

---

## 🎨 Design System

### Colors
```css
--color-black: #000000      /* Backgrounds */
--color-blue: #0066CC       /* Accents, active states */
--color-white: #FFFFFF      /* Text */
--color-green: #00FF00      /* Positive price moves */
--color-red: #FF0000        /* Negative price moves */
```

### Typography
```css
--font-mono: 'IBM Plex Mono', 'Consolas', monospace
--font-sans: System fonts
```

### Spacing
```css
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 12px
--spacing-lg: 16px
--spacing-xl: 24px
```

### Layout Dimensions
```css
--nav-width: 60px
--nav-width-expanded: 200px
--ticker-height: 36px
```

---

## 🚀 Component Usage Examples

### DataTable
```tsx
const columns: Column<Position>[] = [
  { key: 'symbol', header: 'Symbol', align: 'left' },
  { key: 'pnl', header: 'P&L', align: 'right', 
    render: (val) => <span style={{color: val >= 0 ? 'green' : 'red'}}>
      {val.toFixed(2)}
    </span>
  },
]

<DataTable 
  columns={columns}
  data={positions}
  keyField="symbol"
  onRowClick={(row) => console.log(row)}
/>
```

### Panel
```tsx
<Panel 
  title="Market Summary" 
  headerActions={<button>Refresh</button>}
>
  <YourContent />
</Panel>
```

---

## 🔧 Development Workflow

1. **Install**: `npm install`
2. **Develop**: `npm run dev` (http://localhost:3000)
3. **Build**: `npm run build` (outputs to `dist/`)
4. **Preview**: `npm run preview`

---

## 📝 Key Features Implemented

✅ Bloomberg-style black/blue/white theme  
✅ Auto-scrolling market ticker (14 instruments)  
✅ Collapsible sidebar navigation  
✅ Professional data tables  
✅ Home page with market overview  
✅ Trading page with order entry  
✅ Settings page with API key management  
✅ Keyboard shortcuts (Alt+H/T/S)  
✅ Responsive grid layouts  
✅ TypeScript type safety  
✅ CSS Modules for scoped styling  
✅ No external UI libraries  

---

## 🎯 Future Integration Points

### Kraken API
```typescript
// In Settings: Store credentials
// In Trading: Execute orders
// In Ticker: Real-time WebSocket feeds
```

### WebSocket Setup
```typescript
const ws = new WebSocket('wss://ws.kraken.com/')
ws.onmessage = (event) => {
  // Update ticker prices
  // Update order status
  // Update positions
}
```

---

## 📞 Contact

**Engineering**: Samuel Balent (saba6682@colorado.edu)  
**Trading**: Ryan Watts  
**Risk Management**: Magnus Miller  

---

**CU Quants Trading Terminal** v1.0  
Built with React + TypeScript + Vite
