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
st.set_page_config(page_title="💰 JJ-Money Mobile", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 20px; font-weight: bold; border-radius: 12px; margin-bottom: 10px; }
    .main-title { text-align: center; color: #d4af37; font-size: 26px; font-weight: bold; margin-bottom: 20px; }
    .alert-box { background-color: #ff4b4b; color: white; padding: 20px; border-radius: 12px; text-align: center; font-size: 18px; font-weight: bold; margin-bottom: 15px; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px; }
    .price-text { font-size: 20px; color: #ffffff; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 데이터 저장 (클라우드용 파일명)
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
# 🔐 비밀번호 전용 입장 (ID 필요 없음!)
# ==========================================
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<p class='main-title'>🍀오늘도쨔잔!!🍀</p>", unsafe_allow_html=True)
    pw = st.text_input("헤헿", type="password")
    if st.button("입장하기 🚀"):
        if pw == "6006":
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("다시다시")
    st.stop()

# --- 데이터 불러오기 ---
if 'my_stocks' not in st.session_state:
    st.session_state.my_stocks = load_data()

# ==========================================
# 🚨 [팔자!] 폰 상단 빨간 알림
# ==========================================
today_str = datetime.now().strftime('%Y-%m-%d')
sell_list = [s['name'] for s in st.session_state.my_stocks if s.get('status') == 'BOUGHT' and s.get('sell_date') <= today_str]

if sell_list:
    for name in sell_list:
        st.markdown(f"<div class='alert-box'>🚨 오늘 '{name}' 무조건 팔자! 💰</div>", unsafe_allow_html=True)

# ==========================================
# 🎯 오점 없는 정밀 분석 엔진
# ==========================================
@st.cache_data(ttl=3600)
def get_all_stocks(): 
    return fdr.StockListing('KRX')[['Code', 'Name']].dropna()

def analyze_perfect(item):
    try:
        # 8시 30분에 어제까지의 기세를 분석함
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d'))
        if len(df) < 20: return None
        
        last = df.iloc[-1]
        curr_price = int(last['Close'])
        vol_avg = df['Volume'].iloc[-10:-1].mean()
        
        # 1. 🔥 오늘 사자 (오늘 당장 튈 놈 - 거래량 2.5배 폭발)
        if last['Volume'] > vol_avg * 2.5 and last['Close'] > last['Open']:
            return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "price": curr_price, "sell_date": today_str}
        
        # 2. 🛡️ 며칠 후 사자 (안전 바닥 - 정배열 초기)
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        if ma5 > ma20 and last['Close'] > ma5:
            sell_d = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            return {"type": "🛡️ 며칠 후 사자", "name": item['Name'], "code": item['Code'], "price": curr_price, "sell_date": sell_d}
            
        return None
    except: return None

# ==========================================
# 🖥️ 모바일 UI (탭 구조)
# ==========================================
tab1, tab2 = st.tabs(["🔍 종목찾기", "💰 내 장부"])

with tab1:
    s_word = st.text_input("종목명 (한 글자도 OK!)", placeholder="예: 대성, 삼성")
    all_stocks = get_all_stocks()
    if s_word:
        found = all_stocks[all_stocks['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(5).iterrows():
                if st.button(f"🧐 {row['Name']} 분석하기"):
                    res = analyze_perfect({'Code': row['Code'], 'Name': row['Name']})
                    if res:
                        st.success(f"### {res['type']}!\n추천가: {res['price']:,}원 | 매도: {res['sell_date']}")
                        if st.button(f"⭐ {res['name']} 보물함 담기"):
                            st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0})
                            save_data(st.session_state.my_stocks)
                            st.success("보물함에 잘 넣었어! '내 장부'에서 확인해!")
                    else: st.warning("지금은 사기에 애매해. 다른 종목을 보자!")
        else: st.error("그런 이름의 종목은 없어!")

with tab2:
    st.subheader("📋 쩡아의 실전 매매 장부")
    
    # 1. 예약 대기 (WISH)
    st.markdown("---")
    st.write("🧐 **살까 말까 (예약 대기)**")
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "WISH":
            with st.container():
                st.markdown(f"<div class='stock-card'><b>{s['name']}</b> ({s['type']})<br><small>추천: {s['price']:,}원 | 매도: {s['sell_date']}</small></div>", unsafe_allow_html=True)
                b_p = st.number_input("실제 체결가", key=f"bp_{i}", value=s['price'])
                if st.button("구매 완료 ✅", key=f"done_{i}"):
                    s['status'] = "BOUGHT"; s['buy_price'] = b_p
                    save_data(st.session_state.my_stocks); st.rerun()
                if st.button("삭제 🗑️", key=f"del_w_{i}"):
                    st.session_state.my_stocks.pop(i)
                    save_data(st.session_state.my_stocks); st.rerun()

    # 2. 보유 종목 (BOUGHT)
    st.markdown("---")
    st.write("💰 **내 지갑 (보유 중)**")
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "BOUGHT":
            profit = ((s['price'] - s['buy_price']) / s['buy_price']) * 100
            color = "#ff4b4b" if profit > 0 else "#4b8bff"
            st.markdown(f"""
                <div class='stock-card' style='border-left: 8px solid {color};'>
                    <span style='font-size:18px;'><b>{s['name']}</b></span> | 
                    수익률: <span style='color:{color}'><b>{profit:.2f}%</b></span><br>
                    <small>매수가: {s['buy_price']:,} | 매도 예정: {s['sell_date']}</small>
                </div>
            """, unsafe_allow_html=True)
            if st.button("팔았다! (삭제) 💸", key=f"sell_{i}"):
                st.session_state.my_stocks.pop(i)
                save_data(st.session_state.my_stocks); st.rerun()
