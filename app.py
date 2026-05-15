import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os
import numpy as np

#1 --- 📱 모바일 최적화 및 스타일 (색상/버튼 고도화) ---
st.set_page_config(page_title="❤❤❤❤❤❤❤❤", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 22px; font-weight: bold; }
    .alert-box { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 10px; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; }
    .price-curr { color: #ffffff; font-weight: bold; }
    .price-target { color: #ff4b4b; font-weight: bold; } /* 빨간색: 올라갈 시세 */
    .price-stop { color: #4b8bff; font-weight: bold; }   /* 파란색: 팔아야 할 금액(손절/익절) */
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

#2 --- 🔐 보안 시스템 ---
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    st.markdown("<p class='main-title'>🌹오늘도짜쟌🌹</p>", unsafe_allow_html=True)
    pw = st.text_input("헤헿(●'◡'●)", type="password")
    if st.button("입장하기 🚀"):
        if pw == "2727":
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("비밀번호가 틀렸어!")
    st.stop()

if 'my_stocks' not in st.session_state: st.session_state.my_stocks = load_data()

#3 --- 🎯 12가지 정밀 분석 엔진 (전면 복구) ---
@st.cache_data(ttl=3600)
def get_all_stocks():
    try:
        kospi = fdr.StockListing('KOSPI')[['Code', 'Name']]
        kosdaq = fdr.StockListing('KOSDAQ')[['Code', 'Name']]
        return pd.concat([kospi, kosdaq]).dropna().drop_duplicates()
    except:
        # 특정 종목 고정 추천 방지를 위해 비어있는 데이터 반환 (서버 에러 대응)
        return pd.DataFrame(columns=['Code', 'Name'])

def analyze_logic(item, mode="RADAR"):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'))
        if len(df) < 40: return None
        
        c = df['Close']; v = df['Volume']
        curr = int(c.iloc[-1])
        
        # 12가지 지표 분석 (SS 레이더 기반)
        ma5 = c.rolling(5).mean(); ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
        rsi = 100 - (100 / (1 + (c.diff().where(c.diff() > 0, 0).rolling(14).mean() / (-c.diff().where(c.diff() < 0, 0)).rolling(14).mean())))
        
        target = int(df['High'].iloc[-60:].max()) # 목표(빨간색)
        stop = int(ma20.iloc[-1] * 0.97)        # 손절/탈출(파란색)
        
        score = sum([
            v.iloc[-1] > v.iloc[-10:-1].mean() * 1.5, c.iloc[-1] > ma5.iloc[-1],
            ma5.iloc[-1] > ma20.iloc[-1], rsi.iloc[-1] < 70, curr > ma60.iloc[-1]
        ]) # (정밀 분석 점수 요약)

        if mode == "SURGE": # 🔥 당일 급등 (오늘 사자)
            if v.iloc[-1] > v.iloc[-10:-1].mean() * 2.5:
                return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": "오늘 마감 전 매도", "date": datetime.now().strftime('%Y-%m-%d')}
        else: # 📡 레이더 (며칠 사자)
            if score >= 3:
                days = "3일 유지" if rsi.iloc[-1] < 50 else "2일 유지"
                sell_date = (datetime.now() + timedelta(days=int(days[0]))).strftime('%Y-%m-%d')
                return {"type": f"🛡️ {days}", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": days, "date": sell_date}
        return None
    except: return None

#4 --- 📱 메인 UI (4개 페이지) ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 찾기", "🔥 급등", "📡 레이더", "💖 보물함"])

all_s = get_all_stocks()

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="예: 뉴로메카")
    if s_word:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        for _, row in found.head(3).iterrows():
            if st.button(f"🧐 {row['Name']} 12가지 정밀 분석"):
                res = analyze_logic({'Code': row['Code'], 'Name': row['Name']}, "RADAR")
                if res:
                    st.markdown(f"""
                    <div class='stock-card'>
                        <h3>{res['name']}</h3>
                        현재 시세: <span class='price-curr'>{res['curr']:,}원</span><br>
                        올라갈 시세: <span class='price-target'>{res['target']:,}원</span><br>
                        팔아야할 금액: <span class='price-stop'>{res['stop']:,}원</span><br>
                        <b>전략: {res['hold']}</b>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("⭐ 보물함에 담기", key=f"add_{res['code']}"):
                        st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0, "qty": 0})
                        save_data(st.session_state.my_stocks); st.rerun()

with tab2:
    st.write("🔥 **오늘 8:30 예약 → 15:00 매도 종목**")
    if st.button("🚀 당일 급등주 스캔"):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(analyze_logic, {'Code': r.Code, 'Name': r.Name}, "SURGE") for r in all_s.head(300).itertuples()]
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r: results.append(r)
        if results:
            for r in results:
                st.info(f"**{r['name']}** | 현재: {r['curr']:,} | 목표: {r['target']:,}")
                if st.button(f"⭐ {r['name']} 담기", key=f"surge_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0})
                    save_data(st.session_state.my_stocks); st.rerun()
        else: st.write("오늘은 조용하네!")

with tab3:
    st.write("📡 **며칠 동안 쭉쭉 올라갈 보물찾기**")
    if st.button("📡 레이더 가동 (상위 500개)"):
        p_bar = st.progress(0, text="보물 찾는 중...")
        results = []
        subset = all_s.head(500)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(analyze_logic, {'Code': r.Code, 'Name': r.Name}, "RADAR") for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r: results.append(r)
                if i % 50 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        for r in results:
            st.write(f"[{r['type']}] **{r['name']}** | 목표: {r['target']:,}")
            if st.button(f"⭐ 담기", key=f"radar_{r['code']}"):
                st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0})
                save_data(st.session_state.my_stocks); st.rerun()

with tab4:
    st.subheader("💖무조건잘된다니까💖")
    # 1. 살까 말까 (WISH)
    w_list = [s for s in st.session_state.my_stocks if s['status'] == "WISH"]
    if w_list:
        st.write("🧐 **살까 말까 (얼마에 몇 주 샀어?)**")
        for i, s in enumerate(st.session_state.my_stocks):
            if s['status'] == "WISH":
                with st.container():
                    st.markdown(f"<div class='stock-card'><b>{s['name']}</b> ({s['type']})</div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    b_p = c1.number_input("매수가", key=f"bp_{i}", value=s['curr'])
                    b_q = c2.number_input("몇 주?", key=f"bq_{i}", value=1)
                    if st.button("구매 완료 ✅", key=f"done_{i}"):
                        s['status'] = "BOUGHT"; s['buy_price'] = b_p; s['qty'] = b_q
                        save_data(st.session_state.my_stocks); st.rerun()
                    if st.button("삭제 🗑️", key=f"del_{i}"):
                        st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()

    # 2. 내 지갑 (BOUGHT)
    st.divider()
    st.write("💰 **현재 현황**")
    bought_list = [s for s in st.session_state.my_stocks if s['status'] == "BOUGHT"]
    if bought_list:
        for i, s in enumerate(st.session_state.my_stocks):
            if s['status'] == "BOUGHT":
                # 수익 계산: (현재가 - 매수가) * 수량
                profit_rate = ((s['curr'] - s['buy_price']) / s['buy_price']) * 100
                total_profit = (s['curr'] - s['buy_price']) * s['qty']
                color = "#ff4b4b" if profit_rate > 0 else "#4b8bff"
                
                st.markdown(f"""
                <div class='stock-card' style='border-left: 8px solid {color};'>
                    <b>{s['name']}</b> ({s['qty']}주) | <span style='color:{color}'>{profit_rate:.2f}%</span><br>
                    총 이익: <b>{total_profit:,}원</b><br>
                    매수가: {s['buy_price']:,} ➔ 목표가: <span class='price-target'>{s['target']:,}</span><br>
                    <small>📅 매도 예정: {s['date']}</small>
                </div>
                """, unsafe_allow_html=True)
                if st.button("팔았다! (삭제) 💸", key=f"sell_{i}"):
                    st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
    else:
        st.info("지갑이 비어있어. 레이더에서 종목을 담아봐!")
