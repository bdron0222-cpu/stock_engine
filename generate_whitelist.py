import pandas as pd
import pickle
import os
from strategies.range_strategy import run_range_strategy

def generate_whitelist():
    # 1. 載入訓練資料
    with open('cache_train.pkl', 'rb') as f:
        train_data = pickle.load(f)
    
    print(">>> 正在分析 2025 年訓練集，篩選賺錢股票...")
    
    # 2. 執行策略 (使用訓練時的最佳參數，這裡示範用你的極限參數)
    results = run_range_strategy(train_data, kd_threshold=80, bb_buffer=1.2, end_date='2025-12-31')
    
    # 3. 簡單回測計算 (買入 vs 賣出)
    trades = []
    for r in results:
        ticker = r['ticker']
        df = train_data[ticker]
        date = pd.to_datetime(r['date'])
        if date not in df.index: continue
        
        loc = df.index.get_loc(date)
        if (loc + 5) >= len(df): continue
        
        buy_price = df.iloc[loc]['Close']
        sell_price = df.iloc[loc+5]['Close']
        profit = (sell_price - buy_price)
        trades.append({'ticker': ticker, 'profit': profit})
        
    # 4. 分組統計，找出平均獲利 > 0 的股票
    df_trades = pd.DataFrame(trades)
    stats = df_trades.groupby('ticker')['profit'].mean()
    whitelist = stats[stats > 0].index.tolist()
    
    # 5. 存檔
    pd.DataFrame({'ticker': whitelist}).to_csv('whitelist.csv', index=False)
    print(f">>> 篩選完成！共有 {len(whitelist)} 檔股票進入強者清單。")
    print(">>> 已存入 whitelist.csv")

if __name__ == "__main__":
    generate_whitelist()