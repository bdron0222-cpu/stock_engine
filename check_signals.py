import pandas as pd
import os

def check_signals():
    csv_file = 'oos_test_results.csv'
    
    if not os.path.exists(csv_file):
        print(f"錯誤：找不到 {csv_file}，請確認是否已執行 run_oos_test.py")
        return
    
    # 讀取 CSV
    df = pd.read_csv(csv_file)
    
    # 過濾有效訊號
    signals = df[df['is_signal'] == True].copy()
    
    if signals.empty:
        print(">>> 目前沒有產生任何有效的訊號。")
        return
        
    signals['date'] = pd.to_datetime(signals['date'])
    
    # 統計每月訊號數
    monthly_counts = signals['date'].dt.to_period('M').value_counts().sort_index()
    
    print("\n" + "="*30)
    print("【訊號分佈統計 (每月)】")
    print(monthly_counts)
    print("="*30)
    
    # 顯示前 10 筆明細，觀察發生在哪些日期
    print("\n【前 10 筆訊號日期明細】")
    print(signals[['ticker', 'date']].head(10).to_string(index=False))
    print("-" * 30)

if __name__ == "__main__":
    check_signals()