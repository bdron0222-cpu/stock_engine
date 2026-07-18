import requests
import pandas as pd
import io
import re

def fetch_market_list(output_file='stocks_list.csv'):
    print(">>> [系統] 正在抓取全市場資料 (上市/上櫃)...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    targets = [
        {"url": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "suffix": ".TW"},
        {"url": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", "suffix": ".TWO"}
    ]
    
    all_tickers = []
    
    for target in targets:
        url = target['url']
        suffix = target['suffix']
        print(f">>> 正在讀取: {url} ({suffix})")
        
        try:
            r = requests.get(url, headers=headers)
            dfs = pd.read_html(io.StringIO(r.text))
            df = dfs[0]
            column_name = df.columns[0]
            
            for val in df[column_name]:
                if isinstance(val, str):
                    parts = re.split(r'\s+', val.strip())
                    if len(parts) >= 1:
                        code = parts[0]
                        # 4位數、純數字、非 00 開頭 (過濾ETF)
                        if len(code) == 4 and code.isdigit() and not code.startswith('00'):
                            all_tickers.append(f"{code}{suffix}")
                            
        except Exception as e:
            print(f">>> [錯誤] 解析網址 {url} 失敗: {e}")

    # 存檔，強制使用 'ticker' 作為標題
    pd.DataFrame({'ticker': all_tickers}).to_csv(output_file, index=False)
    print(f">>> [系統] 成功！共寫入 {len(all_tickers)} 檔股票至 {output_file}。")

if __name__ == "__main__":
    fetch_market_list()