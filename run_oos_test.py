import pandas as pd
import itertools
import yfinance as yf
import os
import pickle
import time
from tqdm import tqdm
from strategies.range_strategy import run_range_strategy

def fetch_data(tickers, start_date, end_date, cache_filename):
    # 獲取絕對路徑，避免路徑衝突
    abs_path = os.path.abspath(cache_filename)
    
    # 強制檢測檔案並讀取
    if os.path.exists(abs_path):
        try:
            print(f">>> 正在嘗試載入快取: {abs_path}")
            with open(abs_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"    [!] 快取載入失敗 (可能是檔案損毀)，將刪除後重新下載: {e}")
            try:
                os.remove(abs_path)
            except:
                pass
    
    # 如果沒有快取或快取載入失敗，則開始下載
    data_dict = {}
    print(f">>> 正在下載資料 ({start_date} ~ {end_date})...")
    
    chunk_size = 50
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        print(f"  - 處理中: {i} ~ {min(i + chunk_size, len(tickers))}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(2)
                data = yf.download(chunk, start=start_date, end=end_date, group_by='ticker', progress=False)
                
                for ticker in chunk:
                    if ticker in data.columns.levels[0]:
                        df = data[ticker].dropna()
                        if len(df) >= 30:
                            data_dict[ticker] = df
                break 
            except Exception as e:
                print(f"    [!] 第 {attempt+1} 次嘗試失敗: {e}")
                time.sleep(5)
    
    print(f">>> 存入快取: {abs_path}")
    with open(abs_path, 'wb') as f:
        pickle.dump(data_dict, f)
        
    return data_dict

def run_training_phase(data_dict, kd_candidates, bb_candidates):
    print("\n>>> [訓練階段]...")
    best_params = None
    best_score = -1
    combinations = list(itertools.product(kd_candidates, bb_candidates))
    for kd, bb in combinations:
        results = run_range_strategy(data_dict, kd_threshold=kd, bb_buffer=bb, end_date='2026-06-01')
        score = sum([1 for r in results if r['is_signal']])
        print(f"  - 參數 KD<{kd}, BB={bb} | 訊號數: {score}")
        if score > best_score:
            best_score = score
            best_params = {'kd': kd, 'bb': bb}
    return best_params

def run_testing_phase(data_dict, best_params):
    print(f"\n>>> [測試階段] 使用: {best_params}")
    results = run_range_strategy(data_dict, kd_threshold=best_params['kd'], bb_buffer=best_params['bb'], end_date='2026-06-01')
    pd.DataFrame(results).to_csv('oos_test_results.csv', index=False)
    print(">>> 測試結果存入 oos_test_results.csv")

if __name__ == "__main__":
    # 執行前確保沒有遺留的損毀快取
    for f in ['cache_train.pkl', 'cache_test.pkl']:
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass

    df_list = pd.read_csv('stocks_list.csv')
    tickers = df_list['ticker'].tolist()
    
    train_data = fetch_data(tickers, '2025-01-01', '2025-12-31', 'cache_train.pkl')
    test_data = fetch_data(tickers, '2026-01-01', '2026-06-01', 'cache_test.pkl')
    
    best_params = run_training_phase(train_data, [60, 70, 80], [1.05, 1.1, 1.2])
    run_testing_phase(test_data, best_params)