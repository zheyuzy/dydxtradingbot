# -*- coding: utf-8 -*-
"""dydxtradingbot
"""

from dydx3 import Client
from dydx3.constants import *
import time
from decimal import Decimal
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple

class dydxTradingBot:
    """
    Automated trading bot for dYdX exchange
    Implements hourly trading strategy based on price movements
    """
    def __init__(self, ethereum_address: str, api_credentials: Dict, stark_private_key: str):
        # Current top 10 trading pairs by market cap on dydx
        self.trading_pairs = [
            "BTC-USD",   # Bitcoin
            "ETH-USD",   # Ethereum
            "XRP-USD",   # XRP
            "BNB-USD",   # BNB
            "SOL-USD",   # Solana
            "DOGE-USD",  # Dogecoin
            "ADA-USD",   # Cardano
            "TRX-USD",   # TRON
            "LINK-USD",  # Chainlink
            "SUI-USD"    # Sui
        ]

        # Entry thresholds for price drops (in percentage)
        # Adjusted based on current market volatility
        self.entry_thresholds = {
            "BTC-USD": -1.0,    # Lower volatility
            "ETH-USD": -1.2,    # Lower volatility
            "XRP-USD": -1.8,    # Medium volatility
            "BNB-USD": -1.5,    # Medium volatility
            "SOL-USD": -2.0,    # Higher volatility
            "DOGE-USD": -2.2,   # Higher volatility
            "ADA-USD": -1.9,    # Medium volatility
            "TRX-USD": -1.8,    # Medium volatility
            "LINK-USD": -1.7,   # Medium volatility
            "SUI-USD": -2.1     # Higher volatility
        }

        # Decimal precision for each trading pair
        self.decimal_places = {
            "BTC-USD": 4,
            "ETH-USD": 3,
            "XRP-USD": 4,
            "BNB-USD": 2,
            "SOL-USD": 2,
            "DOGE-USD": 5,
            "ADA-USD": 4,
            "TRX-USD": 5,
            "LINK-USD": 3,
            "SUI-USD": 4
        }

        # Initialize dYdX client
        self.client = Client(
            network_id=NETWORK_ID_MAINNET,
            host=API_HOST_MAINNET,
            default_ethereum_address=ethereum_address,
            api_key_credentials=api_credentials,
            stark_private_key=stark_private_key
        )

        # Get account information
        self.position_id = self.client.private.get_account().data['account']['positionId']
        self.markets_data = self._initialize_markets_data()

    def _initialize_markets_data(self) -> Dict:
        """Initialize market data for all trading pairs"""
        return {pair: self.client.public.get_markets(pair).data['markets'][pair]
                for pair in self.trading_pairs}

    def get_best_orderbook_prices(self, trading_pair: str) -> Tuple[str, str]:
        """Get best ask and bid prices from the orderbook"""
        orderbook = self.client.public.get_orderbook(trading_pair).data
        best_ask = min(float(ask['price']) for ask in orderbook['asks'])
        best_bid = max(float(bid['price']) for bid in orderbook['bids'])
        return str(best_ask), str(best_bid)

    def get_market_price(self, trading_pair: str) -> float:
        """Get current market price for a trading pair"""
        market_data = self.client.public.get_markets().data['markets']
        return float(market_data[trading_pair]['indexPrice'])

    def calculate_position_size(self, trading_pair: str, allocation_amount: float) -> float:
        """Calculate position size based on allocation amount"""
        price = self.get_market_price(trading_pair)
        decimals = self.decimal_places[trading_pair]

        if decimals == 0:
            return int(round(allocation_amount / price))
        return round(allocation_amount / price, decimals)

    def create_market_order(self, side: str, trading_pair: str, size: str,
                          time_in_force: str = "FOK") -> Dict:
        """Create a market order"""
        market_data = self.markets_data[trading_pair]
        best_ask, best_bid = self.get_best_orderbook_prices(trading_pair)

        # Calculate order price with buffer
        if side == ORDER_SIDE_BUY:
            price = Decimal(best_ask) + Decimal(market_data['tickSize']) * Decimal('20')
        else:
            price = Decimal(best_bid) - Decimal(market_data['tickSize']) * Decimal('20')

        price = Decimal(price).quantize(Decimal(market_data['tickSize']))

        order_params = {
            'position_id': self.position_id,
            'market': trading_pair,
            'side': side,
            'order_type': ORDER_TYPE_MARKET,
            'post_only': False,
            'size': str(size),
            'price': str(price),
            'limit_fee': '0.1',
            'time_in_force': time_in_force,
            'expiration_epoch_seconds': time.time() + 120
        }

        return self.client.private.create_order(**order_params)

    def close_position(self, trading_pair: str, position_data: Dict):
        """Close an open position"""
        size = abs(float(position_data['size']))
        side = ORDER_SIDE_SELL if position_data['side'] == 'LONG' else ORDER_SIDE_BUY
        self.create_market_order(side, trading_pair, str(size))

    def run_trading_strategy(self):
        """Execute the main trading strategy"""
        current_hour = datetime.now().hour

        while True:
            print(f"Waiting for hour {(current_hour + 1) % 24}\n")

            # Wait for next hour
            while datetime.now().hour == current_hour:
                time.sleep(30)

            current_hour = datetime.now().hour
            self._execute_hourly_trades()

    def _execute_hourly_trades(self):
        """Execute trades for the current hour"""
        # Close existing positions
        self._close_all_positions()

        print("\nAnalyzing market conditions in 45 seconds\n")
        time.sleep(45)

        # Open new positions
        self._open_new_positions()

        # Update trade history
        self._update_trade_history()

    def _close_all_positions(self):
        """Close all open positions"""
        print("Closing all open positions")
        account_positions = self.client.private.get_account().data['account']['openPositions']

        if account_positions:
            for trading_pair, position_data in account_positions.items():
                self.close_position(trading_pair, position_data)
                print(f"Closed position for {trading_pair}")
        else:
            print("No open positions")

    def _open_new_positions(self):
        """Open new positions based on strategy criteria"""
        balance = float(self.client.private.get_account().data['account']['quoteBalance'])
        print("Analyzing opportunities for new positions:\n")

        qualifying_pairs = []
        for pair in self.trading_pairs:
            candle_data = self.client.public.get_candles(
                pair,
                resolution="1HOUR"
            ).data['candles'][1]

            price_change = ((float(candle_data['close']) - float(candle_data['open']))
                          / float(candle_data['open']) * 100)

            print(f"{pair}: {price_change:.2f}%")
            if price_change <= self.entry_thresholds[pair]:
                qualifying_pairs.append(pair)

        # Open positions for qualifying pairs
        if qualifying_pairs:
            allocation_per_pair = balance / (len(qualifying_pairs) * 1.0125)
            for pair in qualifying_pairs:
                size = self.calculate_position_size(pair, allocation_per_pair)
                self.create_market_order(ORDER_SIDE_BUY, pair, str(size), "IOC")
                print(f"\nOpened long position for {pair}")

        print(f"\nTotal new positions opened: {len(qualifying_pairs)}\n")

    def _update_trade_history(self):
        """Update trade history file"""
        print("Updating trade history\n")
        with open("trade_history.txt", "a") as file:
            account_positions = self.client.private.get_account().data['account']['openPositions']

            for pair in account_positions.keys():
                last_position = self.client.private.get_positions(
                    market=pair,
                    status=POSITION_STATUS_CLOSED
                ).data['positions'][-1]

                file.write(
                    f"Trade executed with {pair} from {datetime.now().hour-1}h "
                    f"to {datetime.now().hour}h\n"
                    f"Realized PNL: {last_position['realizedPnl']}\n"
                )

            if account_positions:
                balance = self.client.private.get_account().data['account']['quoteBalance']
                file.write(f"Current Balance: ${balance}\n")

