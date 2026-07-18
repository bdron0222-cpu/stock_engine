import pandas as pd
import pandas_ta as ta
import pickle
import os
import matplotlib.pyplot as plt
from archive.backtester.engine import Backtester

def run_backtest_analysis():
    print(">>> [系統啟動] 執行「實盤壓力測試版」 (流動性+手續費折讓+滑價)...")
    
    if not os.path.exists('cache_test.pkl'): return print("錯誤：缺少 cache_test.pkl")
    with open('cache_test.pkl', 'rb') as f:
        data_dict = pickle.load(f)
    
    signals = pd.read_csv('oos_test_results.csv')
    signals = signals[signals['is_signal'] == True].copy()
    signals['date'] = pd.to_datetime(signals['date']).dt.normalize()
    
    trades = []
    FIXED_INVESTMENT = 50000
    # 參數設定
    DISCOUNT = 0.6 # 手續費 60 折
    COMMISSION_RATE = 0.001425 * DISCOUNT
    TAX_RATE = 0.003
    MIN_FEE = 20
    SLIPPAGE = 0.0005 # 買進/賣出各 0.05% 滑價，總計 0.1%

    print(f">>> 開始模擬交易 (實盤參數)...")
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
        
        # 欄位偵測
        bbu_cols = [c for c in df_full.columns if 'BBU' in c]
        sma_cols = [c for c in df_full.columns if 'SMA' in c]
        adx_cols = [c for c in df_full.columns if 'ADX' in c]
        if not bbu_cols or not sma_cols or not adx_cols: continue
        bbu, sma_col, adx_col = bbu_cols[0], sma_cols[0], adx_cols[0]
        
        # 1. 趨勢與技術濾網
        if pd.isna(df_full.loc[row['date'], adx_col]) or df_full.loc[row['date'], adx_col] > 30: continue
        if df_full.loc[row['date'], 'Close'] < df_full.loc[row['date'], sma_col]: continue
        if not (df_full.loc[row['date'], 'Close'] > df_full.loc[row['date'], 'Open']): continue
        
        # 2. [新增] 流動性檢查 (Liquidity Check)
        # 假設 DataFrame 包含 'Volume' 欄位
        daily_volume = df_full.loc[row['date'], 'Volume']
        current_price = df_full.loc[row['date'], 'Close']
        # 計算此單佔當日成交量的比例
        shares_to_buy = FIXED_INVESTMENT // current_price
        if (shares_to_buy / daily_volume) > 0.05: continue # 若超過 5% 成交量，放棄交易
        
        try:
            start_loc = df_full.index.get_loc(row['date'])
            buy_price = current_row_price = df_full.iloc[start_loc]['Close']
            shares = shares_to_buy
            
            reason = "timeout"
            exit_price = buy_price
            
            # 持有期 5 天
            for i in range(start_loc + 1, min(start_loc + 6, len(df_full))):
                close_i = df_full.iloc[i]['Close']
                bbu_i = df_full.iloc[i][bbu]
                
                # 計算含滑價的停損與獲利 (停損也需考量滑價)
                profit_pct = (close_i - buy_price) / buy_price
                current_sl = buy_price * 1.025 if profit_pct >= 0.02 else buy_price * 0.93
                
                if close_i >= bbu_i:
                    exit_price = close_i; reason = "take_profit"; break
                elif close_i <= current_sl:
                    exit_price = close_i; reason = "stop_loss"; break
                elif i == start_loc + 5:
                    exit_price = close_i; reason = "timeout"; break
            
            # --- [新增] 真實交易成本計算 ---
            # 買進與賣出滑價後的價格
            buy_cost = (buy_price * (1 + SLIPPAGE)) * shares
            exit_revenue = (exit_price * (1 - SLIPPAGE)) * shares
            
            # 手續費與稅金
            commission = max(MIN_FEE, buy_cost * COMMISSION_RATE) + max(MIN_FEE, exit_revenue * COMMISSION_RATE)
            tax = exit_revenue * TAX_RATE
            
            profit = (exit_revenue - buy_cost) - commission - tax
            trades.append({'ticker': ticker, 'profit': profit, 'reason': reason})
        except: continue

    if not trades: return print(">>> 無有效交易。")
    trade_df = pd.DataFrame(trades)
    
    print("\n" + "="*40)
    print("【實盤壓力測試 績效歸因】")
    print(trade_df.groupby('reason')['profit'].agg(['sum', 'count', 'mean']))
    print(f"總淨損益: {trade_df['profit'].sum():.2f} TWD")
    print("="*40 + "\n")
    plt.show()

if __name__ == "__main__":
    run_backtest_analysis()