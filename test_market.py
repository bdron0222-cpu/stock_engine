import sys
import os

# 確保系統能找到 filters 資料夾
sys.path.append(os.getcwd())

from filters.market_analyzer import analyze_market_regime

print(">>> [測試開始] 正在執行市場分析...")
try:
    result = analyze_market_regime(['^TWII'])
    print(f">>> [測試結果] 成功取得資料: {result}")
except Exception as e:
    print(f">>> [測試失敗] 發生錯誤: {e}")
    # 這是為了讓我們看到更詳細的錯誤堆疊
    import traceback
    traceback.print_exc()