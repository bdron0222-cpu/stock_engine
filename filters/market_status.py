import yfinance as yf

def check_market_status(ticker="^TWII"):
    """
    檢查大盤狀態，包含熔斷與解凍機制
    """
    try:
        hist = yf.Ticker(ticker).history(period="10d")
        if len(hist) < 5: return False

        curr_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        drop_pct = (prev_close - curr_close) / prev_close

        # 1. 熔斷機制 (若跌幅 > 2%)
        if drop_pct > 0.02:
            print(f"【警示】大盤跌幅達 {drop_pct:.2%}, 觸發熔斷！")
            return True 

        # 2. 解凍機制 (符合任一條件即可恢復)
        ma5 = hist['Close'].rolling(window=5).mean().iloc[-1]
        last_3d_pct = hist['Close'].pct_change().tail(3).abs()
        
        # 條件 A: 站上 5MA | 條件 B: 連續 3 日波動 < 1%
        if (curr_close > ma5) or (last_3d_pct.max() < 0.01):
            print("【狀態】已達解凍條件，系統恢復交易。")
            return False

        return False # 正常狀態
    except Exception as e:
        print(f"檢查大盤狀態失敗: {e}")
        return False