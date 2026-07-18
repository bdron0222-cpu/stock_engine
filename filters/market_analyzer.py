import pandas as pd
import pandas_ta as ta
import yfinance as yf

def analyze_market_regime(ticker_list):
    """計算 ADX 與 MA20，並加入詳細除錯診斷"""
    try:
        print(">>> [Debug] 正在下載大盤數據...")
        # 下載數據
        data = yf.download(ticker_list, period="100d", threads=True, progress=False)
        
        # 處理 MultiIndex 格式 (確保資料結構正確)
        if isinstance(data.columns, pd.MultiIndex):
            data = data.xs(ticker_list[0], axis=1, level=1)
        
        df = data.copy()
        
        # 指標計算
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        ma20 = df['Close'].rolling(window=20).mean()
        
        # 取得最新數值
        current_adx = adx['ADX_14'].iloc[-1]
        current_close = df['Close'].iloc[-1]
        current_ma20 = ma20.iloc[-1]
        
        # 判斷邏輯
        regime = "趨勢盤 (Trending)" if current_adx > 25 else ("盤整盤 (Range-bound)" if current_adx < 20 else "觀察區 (Observe)")
        direction = "多頭 (Bullish)" if current_close > current_ma20 else "空頭 (Bearish)"
        action = "積極進場" if (regime == "趨勢盤 (Trending)" and direction == "多頭 (Bullish)") else ("區間操作" if regime == "盤整盤 (Range-bound)" else "觀望")
            
        result = {
            'regime': regime,
            'direction': direction,
            'action': action,
            'adx': round(current_adx, 2)
        }
        print(f">>> [Debug] 分析成功，回傳結果: {result}")
        return result
        
    except Exception as e:
        # 修改處：明確印出錯誤訊息，方便我們追蹤問題根源
        print(f">>> [Debug] 市場分析錯誤: {e}") 
        return {
            'regime': '資料錯誤',
            'direction': '未知',
            'action': '無法連線',
            'adx': 0
        }