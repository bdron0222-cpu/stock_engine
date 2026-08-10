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

def analyze_granville(ticker="^TWII", window=20):
    """
    分析大盤目前符合葛蘭碧八大法則的哪個波段/規則
    """
    try:
        market_data = yf.download(ticker, period="3mo", progress=False)
        if isinstance(market_data.columns, pd.MultiIndex):
            market_data = market_data.xs(ticker, axis=1, level=1)
        
        close = market_data['Close']
        if len(close) < window + 10:
            return {"rule": "資料不足", "title": "資料不足", "desc": "無法計算足夠天數的均線", "type": "neutral"}
            
        ma = calculate_sma(close, window)
        curr_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        curr_ma = float(ma.iloc[-1])
        prev_ma = float(ma.iloc[-2])
        
        # 計算均線過去 5 天的斜率方向
        ma_slope = float(ma.iloc[-1] - ma.iloc[-5])
        ma_is_rising = ma_slope > 0
        ma_is_falling = ma_slope < 0
        ma_is_flat = abs(ma_slope) <= (curr_ma * 0.002) # 微幅變動視為走平
        
        # 計算乖離率 (%)
        bias = (curr_price - curr_ma) / curr_ma * 100
        
        # 葛蘭碧八大法則邏輯判定
        # 1. 買進法則一：均線從下降轉為平緩或向上，股價從下往上突破均線
        if (prev_price <= prev_ma) and (curr_price > curr_ma) and (ma_is_rising or ma_is_flat):
            return {"rule": "買進法則 1", "title": "【買進一】突破均線（起漲點）", "desc": "均線由跌轉平或向上，股價由下往上突破均線，代表多頭行情可能展開。", "type": "buy"}
        
        # 2. 買進法則二：股價雖跌破均線，但均線仍持續向上，且不久又回升至均線之上
        elif (prev_price < prev_ma) and (curr_price > curr_ma) and ma_is_rising and (close.iloc[-5:].min() < curr_ma):
            return {"rule": "買進法則 2", "title": "【買進二】回檔買進（假跌破）", "desc": "股價短暫跌破持續向上的均線後迅速收復，為強勢回檔買點。", "type": "buy"}
        
        # 3. 買進法則三：股價在均線上方持續上漲，回檔時未跌破均線，再度止跌回升
        elif (curr_price > curr_ma) and ma_is_rising and (close.iloc[-3:].min() >= curr_ma * 0.99) and bias < 5:
            return {"rule": "買進法則 3", "title": "【買進三】多頭回檔支撐", "desc": "股價在均線上方運行，回檔未破均線即止跌，為多頭續勢買點。", "type": "buy"}
        
        # 4. 買進法則四：股價遠在均線下方暴跌，與均線距離過遠，隨時可能反彈
        elif curr_price < curr_ma and bias < -4.5:
            return {"rule": "買進法則 4", "title": "【買進四】乖離過大搶反彈", "desc": "股價暴跌遠離均線下方，乖離率過大，短線有技術性反彈需求（風險較高）。", "type": "buy"}
        
        # 5. 賣出法則五：均線從上升轉為平緩或向下，股價從上往下跌破均線
        elif (prev_price >= prev_ma) and (curr_price < curr_ma) and (ma_is_falling or ma_is_flat):
            return {"rule": "賣出法則 5", "title": "【賣出五】跌破均線（起跌點）", "desc": "均線由漲轉平或向下，股價由上往下跌破均線，代表空頭行情可能展開。", "type": "sell"}
        
        # 6. 賣出法則六：股價雖反彈突破均線，但均線仍持續向下，且不久又跌回均線之下
        elif (prev_price > prev_ma) and (curr_price < curr_ma) and ma_is_falling and (close.iloc[-5:].max() > curr_ma):
            return {"rule": "賣出法則 6", "title": "【賣出六】反彈逃命（假突破）", "desc": "股價反彈越過下行的均線但未能站穩又再度跌破，為反彈逃命點。", "type": "sell"}
        
        # 7. 賣出法則七：股價在均線下方持續下跌，反彈時未突破均線，再度反轉向下
        elif (curr_price < curr_ma) and ma_is_falling and (close.iloc[-3:].max() <= curr_ma * 1.01) and bias > -5:
            return {"rule": "賣出法則 7", "title": "【賣出七】空頭反壓逃命", "desc": "股價在均線下方弱勢運行，反彈受阻於均線再次下跌，為空頭續跌點。", "type": "sell"}
        
        # 8. 賣出法則八：股價遠在均線上方的暴漲，與均線距離過遠，隨時可能回檔
        elif curr_price > curr_ma and bias > 4.5:
            return {"rule": "賣出法則 8", "title": "【賣出八】乖離過大回檔", "desc": "股價暴漲遠離均線上方，乖離率過大，短線有技術性回檔修正壓力。", "type": "sell"}
        
        else:
            return {"rule": "盤整/觀望", "title": "【中性區間】盤整或過渡期", "desc": f"目前大盤與 20MA 糾結震盪（乖離率: {bias:.2f}%），無明顯極端訊號。", "type": "neutral"}
            
    except Exception as e:
        return {"rule": "分析錯誤", "title": "計算異常", "desc": str(e), "type": "neutral"}
