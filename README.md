# QuantConnect Chikou Bitcoin Breakout Strategy

[![GitHub](https://img.shields.io/github/license/spanston/quantconnect-chikou-bitcoin-strategy)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![QuantConnect](https://img.shields.io/badge/platform-QuantConnect-green)](https://www.quantconnect.com/)

A sophisticated algorithmic trading strategy that combines the Ichimoku Chikou span with Bollinger Bands to identify and trade Bitcoin breakouts on a 4-hour timeframe.

## 📈 Strategy Overview

This algorithm implements a momentum-based breakout strategy using the Chikou span (lagging line) from the Ichimoku Kinko Hyo system. The Chikou span provides powerful momentum confirmation by comparing current price to price 26 periods ago.

### Key Features

- **Chikou Momentum Analysis**: Quantifies the traditional Chikou span into measurable momentum values
- **Bollinger Band Filtering**: Uses statistical bands around momentum to identify significant breakouts
- **Ichimoku Cloud Confirmation**: Leverages cloud boundaries for trend direction and stop-loss levels
- **4-Hour Timeframe**: Optimal balance between signal quality and trading frequency for Bitcoin
- **Dynamic Risk Management**: Cloud-based stop losses and position sizing

## 🔧 Algorithm Components

### Core Indicators

1. **Ichimoku Kinko Hyo**
   - Tenkan-sen (9-period)
   - Kijun-sen (26-period) 
   - Senkou Span A & B (cloud boundaries)
   - Chikou Span (26-period lagging line)

2. **Bollinger Bands on Chikou Momentum**
   - 20-period moving average
   - 2.0 standard deviation bands
   - Applied to momentum calculation rather than price

3. **Custom Momentum Calculation**
   ```python
   chikou_momentum = (current_price - price_26_periods_ago) / price_26_periods_ago * 100
   ```

### Trading Signals

#### Bullish Breakout
- Chikou momentum crosses above upper Bollinger Band
- Current price is above Ichimoku cloud
- No recent signals (12-hour cooldown)

#### Bearish Breakout
- Chikou momentum crosses below lower Bollinger Band
- Current price is below Ichimoku cloud
- No recent signals (12-hour cooldown)

#### Exit Conditions
- Long positions: Price falls back into cloud
- Short positions: Price rises back into cloud

## 🚀 Getting Started

### Prerequisites

- QuantConnect account (free tier available)
- Basic understanding of Python and algorithmic trading
- Familiarity with Ichimoku analysis (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/spanston/quantconnect-chikou-bitcoin-strategy.git
   cd quantconnect-chikou-bitcoin-strategy
   ```

2. **Upload to QuantConnect**
   - Log into your QuantConnect account
   - Create a new algorithm project
   - Copy the contents of `ChikouBitcoinAlgorithm.py` into your algorithm

3. **Run Backtest**
   - Set your desired date range (default: 2020-2025)
   - Click "Backtest" to run the algorithm

### Configuration

Key parameters can be adjusted in the `Initialize()` method:

```python
self.chikou_period = 26      # Chikou span lookback period
self.bb_period = 20          # Bollinger Band period
self.bb_std_dev = 2.0        # Standard deviation multiplier
self.position_size = 0.8     # Percentage of portfolio per trade
self.min_signal_interval = timedelta(hours=12)  # Minimum time between signals
```

## 📊 Performance Characteristics

### Expected Metrics

- **Timeframe**: 4-hour Bitcoin candles
- **Average Trades**: 20-40 per year
- **Hold Time**: 1-7 days typical
- **Market Conditions**: Performs best in trending markets

### Risk Management

- **Stop Losses**: Dynamic cloud-based exits
- **Position Sizing**: Configurable percentage of portfolio
- **Overtrading Protection**: Minimum interval between signals
- **Drawdown Control**: Cloud boundaries provide natural support/resistance

## ⚠️ Disclaimer

**This algorithm is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss and may not be suitable for all investors. Past performance does not guarantee future results. Please conduct your own research and consider your risk tolerance before trading.**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:

- Performance improvements
- Additional features
- Bug fixes
- Documentation enhancements
- Parameter optimization studies

## 📄 License

This project is licensed under the MIT License.

---

**⭐ If you find this strategy useful, please star the repository!**
