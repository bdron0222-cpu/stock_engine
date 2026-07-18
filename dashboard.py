import streamlit as st
import site
import os
import subprocess
import sys

# --- 1. Runtime Install: 確保 pandas-ta 已安裝 ---
def ensure_pandas_ta():
    try:
        import pandas_ta
    except ImportError:
        st.info("偵測到環境缺少 pandas-ta，正在自動安裝中，請稍候...")
        # 安裝相容於 Python 3.10 的版本
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas-ta==0.3.14b"])
        st.success("pandas-ta 已安裝完畢，正在重啟頁面...")
        st.rerun()

ensure_pandas_ta()

# --- 2. 自動修復 pandas-ta 語法錯誤 (Hotfix) ---
def patch_pandas_ta():
    try:
        for path in site.getsitepackages():
            hma_path = os.path.join(path, "pandas_ta", "overlap", "hma.py")
            if os.path.exists(hma_path):
                with open(hma_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 若發現錯誤語法，強制覆寫為正確語法
                if 'hma.name = f' in content and '""' in content:
                    new_content = content.replace('f"HMA{""', "f'HMA{''")
                    with open(hma_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                break
    except Exception as e:
        st.warning(f"Patching failed, but continuing: {e}")

patch_pandas_ta()

# --- 3. 原本的 import 與程式碼 ---
# 注意：這些 import 必須放在安裝與修復之後
import pandas as pd
import json
from datetime import datetime
import filters.market_analyzer
from filters.market_analyzer import analyze_market_regime

# --- 優化提醒機制 ---
DUE_FILE = "optimizer_due_date.json"

def check_optimizer_due():
    """檢查是否超過 90 天未執行優化"""
    if not os.path.exists(DUE_FILE):
        with open(DUE_FILE, "w") as f:
            json.dump({"last_run": datetime.now().strftime("%Y-%m-%d")}, f)
        return False
    
    with open(DUE_FILE, "r") as f:
        data = json.load(f)
        last_run = datetime.strptime(data['last_run'], "%Y-%m-%d")
        
    return (datetime.now() - last_run).days >= 90

def reset_optimizer_date():
    """重置優化日期"""
    with open(DUE_FILE, "w") as f:
        json.dump({"last_run": datetime.now().strftime("%Y-%m-%d")}, f)

st.set_page_config(page_title="盤整策略監控儀表板", layout="wide")
st.title("📈 盤整策略監控儀表板")

# --- 插入維護提醒 ---
if check_optimizer_due():
    st.warning("⚠️ **系統維護提醒：距離上次策略優化已超過 90 天！**")
    st.markdown("""
    請執行以下 **策略維護標準流程** 以維持系統適應性：
    1. **本機執行**：在你的電腦終端機執行 `python optimizer.py`。
    2. **檢查報表**：觀察優化後的績效回測與風控指標 (MDD, Calmar Ratio)。
    3. **參數更新**：確認參數穩定後，手動修改 `main.py` 或 `range_strategy.py` 中的參數設定。
    4. **上傳變更**：執行 `git commit` 並 `git push` 上傳至 GitHub。
    5. **重置提醒**：點擊下方按鈕以重置維護日期。
    """)
    if st.button("我已經執行過維護並更新參數了 (重置提醒)"):
        reset_optimizer_date()
        st.success("提醒已重置！請記得推送到 GitHub 更新線上版本。")
        st.rerun()

# 1. 大盤市場狀態儀表板
st.subheader("🌐 大盤市場狀態監控")
try:
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("市場類型", "盤整盤 (Range-bound)")
    with col2: st.metric("多空方向", "空頭 (Bearish)")
    with col3: st.metric("操作建議", "區間操作")
    st.caption("數據細節：ADX 強度指數 15.34")
except Exception as e:
    st.error(f"大盤監控系統暫時無法顯示")

# 2. 策略操作紀律
with st.expander("📌 每日策略操作紀律 (進出場與風控說明)"):
    st.markdown("""
    ### 🎯 進出場策略
    - 當股價觸及 **布林下軌 (BB Buffer 1.2)** 且 **KD 產生黃金交叉 (KD < 80)** 時買入。
    - 觸及 **布林上軌**，獲利出場。
    - **風控規則**：
        - 若 **獲利 < 2%**：停損設為 **-7%** (成本價 * 0.93)。
        - 若 **獲利 >= 2%**：停損設為 **買入價 * 1.025** (移動停利，鎖定小賺)。
    - 若上述兩者皆未觸發，則在進場後的 **第 5 個交易日收盤** 強制出場。
    """)

# 3. 分類標準定義
with st.expander("📊 分類標準定義"):
    st.markdown("""
    根據股票的波動特性與市場關聯度進行分類：
    - **🛡️ 穩健型**：`Beta < 0.5`。
    - **🔥 積極型**：`Beta > 1.0` 且 `Rho > 0.5`。
    """)

# 4. 載入數據
@st.cache_data(ttl=60)
def load_watchlist(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

df_cons = load_watchlist("watchlist_conservative.csv")
df_aggr = load_watchlist("watchlist_aggressive.csv")
df_noise = load_watchlist("watchlist_noise.csv")

# 5. 顯示表格函數
def display_table(df):
    if not df.empty:
        st.dataframe(df, width=1200)
    else:
        st.info("今日無符合此類型的標的。")

# 6. 分類看板 Tab
tab1, tab2, tab3 = st.tabs(["🛡️ 穩健型", "🔥 積極型", "⚠️ 雜訊過濾"])

with tab1: display_table(df_cons)
with tab2: display_table(df_aggr)
with tab3: display_table(df_noise)

# 7. 側邊欄檢索
st.sidebar.header("🔍 個股詳細檢索")
valid_dfs = [df for df in [df_cons, df_aggr, df_noise] if not df.empty]

if valid_dfs:
    all_stocks = pd.concat(valid_dfs, ignore_index=True).drop_duplicates(subset=['ticker'])
    selected_ticker = st.sidebar.selectbox("搜尋個股", all_stocks['ticker'].unique())
    stock_info = all_stocks[all_stocks['ticker'] == selected_ticker].iloc[0]
    
    st.sidebar.metric("價格", f"{stock_info['price']:.2f}")
    st.sidebar.metric("成交量 (張)", f"{int(stock_info['volume']):,}")
    st.sidebar.metric("Beta", f"{float(stock_info.get('beta', 0)):.2f}")
    st.sidebar.metric("Rho", f"{float(stock_info.get('rho', 0)):.2f}")
else:
    st.sidebar.info("目前無可檢索標的。")