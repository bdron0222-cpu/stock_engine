# backtester/engine.py
import pandas as pd

class Backtester:
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital

    def calculate_equity_curve(self, data_dict, trade_df):
        """
        計算資金曲線
        :param data_dict: 包含所有股票歷史數據的字典
        :param trade_df: 包含所有交易紀錄的 DataFrame
        """
        equity = [self.initial_capital]
        current_capital = self.initial_capital
        
        # 遍歷每一筆交易
        # 使用 iterrows 來安全地讀取每一筆交易紀錄
        for _, trade in trade_df.iterrows():
            # 使用 .get() 方法，這比直接使用 trade['key'] 更安全
            # 如果欄位不存在，會預設回傳 0，避免 KeyError
            profit = trade.get('profit', 0)
            
            # 更新資金
            current_capital += profit
            equity.append(current_capital)
            
        return equity

    def get_summary(self, trade_df):
        """
        簡單的統計功能 (預留給未來擴充)
        """
        total_profit = trade_df['profit'].sum()
        return {"total_profit": total_profit}