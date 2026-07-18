import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

def bulk_funnel_filter(ticker_list):
    """
    分批下載並執行漏斗篩選，避免 YFRateLimitError
    """
    print(f">>> [系統] 開始分批抓取 {len(ticker_list)} 檔股票數據...")
    valid_stocks = []
    chunk_size = 50  # 每次下載 50 檔
    
    for i in range(0, len(ticker_list), chunk_size):
        chunk = ticker_list[i : i + chunk_size]
        print(f"    - 正在處理: {i} ~ {min(i + chunk_size, len(ticker_list))}...")
        
        try:
            # 批次下載
            data = yf.download(chunk, period="20d", threads=True, progress=False)
            
            if data.empty:
                continue
                
            # 處理多檔股票的 MultiIndex 結構
            if 'Close' in data.columns.levels[0]:
                close_df = data['Close']
                vol_df = data['Volume']
            else:
                # 處理只有 1 檔時的結構
                close_df = data[['Close']]
                vol_df = data[['Volume']]
            
            # 針對該批次中的每檔股票進行篩選
            for ticker in chunk:
                if ticker not in close_df.columns:
                    continue
                
                s_close = close_df[ticker].dropna()
                s_vol = vol_df[ticker].dropna()
                
                if len(s_close) < 20:
                    continue
                
                # 計算 Bollinger Bands
                bb = ta.bbands(s_close, length=20, std=2)
                if bb is None: continue
                
                cols = bb.columns
                bbl = bb[cols[0]].iloc[-1]
                bbm = bb[cols[1]].iloc[-1]
                bbu = bb[cols[2]].iloc[-1]
                
                # 計算頻寬
                current_bw = (bbu - bbl) / bbm
                
                # 篩選條件
                if not (0.005 < current_bw < 0.15):
                    continue
                    
                last_close = s_close.iloc[-1]
                avg_volume = s_vol.mean()
                
                if (last_close > 10) and (avg_volume > 500):
                    valid_stocks.append(ticker)
            
            # 每次下載後暫停 1 秒，保護連線
            time.sleep(1)
            
        except Exception as e:
            print(f">>> [警告] 該批次下載失敗，跳過: {e}")
            continue

    print(f">>> [系統] 漏斗篩選完成：符合條件共 {len(valid_stocks)} 檔。")
    return valid_stocks