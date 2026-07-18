import pandas as pd
import pandas_ta as ta
import pickle
import os
import matplotlib.pyplot as plt
import numpy as np

def run_stress_test():
    print(">>> [系統啟動] 執行「壓力測試 + 風險指標分析版」(已修正語法)...")
    
    if not os.path.exists('cache_test.pkl'): return print("錯誤：缺少 cache_test.pkl")
    with open('cache_test.pkl', 'rb') as f:
        data_dict = pickle.load(f)
    
    signals = pd.read_csv('oos_test_results.csv')
    signals = signals[signals['is_signal'] == True].copy()
    signals['date'] = pd.to_datetime(signals['date']).dt.normalize()
    
    trades = []
    FIXED_INVESTMENT = 50000
    INITIAL_CAPITAL = 1000000
    
    # 實盤參數
    DISCOUNT = 0.6 
    COMMISSION_RATE = 0.001425 * DISCOUNT
    TAX_RATE = 0.003
    MIN_FEE = 20
    SLIPPAGE = 0.0005 
    
    print(f">>> 開始模擬交易 (樣本數: {len(signals)})...")
    for _, row in signals.iterrows():
        ticker = row['ticker']
        if ticker not in data_dict: continue
        
        df = data_dict[ticker].copy()
        if len(df) < 60: continue
        
        df.index = pd.to_datetime(df.index).normalize()
        bb = ta.bbands(df['Close'], length=20, std=2)
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        sma = ta.sma(df['Close'], length=50)
        df_full = pd.concat([df, bb, adx, sma], axis=1)
        
        cols = df_full.columns
        bbu = [c for c in cols if 'BBU' in c][0]
        sma_col = [c for c in cols if 'SMA' in c][0]
        adx_col = [c for c in cols if 'ADX' in c][0]
        
        if pd.isna(df_full.loc[row['date'], adx_col]) or df_full.loc[row['date'], adx_col] > 30: continue
        if df_full.loc[row['date'], 'Close'] < df_full.loc[row['date'], sma_col]: continue
        if not (df_full.loc[row['date'], 'Close'] > df_full.loc[row['date'], 'Open']): continue
        
        daily_volume = df_full.loc[row['date'], 'Volume']
        current_price = df_full.loc[row['date'], 'Close']
        shares_to_buy = FIXED_INVESTMENT // current_price
        if (shares_to_buy / daily_volume) > 0.05: continue
        
        try:
            start_loc = df_full.index.get_loc(row['date'])
            buy_price = df_full.iloc[start_loc]['Close']
            
            reason = "timeout"
            exit_price = buy_price
            exit_date = df_full.index[start_loc]
            
            for i in range(start_loc + 1, min(start_loc + 6, len(df_full))):
                close_i = df_full.iloc[i]['Close']
                bbu_i = df_full.iloc[i][bbu]
                
                profit_pct = (close_i - buy_price) / buy_price
                current_sl = buy_price * 1.025 if profit_pct >= 0.02 else buy_price * 0.93
                
                if close_i >= bbu_i or close_i <= current_sl or i == start_loc + 5:
                    exit_price = close_i
                    exit_date = df_full.index[i]
                    reason = "take_profit" if close_i >= bbu_i else ("stop_loss" if close_i <= current_sl else "timeout")
                    break
            
            buy_cost = (buy_price * (1 + SLIPPAGE)) * shares_to_buy
            exit_revenue = (exit_price * (1 - SLIPPAGE)) * shares_to_buy
            commission = max(MIN_FEE, buy_cost * COMMISSION_RATE) + max(MIN_FEE, exit_revenue * COMMISSION_RATE)
            tax = exit_revenue * TAX_RATE
            profit = (exit_revenue - buy_cost) - commission - tax
            
            trades.append({'date': exit_date, 'profit': profit, 'reason': reason})
        except: continue

    if not trades: return print(">>> 無有效交易。")
    
    # --- 風險指標計算 ---
    trade_df = pd.DataFrame(trades)
    daily_equity = trade_df.groupby('date')['profit'].sum().cumsum() + INITIAL_CAPITAL
    
    # 修正後語法：使用 .ffill()
    all_dates = pd.date_range(start=daily_equity.index.min(), end=daily_equity.index.max())
    equity_curve = daily_equity.reindex(all_dates).ffill()
    
    # 計算 MDD
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    mdd = drawdown.min()
    
    # 計算 Calmar Ratio
    total_return = (equity_curve.iloc[-1] / INITIAL_CAPITAL) - 1
    years = len(equity_curve) / 252
    annualized_return = (1 + total_return) ** (1 / years) - 1
    calmar_ratio = annualized_return / abs(mdd) if mdd != 0 else 0
    
    print("\n" + "="*40)
    print("【最終壓力測試與風險評估】")
    print(trade_df.groupby('reason')['profit'].agg(['sum', 'count', 'mean']))
    print(f"總淨損益: {trade_df['profit'].sum():.2f} TWD")
    print("-" * 40)
    print(f"最大回撤 (MDD): {mdd*100:.2f}%")
    print(f"年化報酬率: {annualized_return*100:.2f}%")
    print(f"卡爾馬比率 (Calmar Ratio): {calmar_ratio:.2f}")
    print("="*40 + "\n")

if __name__ == "__main__":
    run_stress_test()