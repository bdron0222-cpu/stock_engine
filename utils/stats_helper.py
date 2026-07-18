import pandas as pd
import numpy as np
from scipy import stats

def calculate_beta_and_rho(stock_data, market_data):
    """
    計算 Beta 與相關係數 (Rho)
    :param stock_data: 股票收盤價 Series
    :param market_data: 大盤收盤價 Series
    """
    # 對齊數據
    combined = pd.concat([stock_data, market_data], axis=1).dropna()
    combined.columns = ['Stock', 'Market']
    
    # 計算日報酬
    stock_ret = combined['Stock'].pct_change().dropna()
    market_ret = combined['Market'].pct_change().dropna()
    
    # Rho (相關係數)
    rho = stock_ret.corr(market_ret)
    
    # Beta (使用線性迴歸計算)
    slope, _, _, _, _ = stats.linregress(market_ret, stock_ret)
    beta = slope
    
    return beta, rho