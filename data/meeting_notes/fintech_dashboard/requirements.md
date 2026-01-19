# FinTech Investment Dashboard

## Business Context
Build a real-time investment portfolio dashboard for a robo-advisor startup. Users need to visualize their portfolio performance, track market trends, and receive AI-powered investment recommendations.

## Target Users
- Retail investors (18-45 age group)
- First-time investors needing guidance
- Experienced traders wanting automation
- Financial advisors managing client portfolios

## Dashboard Features

### Portfolio Overview
- Total portfolio value with daily change
- Asset allocation pie chart (stocks, bonds, crypto, cash)
- Performance graph (1D, 1W, 1M, 1Y, ALL)
- Benchmark comparison (S&P 500, custom benchmarks)
- Risk score indicator

### Holdings View
- List of all positions with current value
- Gain/loss per position ($ and %)
- Cost basis and purchase history
- Dividend tracking and yield
- Sector exposure breakdown

### Market Data
- Real-time stock quotes (15-min delay for free tier)
- Major indices (DOW, S&P, NASDAQ)
- Trending stocks and news
- Economic calendar (earnings, Fed meetings)
- Cryptocurrency prices

### AI Recommendations
- Rebalancing suggestions based on risk profile
- Tax-loss harvesting opportunities
- Dividend reinvestment options
- New investment ideas based on goals
- Risk alerts and portfolio warnings

### Transaction History
- Buy/sell order history
- Dividend payments
- Deposits/withdrawals
- Tax documents (1099s)

## Real-Time Requirements
- WebSocket for live price updates
- Push notifications for price alerts
- Order execution status updates
- Market open/close notifications

## Data Sources
- Market data: Polygon.io API
- Company fundamentals: Alpha Vantage
- News: Finnhub
- Crypto: CoinGecko

## Tech Considerations
- Frontend: React + D3.js for charts + TanStack Query
- Backend: Go for high-performance APIs
- Database: TimescaleDB for time-series data
- Real-time: Redis Pub/Sub + WebSockets
- ML: Python microservice for recommendations
