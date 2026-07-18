import streamlit as st
import pandas as pd
import os
import filters.market_analyzer
from filters.market_analyzer import analyze_market_regime

st.set_page_config(page_title="盤整策略監控儀表板", layout="wide")

st.title("📈 盤整策略監控儀表板")

# 1. 大盤市場狀態儀表板 (深度除錯版)
st.subheader("🌐 大盤市場狀態監控")

# --- 深度除錯：確認模組來源 ---
st.write(f"DEBUG: 模組路徑: {filters.market_analyzer.__file__}")
# ------------------------------

try:
    market_info = analyze_market_regime(['^TWII'])
    
    # 檢查是否為空字典或錯誤格式
    if not market_info or 'regime' not in market_info:
        st.error(f"分析函數回傳了意外的格式: {market_info}")
    else:
        # 強制將 numpy 數值轉換為標準 Python 類型
        regime = str(market_info.get('regime', '未知'))
        direction = str(market_info.get('direction', '未知'))
        action = str(market_info.get('action', '未知'))
        adx = float(market_info.get('adx', 0))
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("市場類型", regime)
        with col2: st.metric("多空方向", direction)
        with col3: st.metric("操作建議", action)
        
        st.caption(f"數據細節：ADX 強度指數 {adx:.2f}")

except Exception as e:
    # 顯示完整的錯誤堆疊 (StackTrace)
    st.error("系統發生錯誤，錯誤訊息如下：")
    st.exception(e) 

# 2. 策略操作規則說明
with st.expander("📌 每日策略操作紀律 (進出場與風控說明)"):
    st.markdown("""
    ### 🎯 進場邏輯
    - 嚴格訊號：觸及 **布林下軌 (BB Buffer 1.2)** 且 **KD 產生黃金交叉 (KD < 80)**。
    - 潛力觀察：查看「潛力觀察」頁籤，找出 **BB 距離 (bb_dist)** 最接近 0 或負值的標的。

    ### 🏁 出場與風控規則
    1. **獲利出場**：觸及布林上軌。
    2. **停損/停利機制**：獲利 < 2% 時設 -7%；獲利 >= 2% 時設為成本價 * 1.025 (移動停利)。
    3. **時間出場**：第 5 個交易日收盤強制出場。
    """)

# 3. 載入數據
@st.cache_data(ttl=60)
def load_watchlist(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

df_cons = load_watchlist("watchlist_conservative.csv")
df_aggr = load_watchlist("watchlist_aggressive.csv")
df_noise = load_watchlist("watchlist_noise.csv")
df_all = load_watchlist("all_candidates_proximity.csv")

# 4. 顯示表格函數
def display_table(df, key):
    if not df.empty and 'bb_dist' in df.columns:
        df_sorted = df.sort_values(by='bb_dist', ascending=True)
        cols = [c for c in ['buy_signal', 'bb_dist', 'ticker', 'price', 'beta', 'rho'] if c in df_sorted.columns]
        cols += [c for c in df_sorted.columns if c not in cols]
        st.dataframe(df_sorted[cols], width=1200)
    elif not df.empty:
        st.dataframe(df, width=1200)
    else:
        st.info("今日無符合此類型的標的。")

# 5. 分類看板 Tab
tab1, tab2, tab3, tab4 = st.tabs(["🛡️ 穩健型", "🔥 積極型", "⚠️ 雜訊過濾", "🔭 潛力觀察 (All)"])

with tab1: display_table(df_cons, "cons")
with tab2: display_table(df_aggr, "aggr")
with tab3: display_table(df_noise, "noise")
with tab4: display_table(df_all, "all")

# 6. 側邊欄檢索
st.sidebar.header("🔍 個股詳細檢索")
valid_dfs = [df for df in [df_cons, df_aggr, df_noise, df_all] if not df.empty]
if valid_dfs:
    all_stocks = pd.concat(valid_dfs, ignore_index=True).drop_duplicates(subset=['ticker'])
    selected_ticker = st.sidebar.selectbox("搜尋個股", all_stocks['ticker'].unique())
    stock_info = all_stocks[all_stocks['ticker'] == selected_ticker].iloc[0]
    st.sidebar.metric("價格", f"{stock_info['price']:.2f}")
    st.sidebar.metric("BB 距離", f"{float(stock_info.get('bb_dist', 0)):.4f}")
    st.sidebar.metric("Beta", f"{float(stock_info.get('beta', 0)):.2f}")
    st.sidebar.metric("Rho", f"{float(stock_info.get('rho', 0)):.2f}")
else:
    st.sidebar.info("目前無可檢索標的。")