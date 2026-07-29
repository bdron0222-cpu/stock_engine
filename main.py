import json
import sys
import os
import pandas as pd
import numpy as np
import yfinance as yf
from filters.bulk_funnel_filter import bulk_funnel_filter
from utils.stats_helper import calculate_beta_and_rho

# 設定檔與路徑
MARKET_STATE_FILE = "market_state.json"
STOCK_LIST_FILE = "stocks_list.csv"

# --- 原生實作取代 pandas-ta ---
def calculate_bbands(close, length=20, std_dev=1.2):
    """計算布林通道下軌 (Lower Band)"""
    sma = close.rolling(window=length).mean()
    std = close.rolling(window=length).std()
    bbl = sma - (std * std_dev)
    return bbl

def calculate_stoch(high, low, close, k_period=14, d_period=3):
    """計算 Stochastic Oscillator (%K, %D)"""
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    
    # 計算 %K
    k = 100 * ((close - low_min) / (high_max - low_min))
    # 計算 %D (K 的移動平均)
    d = k.rolling(window=d_period).mean()
    return k, d

def is_market_allowed():
    """防禦層：檢查大盤狀態"""
    if not os.path.exists(MARKET_STATE_FILE): return True 
    try:
        with open(MARKET_STATE_FILE, "r") as f:
            state = json.load(f)
            return state.get("status") != "frozen"
    except: return True

def calculate_strategy(ticker):
    """策略核心：使用原生 pandas 計算取代 pandas-ta"""
    try:
        df = yf.download(ticker, period="1mo", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs(ticker, axis=1, level=1)
            
        if len(df) < 20: 
            return pd.Series([False, 999.0], index=['buy_signal', 'bb_dist'])
        
        # 使用自定義函數計算指標
        bbl = calculate_bbands(df['Close'], length=20, std_dev=1.2)
        k, d = calculate_stoch(df['High'], df['Low'], df['Close'])
        
        # 獲取最後與倒數第二個值
        curr_close = df['Close'].iloc[-1]
        curr_bbl = bbl.iloc[-1]
        curr_k = k.iloc[-1]
        curr_d = d.iloc[-1]
        prev_k = k.iloc[-2]
        prev_d = d.iloc[-2]
        
        bb_dist = curr_close - curr_bbl
        
        # 買入訊號邏輯：觸及下軌 且 KD 黃金交叉
        is_buy = (curr_close <= curr_bbl) and (curr_k < 80) and (prev_k < prev_d) and (curr_k > curr_d)
        
        return pd.Series([is_buy, bb_dist], index=['buy_signal', 'bb_dist'])
    except Exception as e:
        return pd.Series([False, 999.0], index=['buy_signal', 'bb_dist'])

def main():
    print(">>> [系統啟動] 每日訊號生成與策略驗證...")
    
    # 【修改處】：取消強制終止 (sys.exit)，改為僅印出警告提示，確保防禦期間資料照常更新
    if not is_market_allowed(): 
        print(">>> [提示] 目前大盤處於防禦/熔斷狀態，但已依照設定繼續抓取與更新今日最新數據...")
    
    ticker_list = pd.read_csv(STOCK_LIST_FILE)['ticker'].tolist() if os.path.exists(STOCK_LIST_FILE) else []
    if not ticker_list: sys.exit()
    
    # 1. 篩選股票
    print(f">>> [系統] 執行漏斗篩選...")
    watchlist_tickers = bulk_funnel_filter(ticker_list)
    
    # 如果今日無符合標的，輸出空表覆蓋舊檔案
    if not watchlist_tickers:
        print(">>> 今日無符合標的，覆寫為空表。")
        empty_df = pd.DataFrame(columns=['ticker', 'date', 'price', 'volume', 'beta', 'rho', 'buy_signal', 'bb_dist'])
        empty_df.to_csv("watchlist_conservative.csv", index=False)
        empty_df.to_csv("watchlist_aggressive.csv", index=False)
        empty_df.to_csv("watchlist_noise.csv", index=False)
        empty_df.to_csv("all_candidates_proximity.csv", index=False)
        return
        
    watchlist = pd.DataFrame(watchlist_tickers, columns=['ticker'])
    
    # 2. 獲取大盤數據用於計算 Beta/Rho
    print(">>> [系統] 正在準備統計數據 (Beta/Rho/Volume)...")
    market_df = yf.download("^TWII", period="1mo", progress=False)
    
    latest_date_str = market_df.index[-1].strftime('%Y-%m-%d')
    print(f">>> [檢查] 目前大盤數據最新日期為: {latest_date_str}")

    market_data = market_df['Close'].iloc[:, 0] if isinstance(market_df.columns, pd.MultiIndex) else market_df['Close']
    
    # 3. 計算並填入 date, price, volume, beta, rho
    print(f">>> [系統] 正在計算 {len(watchlist)} 檔股票的技術統計...")
    date_list, price_list, volume_list, beta_list, rho_list = [], [], [], [], []
    
    for ticker in watchlist['ticker']:
        stock_df = yf.download(ticker, period="1mo", progress=False)
        if isinstance(stock_df.columns, pd.MultiIndex):
            stock_df = stock_df.xs(ticker, axis=1, level=1)
        
        data_date = stock_df.index[-1].strftime('%Y-%m-%d')
        price = stock_df['Close'].iloc[-1]
        raw_volume = stock_df['Volume'].iloc[-1] if 'Volume' in stock_df.columns else 0
        volume = int(round(raw_volume / 1000))
        
        beta, rho = calculate_beta_and_rho(stock_df['Close'], market_data)
        
        date_list.append(data_date)
        price_list.append(price)
        volume_list.append(volume)
        beta_list.append(beta)
        rho_list.append(rho)
        
    watchlist['date'] = date_list
    watchlist['price'] = price_list
    watchlist['volume'] = volume_list
    watchlist['beta'] = beta_list
    watchlist['rho'] = rho_list
    
    # 4. 執行策略驗證
    print(f">>> [策略] 正在驗證買入訊號...")
    strategy_results = watchlist['ticker'].apply(calculate_strategy)
    watchlist = pd.concat([watchlist, strategy_results], axis=1)
    
    # 5. 分類並存檔
    target_columns = ['ticker', 'date', 'price', 'volume', 'beta', 'rho', 'buy_signal', 'bb_dist']
    
    cons = watchlist[watchlist['beta'] < 0.5][target_columns]
    aggr = watchlist[(watchlist['beta'] > 1.0) & (watchlist['rho'] > 0.5)][target_columns]
    noise = watchlist[(watchlist['beta'].abs() < 0.1) & (watchlist['rho'].abs() < 0.1)][target_columns]
    
    cons.to_csv("watchlist_conservative.csv", index=False)
    aggr.to_csv("watchlist_aggressive.csv", index=False)
    noise.to_csv("watchlist_noise.csv", index=False)
    
    watchlist[target_columns].to_csv("all_candidates_proximity.csv", index=False)
    
    print(f">>> [成功] 已產出分類清單，成交量已轉換為張數。")

if __name__ == "__main__":
    main()
