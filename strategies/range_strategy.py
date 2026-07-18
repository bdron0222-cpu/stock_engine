import pandas as pd
import pandas_ta as ta
from tqdm import tqdm

def run_range_strategy(data_dict, kd_threshold=30, bb_buffer=1.02, end_date='2026-06-01'):
    results = []
    end_date = pd.to_datetime(end_date)
    
    print(f"正在掃描 {len(data_dict)} 檔股票 (欄位名稱校準版)...")

    for ticker, df in tqdm(data_dict.items(), desc="掃描進度"):
        if len(df) < 30: continue
        
        # 1. 計算指標
        stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3, smooth_k=3)
        bb = ta.bbands(df['Close'], length=20, std=2)
        
        # 合併後直接操作 DataFrame，避免索引混亂
        df_full = pd.concat([df, stoch, bb], axis=1).dropna()
        
        # 找出正確的欄位名稱 (pandas_ta 預設名稱)
        # stoch: ['STOCHk_9_3_3', 'STOCHd_9_3_3']
        # bb:    ['BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0', 'BBB_20_2.0']
        k_col = [c for c in df_full.columns if 'STOCHk' in c][0]
        d_col = [c for c in df_full.columns if 'STOCHd' in c][0]
        bbl_col = [c for c in df_full.columns if 'BBL' in c][0]
        
        # 2. 歷史迴圈
        for i in range(1, len(df_full)):
            current_date = df_full.index[i]
            if current_date > end_date: continue 
            
            # 使用明確的欄位名稱取值
            k = df_full.loc[current_date, k_col]
            d = df_full.loc[current_date, d_col]
            prev_k = df_full.iloc[i-1][k_col]
            prev_d = df_full.iloc[i-1][d_col]
            bbl = df_full.loc[current_date, bbl_col]
            close = df_full.loc[current_date, 'Close']
            
            # 策略邏輯
            is_bb_touch = (close <= (bbl * bb_buffer))
            is_kd_golden_cross = (prev_k < prev_d) and (k > d) and (k < kd_threshold)
            
            if is_bb_touch and is_kd_golden_cross:
                results.append({
                    'ticker': ticker,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'is_signal': True
                })

    return results