# CU Quants Trading Terminal - Frontend
**Version 1.0**  
**Bloomberg-Style Professional Trading Interface**  
**December 25, 2025**

## TLDR 
For running use:
- ./install.sh
- 

## Overview

A professional, institutional-grade trading terminal built with React and TypeScript. Features a  **black, blue, and white** color scheme inspired by Bloomberg Terminal, designed for quantitative trading and market monitoring.

## Design Principles

- **High Information Density**: Maximum data visibility with minimal chrome
- **No Consumer UI Elements**: No rounded corners, gradients, or shadows
- **Professional Aesthetics**: Sharp edges, monospace fonts, grid-aligned layouts
- **Keyboard-First**: Power user shortcuts and focus management
- **Performance Focused**: Minimal animations, fast updates, low latency

## Color Scheme (Strict)

- **Black** (`#000000`): Primary background
- **Blue** (`#0066CC`): Accents, active states, section dividers
- **White** (`#FFFFFF`): Primary text and data
- **Green/Red**: Price movement indicators only

## Architecture

```
src/
├── components/
│   ├── Layout/           # Main app shell
│   ├── MarketTicker/     # Top horizontal ticker
│   ├── Sidebar/          # Left navigation
│   ├── DataTable/        # Reusable table component
│   └── Panel/            # Section container
├── pages/
│   ├── HomePage.tsx      # Market overview
│   ├── TradingPage.tsx   # Order entry & positions
│   └── SettingsPage.tsx  # API configuration
├── hooks/
│   └── useKeyboardShortcuts.ts
├── types/
│   └── index.ts          # TypeScript definitions
└── styles/
    └── global.css        # Theme and reset
```

## Key Features

### Market Ticker (Always Visible)
- Fixed top bar displaying 14 instruments simultaneously
- Auto-scrolling with pause-on-hover
- Real-time price updates with color-coded changes
- Symbol, last price, change, and percent change

### Navigation
- Collapsible left sidebar
- Three main sections: Home, Trading, Settings
- Blue accent bar indicates active page
- Expand on hover for labels

### Home Page
- Market summary table with bid/ask/volume
- Volatility snapshot (24h, 7d, 30d)
- System statistics dashboard
- Dense tabular layout

### Trading Page
- **Order Entry Panel**: Symbol, side, type, quantity, price
- **Open Positions**: Real-time P&L tracking
- **Open Orders**: Active order monitoring
- **Recent Trades**: Trade history table
- Color-coded buy/sell indicators

### Settings Page
- API key configuration with masked inputs
- Connection status monitoring
- System information dashboard
- Secure local storage

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt + H` | Navigate to Home |
| `Alt + T` | Navigate to Trading |
| `Alt + S` | Navigate to Settings |
| `Ctrl + B` | Quick Buy (placeholder) |
| `Ctrl + S` | Quick Sell (placeholder) |

## Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Development

The app runs on **Vite** for fast development with HMR (Hot Module Replacement).

Access at: `http://localhost:3000`

## Component Usage

### DataTable
```tsx
<DataTable 
  columns={columns}
  data={data}
  keyField="id"
  onRowClick={(row) => console.log(row)}
/>
```

### Panel
```tsx
<Panel title="Section Title" headerActions={<button>Action</button>}>
  <YourContent />
</Panel>
```

## Integration Points

### API Configuration
- Users configure Kraken API keys in Settings
- Keys stored in localStorage (encrypt in production)
- All trading operations use configured credentials

### WebSocket (Future)
- Real-time market data via Kraken WebSocket
- Live order updates
- Position tracking

### REST API (Future)
- Account management
- Historical data
- Order execution

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Security Notes

⚠️ **Important**: Current implementation stores API keys in localStorage for demo purposes. In production:
- Encrypt sensitive data
- Use secure backend storage
- Implement proper authentication
- Never expose API secrets client-side

## Performance

- Minimal re-renders with React optimization
- CSS modules for scoped styling
- No heavy animation libraries
- Efficient table rendering

## Accessibility

- Keyboard navigation support
- Focus visible states
- Semantic HTML structure
- ARIA labels (enhance further as needed)

## Future Enhancements

- [ ] Live Kraken API integration
- [ ] WebSocket real-time data feeds
- [ ] Advanced charting (TradingView, etc.)
- [ ] Multi-account support
- [ ] Trade analytics dashboard
- [ ] Alert system
- [ ] Mobile responsive layout
- [ ] Dark/light theme toggle (optional)

## Contributing

Follow the strict design guidelines:
1. **No rounded corners** - All elements must have sharp edges
2. **Color discipline** - Only black, blue, white (+ green/red for prices)
3. **Monospace data** - Use `--font-mono` for numbers
4. **Grid alignment** - Respect spacing variables
5. **Keyboard support** - All actions keyboard accessible

## Contact

**Engineering Lead**: Samuel Balent (saba6682@colorado.edu)  
**Trading Lead**: Ryan Watts  
**Risk Management**: Magnus Miller

---

**CU Quants Trading Terminal** - Professional trading for quantitative strategies.