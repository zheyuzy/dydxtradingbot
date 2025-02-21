# dydxtradingbot
This is an automated trading bot designed for the dYdX exchange, executing a simple trading strategy based on market price movements. It identifies trading opportunities using predefined price drop thresholds and dynamically allocates capital to maximize potential gains.

Features
- Supports Top 10 Trading Pairs: BTC-USD, ETH-USD, XRP-USD, BNB-USD, SOL-USD, DOGE-USD, ADA-USD, TRX-USD, LINK-USD, SUI-USD.
- Trading Strategy: Executes trades based on price fluctuations detected in hourly candlesticks.
- Automated Order Execution: Places market orders with optimal precision.
- Risk Management: Closes all open positions before opening new ones to manage exposure.
- Trade Logging: Records trading activity and balance updates in a local file (trade_history.txt).
