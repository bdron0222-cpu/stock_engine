import yfinance as yf
import pandas as pd
import json
import os

# 設定檔路徑
STATE_FILE = "market_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"status": "active", "last_update": "2000-01-01"}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def monitor_market():
    print(">>> [系統] 開始執行大盤熔斷監控...")
    
    # 1. 抓取大盤數據 (TWII)
    ticker = "^TWII"
    df = yf.download(ticker, period="1mo", progress=False)
    
    if df.empty:
        print(">>> [錯誤] 無法取得大盤數據")
        return

    # 確保資料為 1D Series，並強制轉為 float 以進行單值運算
    close_series = df['Close'].squeeze() 
    curr_close = float(close_series.iloc[-1])
    prev_close = float(close_series.iloc[-2])
    pct_change = (curr_close - prev_close) / prev_close
    
    # 計算 5 日均線
    sma5 = float(close_series.rolling(window=5).mean().iloc[-1])
    
    # 計算最近 3 日的漲跌幅 Series
    last_3_days_pct = close_series.pct_change().tail(3)
    
    # 載入當前狀態
    state = load_state()
    
    # 2. 判斷邏輯
    # 【觸發防禦機制】：當日跌幅超過 2%
    if pct_change < -0.02:
        state["status"] = "frozen"
        state["reason"] = f"Market crash {pct_change:.2%}"
        print(f">>> [警告] 觸發熔斷！當日跌幅 {pct_change:.2%}")
        
    # 【解除防禦機制】：若處於熔斷狀態，檢查恢復條件
    elif state["status"] == "frozen":
        # 條件1: 收盤價 > 5日均線 OR 條件2: 連續3日跌幅皆未超過 1%
        cond1 = curr_close > sma5
        cond2 = (last_3_days_pct.abs() < 0.01).all()
        
        if cond1 or cond2:
            state["status"] = "active"
            state["reason"] = "Market recovered"
            print(f">>> [恢復] 市場已穩定 (條件滿足)，解除熔斷。")
        else:
            print(f">>> [防禦中] 市場尚未滿足解凍條件 (今日收盤: {curr_close:.2f}, 5MA: {sma5:.2f})")

    # 更新時間戳記
    state["last_update"] = str(df.index[-1].date())
    save_state(state)
    print(f">>> [系統] 當前大盤狀態: {state['status']}")

if __name__ == "__main__":
    monitor_market()