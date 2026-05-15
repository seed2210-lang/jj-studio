import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os
import numpy as np

#1 --- 📱 모바일 최적화 및 스타일 (색상/가독성 극대화) ---
st.set_page_config(page_title="❤❤❤❤❤❤❤❤", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 24px; font-weight: bold; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; }
    .score-badge { background: #d4af37; color: black; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .price-target { color: #ff4b4b; font-weight: bold; } /* 빨간색: 목표 */
    .price-stop { color: #4b8bff; font-weight: bold; }   /* 파란색: 손절 */
    </style>
    """, unsafe_allow_html=True)

DATA_FILE = "jj_mobile_v3.json"

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
    pw = st.text_input("비밀번호(헤헿)", type="password")
    if st.button("입장하기 🚀"):
        if pw == "2727":
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("비밀번호가 틀렸어!")
    st.stop()

if 'my_stocks' not in st.session_state: st.session_state.my_stocks = load_data()

#3 --- 🚨 팔자 알림 ---
today_str = datetime.now().strftime('%Y-%m-%d')
sell_list = [s['name'] for s in st.session_state.my_stocks if s.get('status') == 'BOUGHT' and s.get('sell_date') <= today_str]
if sell_list:
    for name in sell_list:
        st.markdown(f"<div style='background:#ff4b4b; color:white; padding:10px; border-radius:10px; text-align:center; margin-bottom:10px;'>🚨 오늘 '{name}' 무조건 팔자! 💰</div>", unsafe_allow_html=True)

#4 --- 🎯 12가지 정밀 분석 엔진 ---
@st.cache_data(ttl=3600)
def get_all_stocks():
    try:
        df1 = fdr.StockListing('KOSPI')[['Code', 'Name']]
        df2 = fdr.StockListing('KOSDAQ')[['Code', 'Name']]
        return pd.concat([df1, df2]).dropna().drop_duplicates()
    except:
        return pd.DataFrame(columns=['Code', 'Name'])

def analyze_12_points(item, mode="RADAR"):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'))
        if len(df) < 40: return None
        
        c = df['Close']; v = df['Volume']; h = df['High']; l = df['Low']
        curr = int(c.iloc[-1])
        
        # --- 12가지 지표 계산 ---
        ma5 = c.rolling(5).mean(); ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
        rsi = 100 - (100 / (1 + (c.diff().where(c.diff() > 0, 0).rolling(14).mean() / (-c.diff().where(c.diff() < 0, 0)).rolling(14).mean()).iloc[-1]))
        obv = (np.sign(c.diff()) * v).fillna(0).cumsum().iloc[-1]
        vol_avg = v.iloc[-10:-1].mean()
        
        # 12가지 체크리스트
        checks = [
            v.iloc[-1] > vol_avg * 1.5,        # 1. 거래량 급증
            c.iloc[-1] > ma5.iloc[-1],         # 2. 5일선 위
            ma5.iloc[-1] > ma20.iloc[-1],      # 3. 단기 정배열
            ma20.iloc[-1] > ma60.iloc[-1],     # 4. 중기 정배열 초기
            30 < rsi < 70,                     # 5. RSI 안정권
            curr < l.iloc[-20:].min() * 1.15,  # 6. 바닥권 이격
            c.iloc[-1] > c.iloc[-2],           # 7. 전일 대비 상승
            obv > (np.sign(c.diff()) * v).fillna(0).cumsum().iloc[-5], # 8. 매집 확인
            (h.iloc[-1] - c.iloc[-1]) < (c.iloc[-1] - l.iloc[-1]), # 9. 윗꼬리 짧음
            curr > ma20.iloc[-1],              # 10. 20일선 지지
            (h.iloc[-20:].max() - curr)/curr > 0.1, # 11. 상승 여력 10% 이상
            v.iloc[-1] > v.iloc[-2]            # 12. 거래량 점증
        ]
        score = sum(checks)
        
        target = int(h.iloc[-60:].max() if h.iloc[-60:].max() > curr else curr * 1.2)
        stop = int(ma20.iloc[-1] * 0.96)
        
        if mode == "SURGE": # 급등 (오늘 사자)
            if checks[0] and checks[8]: # 거래량 폭발 + 양봉 힘
                return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": "오늘 마감 전", "date": today_str, "score": score}
        else: # 레이더 (며칠 사자)
            if score >= 7:
                days = 3 if rsi < 50 else 2
                sell_d = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
                return {"type": f"🛡️ {days}일 유지", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": f"{days}일", "date": sell_d, "score": score}
        return None
    except: return None

#5 --- 📱 메인 UI (찾기, 급등, 레이더, 장부) ---
all_s = get_all_stocks()
tab1, tab2, tab3, tab4 = st.tabs(["🔍 찾기", "🔥 급등", "📡 레이더", "⭐보물함"])

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="공부할 종목 입력")
    if s_word:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(3).iterrows():
                if st.button(f"🧐 {row['Name']} 12지표 분석"):
                    res = analyze_12_points({'Code': row['Code'], 'Name': row['Name']}, "RADAR")
                    if res:
                        st.markdown(f"""
                        <div class='stock-card'>
                            <b>{res['name']}</b> <span class='score-badge'>12점 중 {res['score']}점</span><br>
                            현재가: {res['curr']:,}원<br>
                            올라갈 시세(빨강): <span class='price-target'>{res['target']:,}원</span><br>
                            팔아야할 금액(파랑): <span class='price-stop'>{res['stop']:,}원</span><br>
                            분석 결과: <b>{res['hold']} 보유 추천</b>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"⭐ {res['name']} 보물함 담기", key=f"add_{res['code']}"):
                            st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0, "qty": 0})
                            save_data(st.session_state.my_stocks); st.rerun()
                    else: st.warning("분석 결과, 현재는 추천 점수가 낮아!")
        else: st.error("종목을 못 찾겠어. 정확히 입력해줘!")

with tab2:
    st.write("🔥 **8:30 예약 → 오늘 3:00 매도 (당일 승부)**")
    if st.button("🚀 급등주 스캔"):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(analyze_12_points, {'Code': r.Code, 'Name': r.Name}, "SURGE") for r in all_s.head(200).itertuples()]
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r: results.append(r)
        if results:
            for r in results:
                st.success(f"**{r['name']}** | 현재: {r['curr']:,} | 목표: {r['target']:,}")
                if st.button(f"⭐ {r['name']} 담기", key=f"surge_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0})
                    save_data(st.session_state.my_stocks); st.rerun()
        else: st.info("조건에 맞는 급등주가 없어!")

with tab3:
    st.write("📡 **2~4일간 추세가 살아날 종목 (레이더)**")
    if st.button("📡 레이더 가동"):
        p_bar = st.progress(0, text="12지표 정밀 스캔 중...")
        results = []
        subset = all_s.head(300)
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(analyze_12_points, {'Code': r.Code, 'Name': r.Name}, "RADAR") for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r: results.append(r)
                if i % 30 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        for r in results:
            st.write(f"[{r['type']}] **{r['name']}** | {r['score']}점")
            if st.button(f"⭐ {r['name']} 담기", key=f"radar_{r['code']}"):
                st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0})
                save_data(st.session_state.my_stocks); st.rerun()

with tab4:
    st.subheader("💖무조건잘된다니까💖")
    # 1. 살까 말까 (WISH)
    wishes = [s for s in st.session_state.my_stocks if s['status'] == "WISH"]
    if wishes:
        st.write("🧐 **살까 말까 (매수 정보 입력!)**")
        for i, s in enumerate(st.session_state.my_stocks):
            if s['status'] == "WISH":
                with st.container():
                    st.markdown(f"<div class='stock-card'><b>{s['name']}</b> ({s['type']})</div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    b_p = c1.number_input("매수가", key=f"bp_{i}", value=s['curr'])
                    b_q = c2.number_input("수량(주)", key=f"bq_{i}", value=1)
                    if st.button("구매 완료 ✅", key=f"done_{i}"):
                        s['status'] = "BOUGHT"; s['buy_price'] = b_p; s['qty'] = b_q
                        save_data(st.session_state.my_stocks); st.rerun()
                    if st.button("삭제 🗑️", key=f"del_{i}"):
                        st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()

    # 2. 내 지갑 (BOUGHT)
    st.divider()
    st.write("💰 **내 지갑 (보유 및 수익)**")
    boughts = [s for s in st.session_state.my_stocks if s['status'] == "BOUGHT"]
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "BOUGHT":
            profit_rate = ((s['curr'] - s['buy_price']) / s['buy_price']) * 100
            total_profit = (s['curr'] - s['buy_price']) * s['qty']
            color = "#ff4b4b" if profit_rate > 0 else "#4b8bff"
            st.markdown(f"""
                <div class='stock-card' style='border-left: 8px solid {color};'>
                    <b>{s['name']}</b> ({s['qty']}주) | <span style='color:{color}'><b>{profit_rate:.2f}%</b></span><br>
                    내 수익: <b>{total_profit:,}원</b><br>
                    목표가: <span class='price-target'>{s['target']:,}</span> | 탈출가: <span class='price-stop'>{s['stop']:,}</span><br>
                    📅 팔 날짜: {s['date']}
                </div>
                """, unsafe_allow_html=True)
            if st.button("팔았다! (삭제) 💸", key=f"sell_{i}"):
                st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
