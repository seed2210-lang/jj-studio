import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os

# --- 📱 모바일 최적화 및 스타일 ---
st.set_page_config(page_title="❤❤❤❤❤❤❤", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 18px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 24px; font-weight: bold; }
    .alert-box { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 10px; }
    .stock-card { background: #1c2128; padding: 12px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 10px; }
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

# --- 🔐 비번 6006 ---
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    st.markdown("<p class='main-title'>❤오늘도짜쟌❤</p>", unsafe_allow_html=True)
    pw = st.text_input("헤헿", type="password")
    if st.button("입장하기 🚀"):
        if pw == "2727":
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("비밀번호가 틀렸어!")
    st.stop()

if 'my_stocks' not in st.session_state: st.session_state.my_stocks = load_data()

# --- 🚨 팔자 알림 ---
today_str = datetime.now().strftime('%Y-%m-%d')
sell_list = [s['name'] for s in st.session_state.my_stocks if s.get('status') == 'BOUGHT' and s.get('sell_date') <= today_str]
if sell_list:
    for name in sell_list:
        st.markdown(f"<div class='alert-box'>🚨 오늘 '{name}' 팔자! 💰</div>", unsafe_allow_html=True)

# --- 🎯 [우회 버전] 전 종목 로드 엔진 ---
@st.cache_data(ttl=3600)
def get_all_stocks(): 
    try:
        # KRX 대신 더 안정적인 네이버 금융 리스트 우회 (KOSPI/KOSDAQ 합체)
        kospi = fdr.StockListing('KOSPI')[['Code', 'Name']]
        kosdaq = fdr.StockListing('KOSDAQ')[['Code', 'Name']]
        return pd.concat([kospi, kosdaq]).dropna().drop_duplicates()
    except:
        # 마지막 수단: 직접 종목 데이터를 요청해서라도 앱 유지
        return fdr.StockListing('KRX')[['Code', 'Name']].dropna()

def analyze_v2(item):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d'))
        if len(df) < 15: return None
        last = df.iloc[-1]
        vol_avg = df['Volume'].iloc[-10:-1].mean()
        # 🔥 오늘 사자: 전일 대비 거래량 2.5배 폭발 + 양봉
        if last['Volume'] > vol_avg * 2.5 and last['Close'] > last['Open']:
            return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "price": int(last['Close']), "sell_date": today_str}
        # 🛡️ 며칠 사자: 20일선 위 + 정배열 초기
        elif last['Close'] > df['Close'].rolling(20).mean().iloc[-1]:
            sell_d = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            return {"type": "🛡️ 며칠 사자", "name": item['Name'], "code": item['Code'], "price": int(last['Close']), "sell_date": sell_d}
    except: return None

# --- 📱 메인 UI ---
tab1, tab2, tab3 = st.tabs(["🔍 찾기", "📡 레이더", "💰 장부"])

with tab1:
    s_word = st.text_input("종목명 (대성, 삼성 등)", placeholder="여기에 입력!")
    all_s = get_all_stocks()
    if s_word:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(5).iterrows():
                if st.button(f"🧐 {row['Name']} 분석", key=f"s_{row['Code']}"):
                    res = analyze_v2({'Code': row['Code'], 'Name': row['Name']})
                    if res:
                        st.success(f"**{res['type']}**\n{res['price']:,}원")
                        if st.button(f"⭐ {res['name']} 담기", key=f"add_{res['code']}"):
                            st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0})
                            save_data(st.session_state.my_stocks); st.toast(f"{res['name']} 담기 완료!"); st.rerun()
                    else: st.warning("지금은 때가 아니야!")
        else: st.error("종목을 못 찾겠어!")

with tab2:
    st.write("📡 **실시간 보물찾기 (상위 500개)**")
    if st.button("🚀 수익 날 종목 다 찾아줘!"):
        p_bar = st.progress(0, text="레이더 가동 중... 위이잉")
        results = []
        subset = all_s.head(500) # 시총 상위 500개 우선 스캔
        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
            futures = [ex.submit(analyze_v2, {'Code': r.Code, 'Name': r.Name}) for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r: results.append(r)
                if i % 50 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        if results:
            for r in results:
                with st.container():
                    st.write(f"[{r['type']}] **{r['name']}** ({r['price']:,}원)")
                    if st.button(f"⭐ 담기", key=f"r_{r['code']}"):
                        st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0})
                        save_data(st.session_state.my_stocks); st.rerun()
        else: st.info("지금 레이더에 걸린 종목이 없어!")

with tab3:
    st.subheader("💖무조건잘된다니까💖")
    wishes = [s for s in st.session_state.my_stocks if s['status'] == "WISH"]
    if wishes:
        st.write("🧐 **살까 말까 (예약대기)**")
        for i, s in enumerate(st.session_state.my_stocks):
            if s['status'] == "WISH":
                with st.container():
                    st.markdown(f"<div class='stock-card'><b>{s['name']}</b> ({s['type']})</div>", unsafe_red_html=True)
                    b_p = st.number_input("매수가", key=f"bp_{i}", value=s['price'])
                    if st.button("구매 완료 ✅", key=f"done_{i}"):
                        s['status'] = "BOUGHT"; s['buy_price'] = b_p
                        save_data(st.session_state.my_stocks); st.rerun()
                    if st.button("삭제 🗑️", key=f"del_{i}"):
                        st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
    st.divider()
    st.write("💰 **내 지갑 (보유중)**")
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "BOUGHT":
            profit = ((s['price'] - s['buy_price']) / s['buy_price']) * 100
            color = "#ff4b4b" if profit > 0 else "#4b8bff"
            st.markdown(f"<div class='stock-card' style='border-left: 8px solid {color};'><b>{s['name']}</b> | <span style='color:{color}'>{profit:.2f}%</span></div>", unsafe_allow_html=True)
            if st.button("팔았다! 💸", key=f"sell_{i}"):
                st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
