import json
import sys
import os
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from filters.bulk_funnel_filter import bulk_funnel_filter
from utils.stats_helper import calculate_beta_and_rho

# 設定檔與路徑
MARKET_STATE_FILE = "market_state.json"
STOCK_LIST_FILE = "stocks_list.csv"

def is_market_allowed():
    """防禦層：檢查大盤狀態"""
    if not os.path.exists(MARKET_STATE_FILE): return True 
    try:
        with open(MARKET_STATE_FILE, "r") as f:
            state = json.load(f)
            return state.get("status") != "frozen"
    except: return True

def calculate_strategy(ticker):
    """策略核心：BB 1.2 + KD 黃金交叉，並計算 bb_dist"""
    try:
        df = yf.download(ticker, period="1mo", progress=False)
        # 處理 MultiIndex 格式
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs(ticker, axis=1, level=1)
            
        if len(df) < 20: 
            return pd.Series([False, 999.0], index=['buy_signal', 'bb_dist'])
        
        # 計算指標
        bb = ta.bbands(df['Close'], length=20, std=1.2)
        stoch = ta.stoch(df['High'], df['Low'], df['Close'], fast_k=14, slow_k=3, slow_d=3)
        df_combined = pd.concat([df, bb, stoch], axis=1)
        
        # 動態抓取欄位名稱
        bbl_cols = [c for c in df_combined.columns if 'BBL' in c]
        k_cols = [c for c in df_combined.columns if 'STOCHk' in c]
        d_cols = [c for c in df_combined.columns if 'STOCHd' in c]
        
        if not bbl_cols or not k_cols or not d_cols:
             return pd.Series([False, 999.0], index=['buy_signal', 'bb_dist'])

        bbl = df_combined[bbl_cols[0]].iloc[-1]
        close = df_combined['Close'].iloc[-1]
        k = df_combined[k_cols[0]].iloc[-1]
        d = df_combined[d_cols[0]].iloc[-1]
        k_prev = df_combined[k_cols[0]].iloc[-2]
        d_prev = df_combined[d_cols[0]].iloc[-2]
        
        bb_dist = close - bbl
        is_buy = (close <= bbl) and (k < 80) and (k_prev < d_prev) and (k > d)
        
        return pd.Series([is_buy, bb_dist], index=['buy_signal', 'bb_dist'])
    except:
        return pd.Series([False, 999.0], index=['buy_signal', 'bb_dist'])

def main():
    print(">>> [系統啟動] 每日訊號生成與策略驗證...")
    if not is_market_allowed(): sys.exit()
    
    ticker_list = pd.read_csv(STOCK_LIST_FILE)['ticker'].tolist() if os.path.exists(STOCK_LIST_FILE) else []
    if not ticker_list: sys.exit()
    
    # 1. 篩選股票
    print(f">>> [系統] 執行漏斗篩選...")
    watchlist_tickers = bulk_funnel_filter(ticker_list)
    if not watchlist_tickers:
        print(">>> 今日無符合標的。")
        return
    watchlist = pd.DataFrame(watchlist_tickers, columns=['ticker'])
    
    # 2. 獲取大盤數據用於計算 Beta/Rho
    print(">>> [系統] 正在準備統計數據 (Beta/Rho/Volume)...")
    market_df = yf.download("^TWII", period="1mo", progress=False)
    market_data = market_df['Close'].iloc[:, 0] if isinstance(market_df.columns, pd.MultiIndex) else market_df['Close']
    
    # 3. 計算並填入 price, volume, beta, rho
    print(f">>> [系統] 正在計算 {len(watchlist)} 檔股票的技術統計...")
    price_list = []
    volume_list = []
    beta_list = []
    rho_list = []
    
    for ticker in watchlist['ticker']:
        stock_df = yf.download(ticker, period="1mo", progress=False)
        if isinstance(stock_df.columns, pd.MultiIndex):
            stock_df = stock_df.xs(ticker, axis=1, level=1)
        
        price = stock_df['Close'].iloc[-1]
        
        # 單位換算：股數轉為張數 (1 張 = 1000 股)
        raw_volume = stock_df['Volume'].iloc[-1] if 'Volume' in stock_df.columns else 0
        volume = int(round(raw_volume / 1000))
        
        beta, rho = calculate_beta_and_rho(stock_df['Close'], market_data)
        
        price_list.append(price)
        volume_list.append(volume)
        beta_list.append(beta)
        rho_list.append(rho)
        
    watchlist['price'] = price_list
    watchlist['volume'] = volume_list
    watchlist['beta'] = beta_list
    watchlist['rho'] = rho_list
    
    # 4. 執行策略驗證
    print(f">>> [策略] 正在驗證買入訊號...")
    strategy_results = watchlist['ticker'].apply(calculate_strategy)
    watchlist = pd.concat([watchlist, strategy_results], axis=1)
    
    # 5. 分類並存檔
    target_columns = ['ticker', 'price', 'volume', 'beta', 'rho', 'buy_signal', 'bb_dist']
    
    cons = watchlist[watchlist['beta'] < 0.5][target_columns]
    aggr = watchlist[(watchlist['beta'] > 1.0) & (watchlist['rho'] > 0.5)][target_columns]
    noise = watchlist[(watchlist['beta'].abs() < 0.1) & (watchlist['rho'].abs() < 0.1)][target_columns]
    
    cons.to_csv("watchlist_conservative.csv", index=False)
    aggr.to_csv("watchlist_aggressive.csv", index=False)
    noise.to_csv("watchlist_noise.csv", index=False)
    
    print(f">>> [成功] 已產出分類清單，成交量已轉換為張數。")

if __name__ == "__main__":
    main()