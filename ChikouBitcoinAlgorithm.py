# QuantConnect Chikou Bitcoin Breakout Strategy
# Author: spanston
# Date: September 2025

from AlgorithmImports import *
import numpy as np

class ChikouBitcoinBreakoutAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        """Initialize algorithm parameters and data subscriptions"""
        
        # Set algorithm start/end dates and cash
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2025, 9, 17)
        self.SetCash(100000)
        
        # Add Bitcoin data subscription
        self.symbol = self.AddCrypto("BTCUSD", Resolution.Minute).Symbol
        
        # Algorithm parameters
        self.chikou_period = 26  # Traditional Ichimoku Chikou period
        self.bb_period = 20      # Bollinger Band period for momentum
        self.bb_std_dev = 2.0    # Bollinger Band standard deviation multiplier
        self.position_size = 0.8 # Percentage of portfolio to risk per trade
        
        # Create 4-hour consolidator
        self.four_hour_consolidator = QuoteBarConsolidator(timedelta(hours=4))
        self.four_hour_consolidator.DataConsolidated += self.OnFourHourData
        self.SubscriptionManager.AddConsolidator(self.symbol, self.four_hour_consolidator)
        
        # Initialize indicators
        self.ichimoku = IchimokuKinkoHyo("ICHIMOKU", 9, 26, 26, 52, 26)
        self.bb = BollingerBands("BB", self.bb_period, self.bb_std_dev)
        
        # Price and momentum tracking
        self.price_history = RollingWindow[float](self.chikou_period + 1)
        self.chikou_momentum = RollingWindow[float](self.bb_period + 1)
        
        # Trading state variables
        self.last_signal_time = None
        self.min_signal_interval = timedelta(hours=12)  # Prevent over-trading
        
        # Warm up period
        self.SetWarmUp(max(self.chikou_period, 52) + self.bb_period)
        
    def OnFourHourData(self, sender, consolidated):
        """Process 4-hour consolidated data"""
        
        if self.IsWarmingUp:
            return
            
        # Update price history
        self.price_history.Add(float(consolidated.Close))
        
        # Calculate Chikou momentum (current price vs price 26 periods ago)
        if self.price_history.Count >= self.chikou_period + 1:
            current_price = self.price_history[0]
            historical_price = self.price_history[self.chikou_period]
            chikou_momentum = (current_price - historical_price) / historical_price * 100
            
            self.chikou_momentum.Add(chikou_momentum)
            
            # Update Bollinger Bands on momentum
            if self.chikou_momentum.Count > 0:
                self.bb.Update(consolidated.EndTime, chikou_momentum)
            
        # Update Ichimoku indicator
        self.ichimoku.Update(consolidated)
        
        # Generate trading signals
        self.CheckForSignals(consolidated)
        
    def CheckForSignals(self, data):
        """Check for Chikou breakout signals"""
        
        # Ensure we have enough data and haven't traded recently
        if (not self.bb.IsReady or 
            not self.ichimoku.IsReady or
            self.chikou_momentum.Count < 2 or
            (self.last_signal_time and 
             data.EndTime - self.last_signal_time < self.min_signal_interval)):
            return
            
        current_price = float(data.Close)
        current_momentum = self.chikou_momentum[0]
        previous_momentum = self.chikou_momentum[1]
        
        # Ichimoku cloud levels
        senkou_a = float(self.ichimoku.SenkouA.Current.Value)
        senkou_b = float(self.ichimoku.SenkouB.Current.Value)
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        
        # Bollinger Band levels for momentum
        upper_band = float(self.bb.UpperBand.Current.Value)
        lower_band = float(self.bb.LowerBand.Current.Value)
        
        # Current position
        holdings = self.Portfolio[self.symbol].Quantity
        
        # Bullish breakout signal
        if (previous_momentum <= upper_band and current_momentum > upper_band and
            current_price > cloud_top and holdings <= 0):
            
            self.LiquidateAll()
            quantity = self.CalculateOrderQuantity(self.symbol, self.position_size)
            self.MarketOrder(self.symbol, quantity)
            self.last_signal_time = data.EndTime
            
            self.Log(f"BULLISH BREAKOUT: Price {current_price:.2f}, Momentum {current_momentum:.2f}, Upper Band {upper_band:.2f}")
            
        # Bearish breakout signal
        elif (previous_momentum >= lower_band and current_momentum < lower_band and
              current_price < cloud_bottom and holdings >= 0):
            
            self.LiquidateAll()
            quantity = self.CalculateOrderQuantity(self.symbol, -self.position_size)
            self.MarketOrder(self.symbol, quantity)
            self.last_signal_time = data.EndTime
            
            self.Log(f"BEARISH BREAKOUT: Price {current_price:.2f}, Momentum {current_momentum:.2f}, Lower Band {lower_band:.2f}")
            
        # Exit conditions
        elif holdings != 0:
            self.CheckExitConditions(data, current_price, cloud_top, cloud_bottom)
            
    def CheckExitConditions(self, data, current_price, cloud_top, cloud_bottom):
        """Check for position exit conditions"""
        
        holdings = self.Portfolio[self.symbol].Quantity
        
        # Exit long position if price falls back into cloud
        if holdings > 0 and current_price < cloud_top:
            self.LiquidateAll()
            self.Log(f"EXIT LONG: Price {current_price:.2f} fell below cloud top {cloud_top:.2f}")
            
        # Exit short position if price rises back into cloud  
        elif holdings < 0 and current_price > cloud_bottom:
            self.LiquidateAll()
            self.Log(f"EXIT SHORT: Price {current_price:.2f} rose above cloud bottom {cloud_bottom:.2f}")
            
    def OnData(self, data):
        """Main data handler - processes minute data"""
        
        # Primary logic handled in OnFourHourData
        # This method can be used for additional monitoring or fine-tuning
        pass
        
    def OnOrderEvent(self, orderEvent):
        """Handle order events"""
        
        if orderEvent.Status == OrderStatus.Filled:
            self.Log(f"Order filled: {orderEvent.Symbol} - {orderEvent.FillQuantity} @ {orderEvent.FillPrice}")
            
    def OnEndOfAlgorithm(self):
        """Called at the end of algorithm execution"""
        
        self.Log(f"Algorithm completed. Final portfolio value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        
        # Performance summary
        if self.Portfolio.TotalPortfolioValue > self.StartingPortfolioValue:
            returns = (self.Portfolio.TotalPortfolioValue - self.StartingPortfolioValue) / self.StartingPortfolioValue * 100
            self.Log(f"Total return: {returns:.2f}%")
        else:
            loss = (self.StartingPortfolioValue - self.Portfolio.TotalPortfolioValue) / self.StartingPortfolioValue * 100
            self.Log(f"Total loss: -{loss:.2f}%")
