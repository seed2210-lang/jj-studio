import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os

# ==========================================
# 📱 모바일 UI 최적화 설정
# ==========================================
st.set_page_config(page_title="❤무조건잘된다니까❤", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 20px; font-weight: bold; border-radius: 12px; margin-bottom: 10px; }
    .main-title { text-align: center; color: #d4af37; font-size: 26px; font-weight: bold; margin-bottom: 20px; }
    .alert-box { background-color: #ff4b4b; color: white; padding: 20px; border-radius: 12px; text-align: center; font-size: 18px; font-weight: bold; margin-bottom: 15px; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

DATA_FILE = "jj_mobile_account.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 🔐 비밀번호 입장 (6006)
# ==========================================
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<p class='main-title'>🍀오늘도쨔잔!!🍀</p>", unsafe_allow_html=True)
    pw = st.text_input("헤헿", type="password")
    if st.button("입장하기 🚀"):
        if pw == "6006":
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("비밀번호가 틀렸어!")
    st.stop()

if 'my_stocks' not in st.session_state:
    st.session_state.my_stocks = load_data()

# --- 🚨 팔자! 알림 ---
today_str = datetime.now().strftime('%Y-%m-%d')
sell_list = [s['name'] for s in st.session_state.my_stocks if s.get('status') == 'BOUGHT' and s.get('sell_date') <= today_str]
if sell_list:
    for name in sell_list:
        st.markdown(f"<div class='alert-box'>🚨 쩡아! 오늘 '{name}' 무조건 팔자! 💰</div>", unsafe_allow_html=True)

# ==========================================
# 🎯 [방탄 버전] 데이터 로드 엔진
# ==========================================
@st.cache_data(ttl=3600)
def get_all_stocks(): 
    try:
        # 1차 시도: KRX 전체 종목
        return fdr.StockListing('KRX')[['Code', 'Name']].dropna()
    except:
        try:
            # 2차 시도: KOSPI만이라도 시도
            return fdr.StockListing('KOSPI')[['Code', 'Name']].dropna()
        except:
            # 최종 수단: 서버 에러 시 최소한의 샘플 데이터로 앱 유지
            st.warning("⚠️ 주식 서버가 바빠서 리스트를 못 가져왔어. 잠시 후 다시 시도해줘!")
            return pd.DataFrame({'Code': ['005930', '000660', '128820', '403490'], 
                                 'Name': ['삼성전자', 'SK하이닉스', '대성산업', '뉴로메카']})

def analyze_perfect(item):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d'))
        if len(df) < 15: return None
        last = df.iloc[-1]
        curr_price = int(last['Close'])
        vol_avg = df['Volume'].iloc[-10:-1].mean()
        
        # 8시 30분용 정밀 분석
        if last['Volume'] > vol_avg * 2.5 and last['Close'] > last['Open']:
            return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "price": curr_price, "sell_date": today_str}
        
        ma5, ma20 = df['Close'].rolling(5).mean().iloc[-1], df['Close'].rolling(20).mean().iloc[-1]
        if ma5 > ma20 and last['Close'] > ma5:
            sell_d = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            return {"type": "🛡️ 며칠 사자", "name": item['Name'], "code": item['Code'], "price": curr_price, "sell_date": sell_d}
        return None
    except: return None

# ==========================================
# 🖥️ 모바일 UI
# ==========================================
tab1, tab2 = st.tabs(["🔍 종목찾기", "💰 내 장부"])

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="예: 대성, 삼성")
    stocks_df = get_all_stocks()
    if s_word:
        found = stocks_df[stocks_df['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(5).iterrows():
                if st.button(f"🧐 {row['Name']} 분석하기"):
                    res = analyze_perfect({'Code': row['Code'], 'Name': row['Name']})
                    if res:
                        st.success(f"### {res['type']}!\n추천가: {res['price']:,}원 | 매도: {res['sell_date']}")
                        if st.button(f"⭐ {res['name']} 담기"):
                            st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0})
                            save_data(st.session_state.my_stocks); st.rerun()
                    else: st.warning("지금은 때가 아니야!")
        else: st.error("종목을 못 찾겠어!")

with tab2:
    st.subheader("📋 쩡아의 실전 장부")
    st.write("🧐 **살까 말까**")
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "WISH":
            with st.container():
                st.markdown(f"<div class='stock-card'><b>{s['name']}</b> ({s['type']})</div>", unsafe_allow_html=True)
                b_p = st.number_input("매수가", key=f"bp_{i}", value=s['price'])
                if st.button("구매 완료 ✅", key=f"done_{i}"):
                    s['status'] = "BOUGHT"; s['buy_price'] = b_p
                    save_data(st.session_state.my_stocks); st.rerun()
                if st.button("삭제 🗑️", key=f"del_{i}"):
                    st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
    st.divider()
    st.write("💰 **내 지갑**")
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "BOUGHT":
            profit = ((s['price'] - s['buy_price']) / s['buy_price']) * 100
            color = "#ff4b4b" if profit > 0 else "#4b8bff"
            st.markdown(f"<div class='stock-card' style='border-left: 8px solid {color};'><b>{s['name']}</b> | <span style='color:{color}'>{profit:.2f}%</span><br><small>매도일: {s['sell_date']}</small></div>", unsafe_allow_html=True)
            if st.button("팔았다! 💸", key=f"sell_{i}"):
                st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
