[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python package](https://github.com/canl/algo-trading/workflows/Python%20package/badge.svg?branch=master)
# algo-trading
**algo-trading** is a research project for Financial Analysis, Strategies Backtesting and Algorithmic Trading for Forex, Equities and Futures. 

## Preview

[![Performance Preview](https://canlu.pythonanywhere.com/img/london_breakout_gbpusd.png)](https://canlu.pythonanywhere.com/)

**[View Live Performance](https://canlu.pythonanywhere.com/)**

**algo-trading** reads forex market data feeds from Oanda: https://developer.oanda.com/rest-live-v20/introduction/. 

Python implementations of popular Algorithmic Trading Strategies, along with genetic algorithms for tuning parameters based on historical data.

## Dependencies
Python 3.x, pandas, matplotlib, pyyaml, numpy, scipy, oandapyV20, flask ...

See requirements.txt for full details.

Make sure you get the python3 versions of the relevant packages, i.e. use:

```shell script
sudo pip3 install ....
```

## Installation
This package isn't hosted on pip. So to get the code the easiest way is to use git:

```shell script
git clone https://github.com/canl/algo-trading.git
pip install -r requirements
```
