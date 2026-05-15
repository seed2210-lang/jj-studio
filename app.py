import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os
import numpy as np

#1 --- 📱 모바일 최적화 및 스타일 ---
st.set_page_config(page_title="❤❤❤❤❤❤❤❤❤", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 24px; font-weight: bold; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; }
    .price-target { color: #ff4b4b; font-weight: bold; } /* 빨간색: 목표 */
    .price-stop { color: #4b8bff; font-weight: bold; }   /* 파란색: 손절 */
    .check-ok { color: #4CAF50; font-size: 12px; }       /* 통과 지표 */
    .check-no { color: #777; font-size: 12px; }          /* 미달 지표 */
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

#2 --- 🔐 보안 (2727) ---
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

#3 --- 🎯 12가지 정밀 분석 엔진 ---
@st.cache_data(ttl=3600)
def get_all_stocks():
    try:
        # 거래소 서버 차단 대비 - 가장 안정적인 방식으로 리스트 확보
        df = fdr.StockListing('KRX')[['Code', 'Name']]
        return df.dropna().drop_duplicates()
    except:
        # 서버 차단 시 사용자에게 알림 후 최소한의 동작 보장
        st.error("📡 주식 서버 연결이 불안정해! 잠시 후 다시 시도해줘.")
        return pd.DataFrame(columns=['Code', 'Name'])

def analyze_12_points(item):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d'))
        if len(df) < 40: return None
        
        c = df['Close']; v = df['Volume']; h = df['High']; l = df['Low']
        curr = int(c.iloc[-1])
        vol_avg = v.iloc[-10:-1].mean()
        ma5 = c.rolling(5).mean(); ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
        
        # 12가지 정밀 체크리스트
        names = ["거래량급증", "5일선위", "단기정배열", "중기정배열", "RSI안정", "바닥권", "당일상승", "OBV우상향", "윗꼬리짧음", "20일선지지", "상승여력", "매수강도"]
        checks = [
            v.iloc[-1] > vol_avg * 1.5,
            curr > ma5.iloc[-1],
            ma5.iloc[-1] > ma20.iloc[-1],
            ma20.iloc[-1] > ma60.iloc[-1],
            30 < (100 - (100 / (1 + (c.diff().where(c.diff() > 0, 0).rolling(14).mean() / (-c.diff().where(c.diff() < 0, 0)).rolling(14).mean()).iloc[-1]))) < 70,
            curr < l.iloc[-20:].min() * 1.2,
            curr > c.iloc[-2],
            (np.sign(c.diff()) * v).cumsum().iloc[-1] > (np.sign(c.diff()) * v).cumsum().iloc[-5],
            (h.iloc[-1] - curr) < (curr - l.iloc[-1]),
            curr > ma20.iloc[-1] * 0.98,
            (h.iloc[-40:].max() - curr) / curr > 0.1,
            v.iloc[-1] > v.iloc[-2]
        ]
        
        score = sum(checks)
        report = [f"{'✅' if ch else '❌'} {nm}" for ch, nm in zip(checks, names)]
        
        return {
            "name": item['Name'], "code": item['Code'], "curr": curr,
            "target": int(curr * 1.15), "stop": int(curr * 0.95),
            "score": score, "report": report,
            "is_surge": checks[0] and checks[6] # 급등 조건: 거래량+상승
        }
    except: return None

#4 --- 📱 메인 UI ---
all_s = get_all_stocks()
tab1, tab2, tab3, tab4 = st.tabs(["🔍 찾기", "🔥 급등", "📡 레이더", "⭐보물함"])

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="예: 하이닉스")
    if s_word and not all_s.empty:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(5).iterrows():
                if st.button(f"🧐 {row['Name']} 12지표 정밀 분석"):
                    res = analyze_12_points({'Code': row['Code'], 'Name': row['Name']})
                    if res:
                        st.markdown(f"""
                        <div class='stock-card'>
                            <h3>{res['name']} <small style='font-size:14px;'>({res['score']}점)</small></h3>
                            현재가: {res['curr']:,}원<br>
                            올라갈 시세(빨강): <span class='price-target'>{res['target']:,}원</span><br>
                            팔아야할 금액(파랑): <span class='price-stop'>{res['stop']:,}원</span><br>
                            <div style='margin-top:10px;'>{' '.join(res['report'][:6])}</div>
                            <div>{' '.join(res['report'][6:])}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"⭐ {res['name']} 담기", key=f"add_{res['code']}"):
                            st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0, "qty": 0, "date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')})
                            save_data(st.session_state.my_stocks); st.rerun()
        else: st.error("종목을 못 찾겠어!")

with tab2:
    st.write("🔥 **오늘 8:30 예약 → 오늘 3:00 매도 (당일 승부)**")
    if st.button("🚀 급등주 실시간 스캔"):
        results = []
        if not all_s.empty:
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
                futures = [ex.submit(analyze_12_points, {'Code': r.Code, 'Name': r.Name}) for r in all_s.head(200).itertuples()]
                for f in concurrent.futures.as_completed(futures):
                    r = f.result()
                    if r and r['is_surge']: results.append(r)
            for r in results:
                st.success(f"**{r['name']}** ({r['curr']:,}원) ➔ 목표: {r['target']:,}")
                if st.button(f"⭐ 담기", key=f"surge_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0, "date": datetime.now().strftime('%Y-%m-%d')})
                    save_data(st.session_state.my_stocks); st.rerun()
        else: st.warning("데이터 리스트가 비어있어!")

with tab3:
    st.write("📡 **며칠 동안 쭉쭉 올라갈 보물찾기 (7점 이상)**")
    if st.button("📡 레이더 가동 (위이잉~)"):
        p_bar = st.progress(0, text="보물 찾는 중...")
        results = []
        subset = all_s.head(400)
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(analyze_12_points, {'Code': r.Code, 'Name': r.Name}) for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r and r['score'] >= 7: results.append(r)
                if i % 40 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        for r in results:
            st.write(f"[{r['score']}점] **{r['name']}** ({r['curr']:,}원)")
            if st.button(f"⭐ 담기", key=f"radar_{r['code']}"):
                st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0, "date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')})
                save_data(st.session_state.my_stocks); st.rerun()

with tab4:
    st.subheader("💖무조건잘된다니까💖")
    # 1. 예약대기 (WISH)
    w_list = [s for s in st.session_state.my_stocks if s['status'] == "WISH"]
    if w_list:
        st.write("🧐 **살까 말까 (얼마에 몇 주 샀어?)**")
        for i, s in enumerate(st.session_state.my_stocks):
            if s['status'] == "WISH":
                with st.container():
                    st.markdown(f"<div class='stock-card'><b>{s['name']}</b> ({s['score']}점)</div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    b_p = c1.number_input("매수가", key=f"bp_{i}", value=s['curr'])
                    b_q = c2.number_input("몇 주?", key=f"bq_{i}", value=1)
                    if st.button("구매 완료 ✅", key=f"done_{i}"):
                        s['status'] = "BOUGHT"; s['buy_price'] = b_p; s['qty'] = b_q
                        save_data(st.session_state.my_stocks); st.rerun()
                    if st.button("삭제 🗑️", key=f"del_{i}"):
                        st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
    st.divider()
    # 2. 내 지갑 (BOUGHT)
    st.write("💰 **내 지갑 (수익 관리)**")
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "BOUGHT":
            profit_rate = ((s['curr'] - s['buy_price']) / s['buy_price']) * 100
            total_profit = (s['curr'] - s['buy_price']) * s['qty']
            color = "#ff4b4b" if profit_rate > 0 else "#4b8bff"
            st.markdown(f"""
                <div class='stock-card' style='border-left: 8px solid {color};'>
                    <b>{s['name']}</b> ({s['qty']}주) | <span style='color:{color}'><b>{profit_rate:.2f}%</b></span><br>
                    이익: <b>{total_profit:,}원</b><br>
                    목표: <span class='price-target'>{s['target']:,}</span> | 손절: <span class='price-stop'>{s['stop']:,}</span><br>
                    📅 팔 날짜: {s['date']}
                </div>
                """, unsafe_allow_html=True)
            if st.button("팔았다! (삭제) 💸", key=f"sell_{i}"):
                st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
