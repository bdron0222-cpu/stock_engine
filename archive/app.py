import streamlit as st
import pandas as pd
import os
from filters.market_analyzer import analyze_market_regime

st.set_page_config(page_title="盤整策略監控儀表板", layout="wide")

st.title("📈 盤整策略監控儀表板")

# 1. 大盤市場狀態儀表板 (防禦性寫法)
st.subheader("🌐 大盤市場狀態監控")
try:
    # 呼叫分析函數
    market_info = analyze_market_regime(['^TWII'])
    
    # 使用 .get() 來防禦性讀取，如果找不到 key 就回傳預設值
    regime = market_info.get('regime', '未知')
    direction = market_info.get('direction', '未知')
    action = market_info.get('action', '未知')
    adx = market_info.get('adx', 0)
    
    # 使用三欄位排版
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("市場類型", regime)
    with col2:
        st.metric("多空方向", direction)
    with col3:
        st.metric("操作建議", action)
        
    st.caption(f"數據細節：ADX 強度指數 {adx}")
    
except Exception as e:
    st.warning(f"大盤監控系統暫時無法顯示: {e}")

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

# 3. 載入數據 (加入 ttl=60，每 60 秒自動更新)
@st.cache_data(ttl=60)
def load_watchlist(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

df_cons = load_watchlist("watchlist_conservative.csv")
df_aggr = load_watchlist("watchlist_aggressive.csv")
df_noise = load_watchlist("watchlist_noise.csv")
df_all = load_watchlist("all_candidates_proximity.csv")

# 4. 顯示表格函數 (自動排序)
def display_table(df, key):
    if not df.empty and 'bb_dist' in df.columns:
        # 自動按 bb_dist 升序
        df_sorted = df.sort_values(by='bb_dist', ascending=True)
        # 確保 buy_signal 在前面
        cols = [c for c in ['buy_signal', 'bb_dist', 'ticker', 'price', 'beta', 'rho'] if c in df_sorted.columns]
        cols += [c for c in df_sorted.columns if c not in cols]
        st.dataframe(df_sorted[cols], use_container_width=True)
    elif not df.empty:
        st.dataframe(df, use_container_width=True)
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
all_stocks = pd.concat([df_cons, df_aggr, df_noise, df_all], ignore_index=True).drop_duplicates(subset=['ticker'])
if not all_stocks.empty:
    selected_ticker = st.sidebar.selectbox("搜尋個股", all_stocks['ticker'].unique())
    stock_info = all_stocks[all_stocks['ticker'] == selected_ticker].iloc[0]
    st.sidebar.metric("價格", f"{stock_info['price']:.2f}")
    st.sidebar.metric("BB 距離", f"{stock_info.get('bb_dist', 0):.4f}")
    st.sidebar.metric("Beta", stock_info['beta'])
    st.sidebar.metric("Rho", stock_info['rho'])