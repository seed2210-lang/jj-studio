import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import concurrent.futures
import numpy as np
import json
import os

# ==========================================
# 🚨 오늘도 ☀ (비밀번호 시스템: 6006)
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "6006": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h3 style='text-align: center; color: #d4af37;'>🔒 🌼오늘도쨔잔!!🌼</h3>", unsafe_allow_html=True)
        st.text_input("헤헿", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

# --- 앱 기본 설정 ---
st.set_page_config(page_title="❤ 잘 살아보자 ❤", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    div.stButton > button { border-radius: 8px !important; font-weight: 900 !important; width: 100% !important; }
    .analysis-box { background-color: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 10px; margin-top: 10px; font-size: 13px; line-height: 1.6;}
    .buy-zone { background-color: rgba(255, 75, 75, 0.15); border: 1.5px dashed #ff4b4b; padding: 10px; border-radius: 8px; color: #ff4b4b; font-weight: bold; text-align: center; margin-bottom: 10px;}
    .wait-zone { background-color: rgba(75, 139, 255, 0.1); border: 1.5px dashed #4b8bff; padding: 10px; border-radius: 8px; color: #4b8bff; font-weight: bold; text-align: center; margin-bottom: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 저장/로드 ---
DATA_FILE = "jj_user_data.json"
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"favorites": []}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"favorites": st.session_state.favorites}, f, ensure_ascii=False)

if 'data_loaded' not in st.session_state:
    loaded = load_data()
    st.session_state.favorites = loaded.get("favorites", [])
    st.session_state.data_loaded = True
if 'rt_results' not in st.session_state: st.session_state.rt_results = []
if 'searched_stock' not in st.session_state: st.session_state.searched_stock = "" 

@st.cache_data(ttl=3600)
def load_all_stocks():
    try: return fdr.StockListing('KRX')
    except: return pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자'], 'Market': ['KOSPI']})

all_stocks_df = load_all_stocks()

# --- 보조지표 계산 ---
def add_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Up'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Low'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    df['BB_Width'] = (df['BB_Up'] - df['BB_Low']) / (df['BB_Mid'] + 1e-9)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return df

# --- 분석 엔진 ---
def get_stock_data(item, deep_scan=False):
    try:
        # 가벼운 스캔 시에는 15일치만, 딥스캔 시에는 250일치 가져옴
        days = 250 if deep_scan else 15
        df = fdr.DataReader(item['코드'], (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'))
        if len(df) < 10: return None
        
        # 가벼운 스캔 시 거래량 폭발 여부만 빠르게 체크
        if not deep_scan:
            if df['Volume'].iloc[-1] > df['Volume'].iloc[:-1].mean() * 1.5:
                return item
            return None

        # 정밀 분석 로직
        df = add_indicators(df)
        df['MA5'] = df['Close'].rolling(5).mean(); df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        curr, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
        high_60, low_20 = df['High'].iloc[-60:].max(), df['Low'].iloc[-20:].min()
        
        support = round(df['MA20'].iloc[-1] if curr > df['MA20'].iloc[-1] else df['MA60'].iloc[-1], 0)
        buy_min, buy_max = round(support * 0.99, 0), round(support * 1.03, 0)
        stop_loss = round(support * 0.95, 0)
        
        score = 0
        v1 = df['Volume'].iloc[-1] > df['Volume'].iloc[-5:-1].mean()*1.5; score += 1 if v1 else 0
        v2 = df['MA5'].iloc[-1] > df['MA20'].iloc[-1]; score += 1 if v2 else 0
        v3 = curr > prev; score += 1 if v3 else 0
        v4 = curr > df['High'].iloc[-10:-1].max(); score += 1 if v4 else 0
        v5 = 30 < df['RSI'].iloc[-1] < 70; score += 1 if v5 else 0
        v6 = curr <= low_20 * 1.15; score += 1 if v6 else 0
        v7 = df['BB_Width'].iloc[-1] < df['BB_Width'].rolling(20).mean().iloc[-1]; score += 1 if v7 else 0
        v8 = df['OBV'].iloc[-1] > df['OBV'].iloc[-5]; score += 1 if v8 else 0
        v9 = (df['RSI'].iloc[-1] > df['RSI'].iloc[-5]) and (curr < df['Close'].iloc[-5]); score += 1 if v9 else 0
        v10 = df['Close'].iloc[-1] > df['BB_Mid'].iloc[-1]; score += 1 if v10 else 0
        v11 = (high_60 - curr)/curr*100 >= 15; score += 1 if v11 else 0
        v12 = df['MA20'].iloc[-1] > df['MA20'].iloc[-10]; score += 1 if v12 else 0

        is_buy_zone = buy_min <= curr <= buy_max
        if score >= 10 and is_buy_zone: tier, t_css = "👑 SS", "ss-tier"
        elif score >= 8: tier, t_css = "💎 S", "s-tier"
        else: tier, t_css = "✅ A", "a-tier"
        
        status = "🎯 지금 진입 가능" if is_buy_zone else ("⚠️ 추격 금지" if curr > buy_max else "⏳ 바닥 확인 중")
        
        return {
            "등급": tier, "t_css": t_css, "종목": item['종목명'], "순수종목명": item['종목명'], "코드": item['코드'],
            "가격": int(curr), "수익%": round(((high_60 - curr) / curr) * 100, 1), "데이터": df,
            "타점": {"status": status, "min": buy_min, "max": buy_max, "stop": stop_loss},
            "지표": [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12], "점수": score, "고점": int(high_60)
        }
    except: return None

# --- 분석 리포트 ---
def render_analysis(sel, tab_key):
    st.markdown(f"### <span class='{sel['t_css']}'>[{sel['등급']}]</span> {sel['순수종목명']} 정밀 진단", unsafe_allow_html=True)
    t = sel['타점']
    st.markdown(f"<div class=\"{'buy-zone' if '진입' in t['status'] else 'wait-zone'}\">{t['status']} (지표 {sel['점수']}/12 통과)</div>", unsafe_allow_html=True)
    
    c1, c2, col_stop = st.columns(3)
    c1.metric("최적 매수", f"{int(t['min']):,}~")
    c2.metric("현재가", f"{sel['가격']:,}원")
    col_stop.metric("손절가", f"{int(t['stop']):,}원")

    df = sel['데이터'].tail(100)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#ff4b4b', decreasing_line_color='#4b8bff'), row=1, col=1)
    fig.add_hrect(y0=t['min'], y1=t['max'], fillcolor="red", opacity=0.15, line_width=0, row=1, col=1)
    for ma, color in zip(['MA5', 'MA20', 'MA60'], ['#EAD04C', '#C881F8', '#4CB4E2']):
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(width=1.2, color=color)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=['#ff4b4b' if c > o else '#4b8bff' for o, c in zip(df['Open'], df['Close'])]), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, xaxis_rangeslider_visible=False, dragmode='pan')
    fig.update_yaxes(side="right"); fig.update_xaxes(range=[df.index[-30], df.index[-1]])
    st.plotly_chart(fig, use_container_width=True, key=f"ch_{sel['순수종목명']}_{tab_key}")

    if st.button(f"{'❌ 삭제' if sel['순수종목명'] in st.session_state.favorites else '⭐ 추가'}", key=f"btn_{sel['순수종목명']}_{tab_key}"):
        if sel['순수종목명'] in st.session_state.favorites: st.session_state.favorites.remove(sel['순수종목명'])
        else: st.session_state.favorites.append(sel['순수종목명'])
        save_data(); st.rerun()

# --- 메인 UI ---
st.markdown("<h4 style='text-align: center; color: #d4af37;'>🌼무조건잘된다니까🌼</h4>", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(["🔍 검색", "📡 레이더", "⭐ 보물함"])

with t1:
    s_in = st.text_input("종목명 입력", "")
    if st.button("분석하기"): st.session_state.searched_stock = s_in
    if st.session_state.searched_stock:
        m = all_stocks_df[all_stocks_df['Name'] == st.session_state.searched_stock]
        if not m.empty:
            res = get_stock_data({'코드': m.iloc[0]['Code'], '종목명': m.iloc[0]['Name']}, deep_scan=True)
            if res: render_analysis(res, "search")
        else: st.warning("정확한 이름을 입력해줘!")

with t2:
    m_type = st.selectbox("시장", ["KOSPI", "KOSDAQ"])
    if st.button("📡 [터보 스캔] SS등급 추출하기"):
        try:
            # 1단계: 가벼운 리스팅 가져오기
            all_l = fdr.StockListing('KRX')
            df_s = all_l[all_l['Market'].str.contains(m_type)]
            
            p_bar = st.progress(0, text="📡 1단계: 후보 종목 필터링 중...")
            found_candidates = []
            
            # 가벼운 스캔 진행
            with concurrent.futures.ThreadPoolExecutor(max_workers=35) as ex:
                futures = [ex.submit(get_stock_data, {'코드': r.Code, '종목명': r.Name}, deep_scan=False) for r in df_s.itertuples()]
                for i, f in enumerate(concurrent.futures.as_completed(futures)):
                    res = f.result()
                    if res: found_candidates.append(res)
                    p_bar.progress((i+1)/len(df_s), text=f"📡 1단계 완료: 후보 {len(found_candidates)}개 포착")

            # 2단계: 정밀 분석 진행
            p_bar.progress(0, text="💎 2단계: 후보 종목 정밀 분석 중...")
            final_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
                futures = [ex.submit(get_stock_data, item, deep_scan=True) for item in found_candidates]
                for i, f in enumerate(concurrent.futures.as_completed(futures)):
                    res = f.result()
                    if res: final_results.append(res)
                    p_bar.progress((i+1)/len(found_candidates), text=f"💎 2단계 완료: {i+1}/{len(found_candidates)}")
            
            st.session_state.rt_results = sorted(final_results, key=lambda x: (x['등급'], x['점수'], x['수익%']), reverse=True)[:30]
            p_bar.empty()
        except: st.error("❗ 서버 점검 시간인 것 같아. 잠시 후에 다시 시도해줘!")
    
    if st.session_state.rt_results:
        df_r = pd.DataFrame(st.session_state.rt_results)
        event = st.dataframe(df_r[['등급', '종목', '가격', '수익%']].style.apply(lambda r: ['background-color: rgba(255, 75, 75, 0.15)']*4 if 'SS' in r['등급'] else ['']*4, axis=1), 
                             use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="radar_df")
        if event.selection.rows: render_analysis(st.session_state.rt_results[event.selection.rows[0]], "radar")

with t3:
    if st.session_state.favorites:
        if st.button("🔄 실시간 동기화"): st.rerun()
        fav_l = []
        for fn in st.session_state.favorites:
            m = all_stocks_df[all_stocks_df['Name'] == fn]
            if not m.empty:
                r = get_stock_data({'코드': m.iloc[0]['Code'], '종목명': fn}, deep_scan=True)
                if r: fav_l.append(r)
        if fav_l:
            fav_r = pd.DataFrame(fav_l)
            event_f = st.dataframe(fav_r[['등급', '종목', '가격', '수익%']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="fav_df")
            if event_f.selection.rows: render_analysis(fav_l[event_f.selection.rows[0]], "fav")
    else: st.info("보물함이 비어 있어!")
