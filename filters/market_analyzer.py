import pandas as pd
import yfinance as yf
import numpy as np

def calculate_sma(data, window=20):
    """原生 Pandas 計算簡單移動平均線"""
    return data.rolling(window=window).mean()

def analyze_market_regime(ticker_list):
    """
    分析市場狀態的函數：回傳多頭、盤整或空頭
    """
    results = {}
    
    try:
        market_data = yf.download("^TWII", period="3mo", progress=False)
        if isinstance(market_data.columns, pd.MultiIndex):
            market_data = market_data.xs("^TWII", axis=1, level=1)
        
        close = market_data['Close']
        sma_20 = calculate_sma(close, 20)
        sma_60 = calculate_sma(close, 60) # 可加入長天期均線輔助判斷趨勢
        
        current_price = close.iloc[-1]
        current_sma20 = sma_20.iloc[-1]
        current_sma60 = sma_60.iloc[-1] if not pd.isna(sma_60.iloc[-1]) else current_sma20
        
        # 計算價格與 20 日均線的乖離率 (%)
        bias = (current_price - current_sma20) / current_sma20 * 100
        
        # 判斷型態：多頭、盤整、空頭
        # 邏輯範例：
        # 1. 乖離率介於 -1.5% ~ +1.5% 之間視為「盤整」
        # 2. 價格大於 20MA 且乖離大於 1.5% 為「多頭」
        # 3. 其餘或小於 20MA 且乖離小於 -1.5% 為「空頭」
        if abs(bias) <= 1.5:
            market_regime = "盤整 (Range-bound)"
        elif current_price > current_sma20 and bias > 1.5:
            market_regime = "多頭 (Bullish)"
        else:
            market_regime = "空頭 (Bearish)"
            
        results['regime'] = market_regime
        results['sma_20'] = current_sma20
        results['bias'] = bias
        
    except Exception as e:
        results['regime'] = "盤整 (Range-bound)"
        results['error'] = str(e)
        
    return results
