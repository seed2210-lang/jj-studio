import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import json
import os

#1 --- 📱 모바일 최적화 및 스타일 ---
st.set_page_config(page_title="❤❤❤❤❤❤❤❤", layout="centered")
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px; font-weight: bold; border-radius: 12px; margin-bottom: 8px; }
    .main-title { text-align: center; color: #d4af37; font-size: 24px; font-weight: bold; }
    .alert-box { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 10px; }
    .stock-card { background: #1c2128; padding: 15px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; }
    .price-target { color: #ff4b4b; font-weight: bold; } /* 빨간색: 목표가 */
    .price-stop { color: #4b8bff; font-weight: bold; }   /* 파란색: 손절가 */
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

#2 --- 🔐 비번 2727 ---
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
        st.markdown(f"<div class='alert-box'>🚨 오늘 '{name}' 팔자! 💰</div>", unsafe_allow_html=True)

#4 --- 🎯 [특급 우회] 데이터 엔진 ---
@st.cache_data(ttl=3600)
def get_all_stocks(): 
    try:
        # 네이버 금융 리스트 우회 (차단 방지)
        df = fdr.StockListing('KOSPI')[['Code', 'Name']]
        df2 = fdr.StockListing('KOSDAQ')[['Code', 'Name']]
        res = pd.concat([df, df2]).dropna().drop_duplicates()
        if res.empty: raise Exception("Data Empty")
        return res
    except:
        # 최종 보루: 서버가 아예 막혔을 때 핵심 종목이라도 띄워줌
        return pd.DataFrame({'Code':['005930','000660','128820','403490','066570'], 
                             'Name':['삼성전자','SK하이닉스','대성산업','뉴로메카','LG전자']})

def analyze_logic(item, mode="RADAR"):
    try:
        # 야후 파이낸스(구글 우회) 방식으로 데이터 로드 시도
        df = fdr.DataReader(item['Code'], (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d'))
        if len(df) < 15: return None
        
        last = df.iloc[-1]; prev = df.iloc[-2]
        curr = int(last['Close'])
        vol_avg = df['Volume'].iloc[-15:-1].mean()
        
        # 목표/손절 계산
        target = int(curr * 1.15) # 빨간색 (올라갈 시세)
        stop = int(curr * 0.95)   # 파란색 (팔아야 할 금액)
        
        # 🔥 오늘 사자 (SURGE)
        if mode == "SURGE":
            if last['Volume'] > vol_avg * 2.0 and last['Close'] > last['Open']:
                return {"type": "🔥 오늘 사자", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "sell_date": today_str, "hold": "오늘 마감 전"}
        
        # 📡 레이더 (며칠 사자)
        else:
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            if last['Close'] > ma20:
                days = 3 if last['Close'] > prev['Close'] else 2
                sell_d = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
                return {"type": f"🛡️ {days}일 유지", "name": item['Name'], "code": item['Code'], "curr": curr, "target": target, "stop": stop, "sell_date": sell_d, "hold": f"{days}일"}
        return None
    except: return None

#5 --- 📱 메인 UI (찾기, 급등, 레이더, 장부) ---
all_s = get_all_stocks()
tab1, tab2, tab3, tab4 = st.tabs(["🔍 찾기", "🔥 급등", "📡 레이더", "⭐보물함"])

with tab1:
    s_word = st.text_input("종목명 검색", placeholder="예: 뉴로메카")
    if s_word:
        found = all_s[all_s['Name'].str.contains(s_word, case=False, na=False)]
        if not found.empty:
            for _, row in found.head(3).iterrows():
                if st.button(f"🧐 {row['Name']} 분석하기", key=f"s_{row['Code']}"):
                    res = analyze_logic({'Code': row['Code'], 'Name': row['Name']}, "RADAR")
                    if res:
                        st.markdown(f"""
                        <div class='stock-card'>
                            <b>{res['name']}</b> ({res['type']})<br>
                            현재: {res['curr']:,}원<br>
                            올라갈 시세(빨강): <span class='price-target'>{res['target']:,}원</span><br>
                            팔아야할 금액(파랑): <span class='price-stop'>{res['stop']:,}원</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"⭐ 담기", key=f"add_{res['code']}"):
                            st.session_state.my_stocks.append({**res, "status": "WISH", "buy_price": 0, "qty": 0})
                            save_data(st.session_state.my_stocks); st.rerun()
        else: st.error("종목을 못 찾겠어!")

with tab2:
    st.write("🔥 **8:30 예약 → 오늘 3:00 매도 종목**")
    if st.button("🚀 급등주 스캔 시작"):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(analyze_logic, {'Code': r.Code, 'Name': r.Name}, "SURGE") for r in all_s.head(200).itertuples()]
            for f in concurrent.futures.as_completed(futures):
                r = f.result()
                if r: results.append(r)
        if results:
            for r in results:
                st.success(f"**{r['name']}** | 현재: {r['curr']:,} | 목표: {r['target']:,}")
                if st.button(f"⭐ {r['name']} 담기", key=f"surge_{r['code']}"):
                    st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0})
                    save_data(st.session_state.my_stocks); st.rerun()
        else: st.info("지금 당장 튈 종목이 안 보여. 좀 더 기다려보자!")

with tab3:
    st.write("📡 **며칠 동안 쭉쭉 올라갈 보물찾기**")
    if st.button("📡 레이더 가동 (상위 300개)"):
        p_bar = st.progress(0, text="스캔 중...")
        results = []
        subset = all_s.head(300)
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(analyze_logic, {'Code': r.Code, 'Name': r.Name}, "RADAR") for r in subset.itertuples()]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                r = f.result()
                if r: results.append(r)
                if i % 30 == 0: p_bar.progress((i+1)/len(subset))
        p_bar.empty()
        for r in results:
            st.write(f"[{r['type']}] **{r['name']}** | 목표: {r['target']:,}")
            if st.button(f"⭐ 담기", key=f"radar_{r['code']}"):
                st.session_state.my_stocks.append({**r, "status": "WISH", "buy_price": 0, "qty": 0})
                save_data(st.session_state.my_stocks); st.rerun()

with tab4:
    st.subheader("💖무조건잘된다니까💖")
    w_list = [s for s in st.session_state.my_stocks if s['status'] == "WISH"]
    if w_list:
        st.write("🧐 **살까 말까 (대기 목록)**")
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
    st.divider()
    st.write("💰 **내 지갑 (수익률 관리)**")
    b_list = [s for s in st.session_state.my_stocks if s['status'] == "BOUGHT"]
    for i, s in enumerate(st.session_state.my_stocks):
        if s['status'] == "BOUGHT":
            profit_rate = ((s['curr'] - s['buy_price']) / s['buy_price']) * 100
            total_profit = (s['curr'] - s['buy_price']) * s['qty']
            color = "#ff4b4b" if profit_rate > 0 else "#4b8bff"
            st.markdown(f"""
                <div class='stock-card' style='border-left: 8px solid {color};'>
                    <b>{s['name']}</b> ({s['qty']}주) | <span style='color:{color}'>{profit_rate:.2f}%</span><br>
                    이익: <b>{total_profit:,}원</b><br>
                    목표: <span class='price-target'>{s['target']:,}</span> | 손절: <span class='price-stop'>{s['stop']:,}</span><br>
                    📅 매도 예정: {s['sell_date']}
                </div>
                """, unsafe_allow_html=True)
            if st.button("팔았다! (삭제) 💸", key=f"sell_{i}"):
                st.session_state.my_stocks.pop(i); save_data(st.session_state.my_stocks); st.rerun()
