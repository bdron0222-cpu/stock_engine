import pandas as pd
import yfinance as yf
import numpy as np

def calculate_sma(data, window=20):
    """原生 Pandas 計算簡單移動平均線"""
    return data.rolling(window=window).mean()

def analyze_market_regime(ticker_list):
    """
    分析市場狀態的函數
    不再依賴 pandas_ta，改用原生 Pandas 邏輯
    """
    results = {}
    
    # 簡單範例：以大盤指數 (^TWII) 作為市場狀態判斷基準
    # 如果你原本是用個股來判斷，請將此處邏輯調整為對應的輸入
    try:
        market_data = yf.download("^TWII", period="3mo", progress=False)
        if isinstance(market_data.columns, pd.MultiIndex):
            market_data = market_data.xs("^TWII", axis=1, level=1)
        
        close = market_data['Close']
        sma_20 = calculate_sma(close, 20)
        
        # 簡單的市場狀態判斷邏輯 (你可以根據需要調整)
        current_price = close.iloc[-1]
        current_sma = sma_20.iloc[-1]
        
        if current_price > current_sma:
            market_regime = "Bullish (多頭)"
        else:
            market_regime = "Bearish (空頭)"
            
        results['regime'] = market_regime
        results['sma_20'] = current_sma
        
    except Exception as e:
        # 如果無法獲取資料，預設為盤整
        results['regime'] = "Range-bound (盤整)"
        results['error'] = str(e)
        
    return results