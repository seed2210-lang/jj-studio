import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os
import numpy as np

#1 --- 📱 모바일 최적화 및 스타일 ---
st.set_page_config(page_title="💖💖💖💖💖💖💖💖", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 24px; font-weight: bold; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; }
    .score-badge { background: #ff4b4b; color: white; padding: 3px 10px; border-radius: 5px; font-size: 13px; font-weight: bold; }
    .price-curr { color: #ffffff; font-weight: bold; font-size: 18px; }
    .price-target { color: #ff4b4b; font-weight: bold; font-size: 18px; } 
    .price-stop { color: #4b8bff; font-weight: bold; font-size: 18px; }   
    </style>
    """, unsafe_allow_html=True)

DATA_FILE = "jj_mobile_v4.json"

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

today_str = datetime.now().strftime('%Y-%m-%d')
sell_list = [s['name'] for s in st.session_state.my_stocks if s.get('status') == 'BOUGHT' and s.get('sell_date') <= today_str]
if sell_list:
    for name in sell_list:
        st.markdown(f"<div style='background:#ff4b4b; color:white; padding:10px; border-radius:10px; text-align:center; margin-bottom:10px;'>🚨 {name} 매도 타이밍! 기계처럼 익절/손절하자 💰</div>", unsafe_allow_html=True)

#3 --- 🎯 [퀀트 스나이퍼] 알고리즘 엔진 ---
@st.cache_data(ttl=3600)
def get_all_stocks():
    try:
        df1 = fdr.StockListing('KOSPI')[['Code', 'Name']]
        df2 = fdr.StockListing('KOSDAQ')[['Code', 'Name']]
        total = pd.concat([df1, df2]).dropna().drop_duplicates()
        return total.sample(frac=1).reset_index(drop=True)
    except:
        return pd.DataFrame({'Code': ['005930', '128820', '403490'], 'Name': ['삼성전자', '대성산업', '뉴로메카']})

def analyze_quant_sniper(item, mode="RADAR"):
    try:
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d'))
        if len(df) < 40: return None
        
        c = df['Close']; v = df['Volume']; h = df['High']; l = df['Low']
        curr = int(c.iloc[-1])
        vol_avg = v.iloc[-20:-1].mean()
        
        # 볼린저 밴드 (에너지 응축 확인)
        ma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        upper_bb = ma20 + (std20 * 2)
        lower_bb = ma20 - (std20 * 2)
        band_width = (upper_bb - lower_bb) / ma20
        
        # 퀀트 평가 지표
        checks = [
            band_width.iloc[-2] < 0.1,                 # 1. 어제까지 밴드폭이 10% 이내로 응축됨 (폭풍 전야)
            c.iloc[-1] > upper_bb.iloc[-2],            # 2. 오늘 상단 밴드를 강하게 뚫음 (돌파)
            v.iloc[-1] > vol_avg * 2.5,                # 3. 거래량이 평균 대비 2.5배 폭발
            c.iloc[-1] > c.iloc[-2],                   # 4. 전일 대비 상승
            c.iloc[-1] > ma20.iloc[-1],                # 5. 20일 생명선 위
            (h.iloc[-1] - c.iloc[-1]) < (c.iloc[-1] - l.iloc[-1]) # 6. 매수세가 더 강하게 마감 (윗꼬리 짧음)
        ]
        
        # 목표/손절가 기계적 세팅 (손익비 2:1 구조)
        target = int(curr * 1.15) # 15% 수익 노림
        stop = int(curr * 0.93)   # 7% 하락 시 무조건 기계적 손절
        
        if mode == "SURGE": 
            # 급등 스나이퍼 모드: 에너지가 응축되었다가 막 터지기 시작한 놈
            if checks[0] and checks[1] and checks[2] and checks[5]: 
                return {"type": "🔥 퀀트 돌파", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": "오늘 마감 전 매도", "date": today_str}
        else:
            # 스윙 레이더 모드: 정배열에서 이쁘게 눌림목 주는 놈
            ma5 = c.rolling(5).mean()
            if ma5.iloc[-1] > ma20.iloc[-1] and (ma20.iloc[-1] * 0.98 < curr < ma20.iloc[-1] * 1.05) and v.iloc[-1] < vol_avg:
                sell_d = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
                return {"type": "🛡️ 3일 스윙", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "hold": "3일 유지", "date": sell_d}
        return None
    except: return None

#4 --- 📱 메인 UI ---
all_s = get_all_stocks()
tab1, tab2, tab3, tab4 = st.tabs(["🔍검색", "🎁당일", "📡장기", "💰보물함"])

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="타겟 종목 입력")
    if s_word and not all_s.empty:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(3).iterrows():
                if st.button(f"🧐 {row['Name']} 퀀트 분석"):
                    res = analyze_quant_sniper({'Code': row['Code'], 'Name': row['Name']}, "SURGE")
                    if not res: res = analyze_quant_sniper({'Code': row['Code'], 'Name': row['Name']}, "RADAR")
                    
                    if res:
                        st.markdown(f"""
                        <div class='stock-card'>
                            <h3>{res['name']} <span class='score-badge'>{res['type']}</span></h3>
                            현재 시세: <span class='price-curr'>{res['curr']:,}원</span><br>
                            올라갈 시세(목표): <span class='price-target'>{res['target']:,}원</span><br>
                            팔아야할 금액(손절): <span class='price-stop'>{res['stop']:,}원</span><br>
                        </div>
                        """, unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        in_p = c1.number_input("매수가", key=f"src_p_{row['Code']}", value=res['curr'])
                        in_q = c2.number_input("수량(주)", key=f"src_q_{row['Code']}", value=1, min_value=1)
                        if st.button("⭐ 장부에 즉시 기록", key=f"src_btn_{row['Code']}"):
                            st.session_state.my_stocks.append({**res, "status": "BOUGHT", "buy_price": in_p, "qty": in_q, "sell_date": res['date']})
                            save_data(st.session_state.my_stocks); st.toast("지갑에 기록 완료! 🚀"); st.rerun()
                    else: st.warning("지금은 차트가 망가졌거나 에너지가 없어. 패스!")
        else: st.error("종목을 못 찾겠어!")

with tab2:
    st.write("🔥 **응축 폭발 돌파 매매 (8:30 예약 → 15:00 청산)**")
    if st.button("🚀 퀀트 급등주 스캔"):
        results = []
        subset = all_s.head(400) 
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(analyze_quant_sniper, {'Code': r.Code, 'Name': r.Name}, "SURGE") for r in subset.itertuples()]
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r: results.append(r)
        st.session_state.surge_results = results

    if 'surge_results' in st.session_state and st.session_state.surge_results:
        for i, r in enumerate(st.session_state.surge_results):
            with st.expander(f"🔥 {r['name']} (시세: {r['curr']:,}원)"):
                st.markdown(f"""
                <div class='stock-card'>
                    올라갈 시세(빨강): <span class='price-target'>{r['target']:,}원</span><br>
                    팔아야할 금액(파랑): <span class='price-stop'>{r['stop']:,}원</span><br>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                p_val = c1.number_input("매수가", key=f"p_sg_{i}_{r['code']}", value=r['curr'])
                q_val = c2.number_input("수량", key=f"q_sg_{i}_{r['code']}", value=1, min_value=1)
                if st.button("⭐ 지갑에 기록", key=f"btn_sg_{i}_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "BOUGHT", "buy_price": p_val, "qty": q_val, "sell_date": today_str})
                    save_data(st.session_state.my_stocks); st.rerun()

with tab3:
    st.write("📡 **안전한 눌림목 스윙 (2~3일 보유)**")
    if st.button("📡 스윙 레이더 가동"):
        p_bar = st.progress(0, text="알고리즘 분석 중... 위이잉")
        results = []
        subset = all_s.head(400)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(analyze_quant_sniper, {'Code': r.Code, 'Name': r.Name}, "RADAR") for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r: results.append(r)
                if i % 40 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        st.session_state.radar_results = results

    if 'radar_results' in st.session_state and st.session_state.radar_results:
        for i, r in enumerate(st.session_state.radar_results):
            with st.expander(f"🛡️ {r['name']} (시세: {r['curr']:,}원)"):
                st.markdown(f"""
                <div class='stock-card'>
                    올라갈 시세(빨강): <span class='price-target'>{r['target']:,}원</span><br>
                    팔아야할 금액(파랑): <span class='price-stop'>{r['stop']:,}원</span><br>
                    유지 기간: <b>{r['hold']}</b>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                p_val = c1.number_input("매수가", key=f"p_rd_{i}_{r['code']}", value=r['curr'])
                q_val = c2.number_input("수량", key=f"q_rd_{i}_{r['code']}", value=1, min_value=1)
                if st.button("⭐ 지갑에 기록", key=f"btn_rd_{i}_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "BOUGHT", "buy_price": p_val, "qty": q_val, "sell_date": r['date']})
                    save_data(st.session_state.my_stocks); st.rerun()

with tab4:
    st.markdown("<h4 style='text-align:center;'>💓무조건잘된다니까💓</h4>", unsafe_allow_html=True)
    st.write("💰 **내 지갑 (수익률 관리소)**")
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
                        매수가: {s['buy_price']:,} ➔ 목표: <span class='price-target'>{s['target']:,}</span> | 탈출: <span class='price-stop'>{s['stop']:,}</span><br>
                        📅 팔아야 할 날짜: {s.get('sell_date', today_str)}
                    </div>
                    """, unsafe_allow_html=True)
                if st.button("청산 완료! (삭제) 💸", key=f"sell_{i}_{s['code']}"):
                    st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
    else: st.info("지갑이 텅 비었어! 급등이나 레이더에서 매수 정보를 적고 기록을 눌러봐!")
