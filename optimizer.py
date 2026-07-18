import itertools
import pickle
import os
import pandas as pd
from strategies.range_strategy import run_range_strategy

def optimize():
    # 1. 載入訓練資料
    # Optimizer 需要訓練用的歷史數據 (cache_train.pkl)，否則無法運算指標
    if not os.path.exists('cache_train.pkl'):
        print("錯誤：找不到 cache_train.pkl。請先執行過回測流程或產生訓練資料快取。")
        return
        
    with open('cache_train.pkl', 'rb') as f:
        train_data = pickle.load(f) # 這才是 run_range_strategy 需要的數據格式
    
    # 2. 定義要測試的參數範圍
    kd_ranges = [20, 25, 30, 35]
    bb_ranges = [1.0, 1.01, 1.02, 1.03]
    
    # 3. 產生所有組合
    combinations = list(itertools.product(kd_ranges, bb_ranges))
    print(f">>> [系統] 開始進行網格搜尋，共 {len(combinations)} 種參數組合...")
    
    best_score = -999999
    best_params = None
    
    # 4. 迴圈測試
    for kd, bb in combinations:
        print(f"測試中: KD<{kd}, BB_Buffer={bb}")
        
        # 傳入 train_data 字典，而非單純的 ticker_list
        results = run_range_strategy(train_data, kd_threshold=kd, bb_buffer=bb)
        
        # 以「產生的有效訊號數量」作為評分標準
        score = len(results) 
        
        if score > best_score:
            best_score = score
            best_params = (kd, bb)
            
    print(f">>> [優化完成] 最佳參數組合: KD<{best_params[0]}, BB_Buffer={best_params[1]}")

if __name__ == "__main__":
    optimize()