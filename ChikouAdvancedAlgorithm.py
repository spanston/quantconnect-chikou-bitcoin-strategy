# Advanced QuantConnect Chikou Bitcoin Strategy
# Inspired by Pine Script implementation with state management and retest signals
# Author: spanston
# Date: September 2025

from AlgorithmImports import *
import numpy as np
from enum import Enum

class SignalState(Enum):
    NEUTRAL = 0
    BULLISH = 1
    BEARISH = -1

class ChikouAdvancedAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        """Initialize advanced Chikou algorithm with state management"""
        
        # Set algorithm parameters
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2025, 9, 17)
        self.SetCash(100000)
        
        # Add Bitcoin data
        self.symbol = self.AddCrypto("BTCUSD", Resolution.Minute).Symbol
        
        # Core Ichimoku parameters
        self.tenkan_period = 9
        self.kijun_period = 26
        self.senkou_b_period = 52
        self.displacement = 26
        
        # Advanced signal parameters
        self.use_bodies = False  # Use wicks vs bodies for Chikou reference
        self.confirm_on_close = True  # Wait for bar close confirmation
        self.show_retest_signals = True  # Enable retest functionality
        self.retest_min_delay_bars = 2  # Minimum bars before retest
        self.neutral_reset_bars = 60  # Bars to reset to neutral
        
        # Volume and scoring parameters
        self.use_volume = True
        self.volume_sensitivity = 0.35
        self.volume_lookback = 20
        self.volume_cap = 3.0
        
        # Position and risk management
        self.position_size = 0.8
        self.min_signal_interval = timedelta(hours=12)
        
        # Create 4-hour consolidator
        self.four_hour_consolidator = QuoteBarConsolidator(timedelta(hours=4))
        self.four_hour_consolidator.DataConsolidated += self.OnFourHourData
        self.SubscriptionManager.AddConsolidator(self.symbol, self.four_hour_consolidator)
        
        # Initialize indicators
        self.ichimoku = IchimokuKinkoHyo("ICHIMOKU", 
                                        self.tenkan_period, 
                                        self.kijun_period, 
                                        self.kijun_period, 
                                        self.senkou_b_period, 
                                        self.displacement)
        
        # Volume indicator for weighting
        self.volume_sma = SimpleMovingAverage("VOL_SMA", self.volume_lookback)
        
        # Price and reference tracking
        self.price_history = RollingWindow[QuoteBar](self.displacement + 10)
        
        # Advanced state management
        self.active_direction = SignalState.NEUTRAL
        self.last_breakout_bar = None
        self.last_breakout_direction = SignalState.NEUTRAL
        self.last_retest_bar = None
        self.last_signal_time = None
        self.trend_score = 0.0
        
        # Bar tracking for state management
        self.bar_index = 0
        
        # Warm up period
        self.SetWarmUp(max(self.displacement, self.senkou_b_period) + 10)
        
        # Performance tracking
        self.breakout_signals = 0
        self.retest_signals = 0
        
    def OnFourHourData(self, sender, consolidated):
        """Process 4-hour consolidated data with advanced signal logic"""
        
        if self.IsWarmingUp:
            return
            
        self.bar_index += 1
        
        # Update price history
        self.price_history.Add(consolidated)
        
        # Update indicators
        self.ichimoku.Update(consolidated)
        if consolidated.Volume is not None:
            self.volume_sma.Update(consolidated.EndTime, float(consolidated.Volume))
        
        # Process signals only if we have enough data
        if (not self.ichimoku.IsReady or 
            self.price_history.Count < self.displacement + 1):
            return
            
        # Get reference levels from displacement periods ago
        ref_bar = self.price_history[self.displacement]
        
        if self.use_bodies:
            ref_high = max(float(ref_bar.Open), float(ref_bar.Close))
            ref_low = min(float(ref_bar.Open), float(ref_bar.Close))
        else:
            ref_high = float(ref_bar.High)
            ref_low = float(ref_bar.Low)
            
        current_price = float(consolidated.Close)
        
        # Calculate trend score
        self.trend_score = self.CalculateTrendScore(consolidated)
        
        # Check for primary breakout signals
        self.CheckBreakoutSignals(consolidated, current_price, ref_high, ref_low)
        
        # Check for retest signals
        if self.show_retest_signals:
            self.CheckRetestSignals(consolidated, current_price, ref_high, ref_low)
            
        # Check for neutral reset
        self.CheckNeutralReset()
        
        # Update last signal time tracking
        if (self.last_signal_time and 
            consolidated.EndTime - self.last_signal_time >= self.min_signal_interval):
            pass  # Signal cooldown expired
            
    def CalculateTrendScore(self, data):
        """Calculate comprehensive trend score based on multiple factors"""
        
        # Ichimoku component values
        tenkan = float(self.ichimoku.Tenkan.Current.Value)
        kijun = float(self.ichimoku.Kijun.Current.Value)
        senkou_a = float(self.ichimoku.SenkouA.Current.Value)
        senkou_b = float(self.ichimoku.SenkouB.Current.Value)
        chikou = float(data.Close)
        
        # Get Chikou reference levels
        if self.price_history.Count >= self.displacement:
            kijun_at_chikou = float(self.price_history[self.displacement].Close)  # Simplified
            cloud_top_at_chikou = max(senkou_a, senkou_b)
            cloud_bottom_at_chikou = min(senkou_a, senkou_b)
        else:
            return 0.0
            
        # Scoring weights
        W_BIAS = 35
        W_TK = 25
        W_CH_KIJUN = 20
        W_CH_CLOUD = 20
        
        # Base bias score from active direction
        score_bias = int(self.active_direction.value) * W_BIAS
        
        # Tenkan-Kijun relationship
        score_tk = W_TK if tenkan > kijun else -W_TK if tenkan < kijun else 0
        
        # Chikou vs Kijun
        score_ch_kijun = W_CH_KIJUN if chikou > kijun_at_chikou else -W_CH_KIJUN if chikou < kijun_at_chikou else 0
        
        # Chikou vs Cloud
        score_ch_cloud = 0
        if chikou > cloud_top_at_chikou:
            score_ch_cloud = W_CH_CLOUD
        elif chikou < cloud_bottom_at_chikou:
            score_ch_cloud = -W_CH_CLOUD
            
        # Volume multiplier
        volume_mult = 1.0
        if self.use_volume and self.volume_sma.IsReady:
            current_vol = float(data.Volume) if data.Volume else 0.0
            avg_vol = float(self.volume_sma.Current.Value)
            if avg_vol > 0:
                rel_vol = min(current_vol / avg_vol, self.volume_cap)
                volume_mult = 1.0 + (rel_vol - 1.0) * self.volume_sensitivity
                
        # Calculate directional score with volume weighting
        directional_score = (score_tk + score_ch_kijun + score_ch_cloud) * volume_mult
        
        # Final score
        final_score = score_bias + directional_score
        
        # Normalize to reasonable range
        max_possible = W_BIAS + (W_TK + W_CH_KIJUN + W_CH_CLOUD) * (1.0 + (self.volume_cap - 1.0) * self.volume_sensitivity)
        
        return max(-max_possible, min(max_possible, final_score))
        
    def CheckBreakoutSignals(self, data, current_price, ref_high, ref_low):
        """Check for primary Chikou breakout signals"""
        
        # Skip if we have recent signals
        if (self.last_signal_time and 
            data.EndTime - self.last_signal_time < self.min_signal_interval):
            return
            
        # Bullish breakout: price crosses above reference high
        if (current_price > ref_high and 
            self.active_direction != SignalState.BULLISH):
            
            if not self.confirm_on_close or data.EndTime.minute == 0:  # Simplified close confirmation
                self.ProcessBreakoutSignal(SignalState.BULLISH, data, current_price, ref_high)
                
        # Bearish breakout: price crosses below reference low
        elif (current_price < ref_low and 
              self.active_direction != SignalState.BEARISH):
            
            if not self.confirm_on_close or data.EndTime.minute == 0:
                self.ProcessBreakoutSignal(SignalState.BEARISH, data, current_price, ref_low)
                
    def ProcessBreakoutSignal(self, direction, data, price, ref_level):
        """Process confirmed breakout signal"""
        
        # Update state
        self.active_direction = direction
        self.last_breakout_direction = direction
        self.last_breakout_bar = self.bar_index
        self.last_signal_time = data.EndTime
        self.breakout_signals += 1
        
        # Determine position based on trend score
        signal_strength = "STRONG" if abs(self.trend_score) > 50 else "WEAK"
        
        # Execute trade
        if direction == SignalState.BULLISH:
            self.LiquidateAll()
            quantity = self.CalculateOrderQuantity(self.symbol, self.position_size)
            self.MarketOrder(self.symbol, quantity)
            
            self.Log(f"BULLISH BREAKOUT ({signal_strength}): Price {price:.2f} > Ref {ref_level:.2f}, Score: {self.trend_score:.1f}")
            
        elif direction == SignalState.BEARISH:
            self.LiquidateAll()
            quantity = self.CalculateOrderQuantity(self.symbol, -self.position_size)
            self.MarketOrder(self.symbol, quantity)
            
            self.Log(f"BEARISH BREAKOUT ({signal_strength}): Price {price:.2f} < Ref {ref_level:.2f}, Score: {self.trend_score:.1f}")
            
    def CheckRetestSignals(self, data, current_price, ref_high, ref_low):
        """Check for retest signals after breakouts"""
        
        if (self.last_breakout_bar is None or 
            self.last_breakout_direction == SignalState.NEUTRAL):
            return
            
        bars_since_breakout = self.bar_index - self.last_breakout_bar
        
        # Check if we're in the retest window
        if (bars_since_breakout < self.retest_min_delay_bars or 
            bars_since_breakout > 60):  # 60 bar retest window
            return
            
        # Check if we already had a retest for this breakout
        if (self.last_retest_bar is not None and 
            self.last_retest_bar >= self.last_breakout_bar):
            return
            
        epsilon = self.Securities[self.symbol].SymbolProperties.MinimumPriceVariation
        
        # Bullish retest: price retests breakout level from above
        if (self.last_breakout_direction == SignalState.BULLISH and
            data.Low <= ref_high + epsilon and
            current_price >= ref_high):
            
            self.ProcessRetestSignal(SignalState.BULLISH, data, "retest of bullish breakout")
            
        # Bearish retest: price retests breakout level from below  
        elif (self.last_breakout_direction == SignalState.BEARISH and
              data.High >= ref_low - epsilon and
              current_price <= ref_low):
            
            self.ProcessRetestSignal(SignalState.BEARISH, data, "retest of bearish breakout")
            
    def ProcessRetestSignal(self, direction, data, description):
        """Process confirmed retest signal"""
        
        self.last_retest_bar = self.bar_index
        self.retest_signals += 1
        
        # Retests can add to existing positions or confirm trend continuation
        current_position = self.Portfolio[self.symbol].Quantity
        
        if direction == SignalState.BULLISH and current_position > 0:
            # Could add to position or just log confirmation
            self.Log(f"BULLISH RETEST CONFIRMED: {description}, maintaining long position")
            
        elif direction == SignalState.BEARISH and current_position < 0:
            self.Log(f"BEARISH RETEST CONFIRMED: {description}, maintaining short position")
            
        else:
            # Retest suggests trend continuation, enter if not positioned
            if direction == SignalState.BULLISH:
                quantity = self.CalculateOrderQuantity(self.symbol, self.position_size * 0.5)  # Smaller retest position
                self.MarketOrder(self.symbol, quantity)
                self.Log(f"BULLISH RETEST ENTRY: {description}")
                
            elif direction == SignalState.BEARISH:
                quantity = self.CalculateOrderQuantity(self.symbol, -self.position_size * 0.5)
                self.MarketOrder(self.symbol, quantity)
                self.Log(f"BEARISH RETEST ENTRY: {description}")
                
    def CheckNeutralReset(self):
        """Reset to neutral state after extended periods without confirmation"""
        
        if (self.active_direction != SignalState.NEUTRAL and 
            self.last_breakout_bar is not None):
            
            bars_since_breakout = self.bar_index - self.last_breakout_bar
            
            if bars_since_breakout > self.neutral_reset_bars:
                old_direction = self.active_direction
                self.active_direction = SignalState.NEUTRAL
                self.Log(f"NEUTRAL RESET: {old_direction.name} -> NEUTRAL after {bars_since_breakout} bars")
                
    def OnData(self, data):
        """Main data handler - primary logic in OnFourHourData"""
        pass
        
    def OnOrderEvent(self, orderEvent):
        """Handle order events with enhanced logging"""
        
        if orderEvent.Status == OrderStatus.Filled:
            direction = "LONG" if orderEvent.FillQuantity > 0 else "SHORT"
            self.Log(f"ORDER FILLED: {direction} {abs(orderEvent.FillQuantity)} {orderEvent.Symbol} @ {orderEvent.FillPrice}")
            
    def OnEndOfAlgorithm(self):
        """Algorithm completion summary with signal statistics"""
        
        self.Log(f"\n=== ALGORITHM SUMMARY ===")
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        
        if self.Portfolio.TotalPortfolioValue > self.StartingPortfolioValue:
            returns = (self.Portfolio.TotalPortfolioValue - self.StartingPortfolioValue) / self.StartingPortfolioValue * 100
            self.Log(f"Total Return: {returns:.2f}%")
        else:
            loss = (self.StartingPortfolioValue - self.Portfolio.TotalPortfolioValue) / self.StartingPortfolioValue * 100
            self.Log(f"Total Loss: -{loss:.2f}%")
            
        self.Log(f"Breakout Signals Generated: {self.breakout_signals}")
        self.Log(f"Retest Signals Generated: {self.retest_signals}")
        self.Log(f"Final Active Direction: {self.active_direction.name}")
        self.Log(f"Final Trend Score: {self.trend_score:.1f}")
