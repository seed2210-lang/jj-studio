import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os
import numpy as np

#1 --- 📱 모바일 최적화 및 스타일 (색상/가독성 극대화) ---
st.set_page_config(page_title="💖💖💖💖💖💖💖💖", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 24px; font-weight: bold; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; }
    .score-badge { background: #d4af37; color: black; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .price-curr { color: #ffffff; font-weight: bold; font-size: 18px; }
    .price-target { color: #ff4b4b; font-weight: bold; font-size: 18px; } /* 빨간색: 목표 */
    .price-stop { color: #4b8bff; font-weight: bold; font-size: 18px; }   /* 파란색: 손절/탈출 */
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

#2 --- 🔐 보안 시스템 (2727) ---
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
        total = pd.concat([df1, df2]).dropna().drop_duplicates()
        return total.sample(frac=1).reset_index(drop=True) # 랜덤 셔플로 중소형주 발굴
    except:
        return pd.DataFrame(columns=['Code', 'Name']) # 텅 빈 리스트 반환(억지 추천 삭제)

def analyze_12_points(item, mode="RADAR"):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d'))
        if len(df) < 30: return None
        
        c = df['Close']; v = df['Volume']; h = df['High']; l = df['Low']
        curr = int(c.iloc[-1])
        vol_avg = v.iloc[-10:-1].mean()
        ma5 = c.rolling(5).mean(); ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
        
        rsi = 100 - (100 / (1 + (c.diff().where(c.diff() > 0, 0).rolling(14).mean() / (-c.diff().where(c.diff() < 0, 0)).rolling(14).mean()).iloc[-1]))
        obv = (np.sign(c.diff()) * v).fillna(0).cumsum().iloc[-1]
        
        names = ["거래량급증", "5일선위", "단기정배열", "중기정배열", "RSI안정", "바닥권", "당일상승", "OBV우상향", "윗꼬리짧음", "20일선지지", "상승여력", "매수강도"]
        checks = [
            v.iloc[-1] > vol_avg * 1.5, curr > ma5.iloc[-1], ma5.iloc[-1] > ma20.iloc[-1], ma20.iloc[-1] > ma60.iloc[-1],
            30 < rsi < 70, curr < l.iloc[-20:].min() * 1.2, curr > c.iloc[-2],
            obv > (np.sign(c.diff()) * v).fillna(0).cumsum().iloc[-5], (h.iloc[-1] - curr) < (curr - l.iloc[-1]),
            curr > ma20.iloc[-1] * 0.98, (h.iloc[-30:].max() - curr) / curr > 0.1, v.iloc[-1] > v.iloc[-2]
        ]
        score = sum(checks)
        report = [f"{'✅' if ch else '❌'} {nm}" for ch, nm in zip(checks, names)]
        
        target = int(curr * 1.15)
        stop = int(curr * 0.95)
        
        if mode == "SURGE":
            if checks[0] and checks[6]: # 거래량 급증 + 상승세
                return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": "오늘 마감 전 매도", "date": today_str, "score": score, "report": report}
        else:
            if score >= 6: # 레이더 필터링 기준
                days = "3일 유지" if rsi < 50 else "2일 유지"
                sell_d = (datetime.now() + timedelta(days=int(days[0]))).strftime('%Y-%m-%d')
                return {"type": f"🛡️ {days}", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": days, "date": sell_d, "score": score, "report": report}
        return None
    except: return None

#5 --- 📱 메인 UI (4개 탭) ---
all_s = get_all_stocks()
tab1, tab2, tab3, tab4 = st.tabs(["🔍 찾기", "🔥 급등", "📡 레이더", "⭐ 보물함"])

if 'selected_stock' not in st.session_state: st.session_state.selected_stock = None

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="예: 하이닉스")
    if s_word and not all_s.empty:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(3).iterrows():
                if st.button(f"🧐 {row['Name']} 정밀 분석", key=f"src_{row['Code']}"):
                    st.session_state.selected_stock = row['Code']
                    st.session_state.selected_name = row['Name']
            
            if st.session_state.selected_stock:
                res = analyze_12_points({'Code': st.session_state.selected_stock, 'Name': st.session_state.selected_name}, "RADAR")
                if res:
                    st.markdown(f"""
                    <div class='stock-card'>
                        <h3>{res['name']} <small style='font-size:14px;'>({res['score']}점)</small></h3>
                        현재 시세: <span class='price-curr'>{res['curr']:,}원</span><br>
                        올라갈 시세(빨강): <span class='price-target'>{res['target']:,}원</span><br>
                        팔아야할 금액(파랑): <span class='price-stop'>{res['stop']:,}원</span><br>
                        <div style='margin-top:10px;'>{' '.join(res['report'][:6])}</div>
                        <div>{' '.join(res['report'][6:])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    in_p = c1.number_input("실제 매수가 입력", key="in_p_1", value=res['curr'])
                    in_q = c2.number_input("매수 수량(주) 입력", key="in_q_1", value=1, min_value=1)
                    
                    if st.button("⭐ 장부에 즉시 기록", key="save_src_btn"):
                        st.session_state.my_stocks.append({**res, "status": "BOUGHT", "buy_price": in_p, "qty": in_q, "sell_date": res['date']})
                        save_data(st.session_state.my_stocks)
                        st.toast("지갑에 기록 완료! 🚀")
                        st.session_state.selected_stock = None
                        st.rerun()
        else: st.error("종목을 못 찾겠어!")

with tab2:
    st.write("🔥 **오늘 8:30 예약 → 오늘 3:00 매도 (당일 승부 중소형주)**")
    if st.button("🚀 급등주 실시간 스캔 시작"):
        results = []
        subset = all_s.head(400) # 랜덤하게 섞인 상위 400개 스캔
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(analyze_12_points, {'Code': r.Code, 'Name': r.Name}, "SURGE") for r in subset.itertuples()]
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r: results.append(r)
        st.session_state.surge_results = results

    if 'surge_results' in st.session_state and st.session_state.surge_results:
        for i, r in enumerate(st.session_state.surge_results):
            with st.expander(f"🔥 {r['name']} (현재 시세: {r['curr']:,}원)"):
                st.markdown(f"""
                <div class='stock-card'>
                    현재 시세: <span class='price-curr'>{r['curr']:,}원</span><br>
                    올라갈 시세(빨강): <span class='price-target'>{r['target']:,}원</span><br>
                    팔아야할 금액(파랑): <span class='price-stop'>{r['stop']:,}원</span><br>
                    <div style='margin-top:5px;'>{' '.join(r['report'][:6])}</div>
                    <div>{' '.join(r['report'][6:])}</div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                p_val = c1.number_input("매수가", key=f"p_sg_{i}_{r['code']}", value=r['curr'])
                q_val = c2.number_input("수량(주)", key=f"q_sg_{i}_{r['code']}", value=1, min_value=1)
                if st.button("⭐ 이 금액으로 장부 기록", key=f"btn_sg_{i}_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "BOUGHT", "buy_price": p_val, "qty": q_val, "sell_date": today_str})
                    save_data(st.session_state.my_stocks); st.rerun()

with tab3:
    st.write("📡 **2~4일간 추세가 우상향할 보물찾기**")
    if st.button("📡 레이더 가동"):
        p_bar = st.progress(0, text="12지표 엔진 가동 중... 위이잉")
        results = []
        subset = all_s.head(400)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(analyze_12_points, {'Code': r.Code, 'Name': r.Name}, "RADAR") for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r: results.append(r)
                if i % 40 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        st.session_state.radar_results = results

    if 'radar_results' in st.session_state and st.session_state.radar_results:
        for i, r in enumerate(st.session_state.radar_results):
            with st.expander(f"📡 [{r['score']}점] {r['name']} (현재 시세: {r['curr']:,}원)"):
                st.markdown(f"""
                <div class='stock-card'>
                    현재 시세: <span class='price-curr'>{r['curr']:,}원</span><br>
                    올라갈 시세(빨강): <span class='price-target'>{r['target']:,}원</span><br>
                    팔아야할 금액(파랑): <span class='price-stop'>{r['stop']:,}원</span><br>
                    유지 기간: <b>{r['hold']}</b><br>
                    <div style='margin-top:5px;'>{' '.join(r['report'][:6])}</div>
                    <div>{' '.join(r['report'][6:])}</div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                p_val = c1.number_input("매수가", key=f"p_rd_{i}_{r['code']}", value=r['curr'])
                q_val = c2.number_input("수량(주)", key=f"q_rd_{i}_{r['code']}", value=1, min_value=1)
                if st.button("⭐ 이 금액으로 장부 기록", key=f"btn_rd_{i}_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "BOUGHT", "buy_price": p_val, "qty": q_val, "sell_date": r['date']})
                    save_data(st.session_state.my_stocks); st.rerun()

with tab4:
    st.markdown("<h3 style='text-align:center;'>💖무조건잘된다니까💖</h3>", unsafe_allow_html=True)
    st.write("💰 **내 지갑 (실시간 보유 및 총수익)**")
    boughts = [s for s in st.session_state.my_stocks if s.get('status') == "BOUGHT"]
    if boughts:
        for i, s in enumerate(st.session_state.my_stocks):
            if s.get('status') == "BOUGHT":
                profit_rate = ((s['curr'] - s['buy_price']) / s['buy_price']) * 100
                total_profit = (s['curr'] - s['buy_price']) * s['qty']
                color = "#ff4b4b" if profit_rate > 0 else "#4b8bff"
                st.markdown(f"""
                    <div class='stock-card' style='border-left: 8px solid {color};'>
                        <span style='font-size:18px;'><b>{s['name']}</b></span> ({s['qty']}주)<br>
                        현재 수익률: <span style='color:{color}; font-weight:bold;'>{profit_rate:.2f}%</span><br>
                        실제 이익금: <b>{total_profit:,}원</b><br>
                        매수가: {s['buy_price']:,} ➔ 현재 시세: {s['curr']:,}원<br>
                        목표(빨강): <span class='price-target'>{s['target']:,}</span> | 탈출(파랑): <span class='price-stop'>{s['stop']:,}</span><br>
                        📅 팔아야 할 날짜: {s.get('sell_date', today_str)}
                    </div>
                    """, unsafe_allow_html=True)
                if st.button("팔았다! (장부에서 삭제) 💸", key=f"sell_{i}_{s['code']}"):
                    st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
    else: st.info("현재 지갑에 보유 중인 주식이 없어. 검색이나 레이더에서 매수가와 수량을 적고 [⭐장부 기록]을 눌러봐!")
