# UI:

# Bloomberg-Style Trading Terminal UI  
**Color Scheme: Black, Blue, White**

## Role
You are a world class senior frontend engineer and professional UI designer building an institutional-grade, Bloomberg-style trading terminal. Generate all required files inside /frontend and leave clear and consise comments when needed.

The product is a **React-based web trading terminal** designed for quantitative trading and market monitoring. The interface must prioritize clarity, speed, and dense information display.

---

## Core Design Principles
- Dark, professional theme
- High information density
- No consumer-style cards or rounded layouts
- No gradients, glassmorphism, or shadows
- Sharp edges and grid-aligned components
- Keyboard-friendly and power-user oriented
- Visual hierarchy driven by typography and spacing, not decoration

---

## Color Scheme (Strict)
Use **only** the following colors:

- **Black** for primary background
- **Deep Blue** for accents, highlights, and active states
- **White** for primary text and key values

### Usage Rules
- Black background dominates the UI
- Blue is used sparingly for:
  - Active tabs
  - Selected rows
  - Focus states
  - Section dividers
- White is used for:
  - Text
  - Prices
  - Labels
- Green and red may be used **only** for price movement indicators
- No additional colors allowed

---

## Global Layout
- Full-screen application
- Fixed layout with internal scrolling panels
- Grid-based structure with adjustable panel widths
- No page reloads

---

## Top Market Ticker (Always Visible)
- Horizontal ticker bar fixed to the top of the screen
- Displays **14 instruments simultaneously**
- Each ticker item includes:
  - Symbol
  - Last price
  - Net change
  - Percent change
- Styling:
  - Black background
  - White text
  - Blue separators between instruments
  - Green/red only for price change indicators
- Smooth horizontal auto-scroll with pause-on-hover

---

## Left Navigation Bar
- Vertical sidebar anchored to the left
- Black background with blue active indicator
- Minimal text labels
- Navigation items:
  - Home
  - Trading
  - Settings
- Active page highlighted with blue accent bar
- Collapsible for compact mode

---

## Home Page
- Market overview layout
- Sections:
  - Market summary table
  - Volatility snapshot
  - Recent signals or alerts
- Dense tabular layout
- No charts unless essential

---

## Trading Page
- Primary workspace
- Layout sections:
  - Order entry panel
  - Open positions table
  - Live order book
  - Trade history
- Tables use:
  - White text
  - Blue header separators
  - Alternating row emphasis via opacity only
- Order inputs are compact, inline, and keyboard accessible

---

## Settings Page
- Simple form layout
- API Key configuration section
- Masked input for API keys
- Clear save and validation states
- No animations

---

## Typography
- Monospace or condensed sans-serif
- Numeric values aligned vertically
- No decorative fonts
- Emphasis via weight, not color

---

## Interaction Rules
- Hover states use subtle blue outlines
- Focus states clearly visible for keyboard navigation
- No unnecessary animations
- Fast UI response over visual flair

---

## Output Expectations
Generate:
- React component structure
- Layout hierarchy
- Styling strategy (CSS modules, Tailwind, or styled-components)
- Reusable components for:
  - Ticker items
  - Data tables
  - Sidebar navigation
  - Order entry forms

The result should resemble a professional trading terminal used by quantitative desks, not a retail trading app.
