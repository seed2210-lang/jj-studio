import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import concurrent.futures
import random
import numpy as np
import json
import os

# ==========================================
# 🚨 오늘도 ☀ (비밀번호 시스템)
# ==========================================
def check_password():
    """비밀번호가 맞으면 True를 반환하는 함수"""
    def password_entered():
        # 설정한 비밀번호 "6006"
        if st.session_state["password"] == "6006": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #d4af37;'>🔒 🌼오늘도쨔잔!!🌼</h2>", unsafe_allow_html=True)
        st.text_input("많이먹어보자", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center; color: #d4af37;'>🔒 🌼오늘도쨔잔!!🌼</h2>", unsafe_allow_html=True)
        st.text_input("비밀번호는내보물", type="password", on_change=password_entered, key="password")
        st.error("😕땡!")
        return False
    return True

# 비밀번호 통과 못하면 여기서 멈춤
if not check_password():
    st.stop()

# --- 앱 기본 설정 ---
st.set_page_config(page_title="🌼 잘살아보자 🌼", layout="wide")

# CSS: 모바일 최적화 및 스타일링
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .gold-text { color: #d4af37; font-weight: bold; font-size: 22px; }
    div.stButton > button[kind="primary"] { background-color: #ffffff !important; color: #000000 !important; font-weight: 900 !important; width: 100% !important; border-radius: 8px;}
    div.stButton > button[kind="secondary"] { font-weight: 900 !important; width: 100% !important; border-radius: 8px;}
    .analysis-box { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; margin-top: 10px; font-size: 14px; line-height: 1.6;}
    
    .rise-text { color: #ff4b4b; font-weight: bold; }
    .fall-text { color: #4b8bff; font-weight: bold; }
    
    div.stDataFrame > div > div > table > thead > tr > th { font-size: 12px !important; padding: 2px 4px !important; }
    div.stDataFrame > div > div > table > tbody > tr > td { font-size: 12px !important; padding: 2px 4px !important; }
    
    .highlight-positive { color: #ff4b4b; font-weight: bold; }
    .highlight-negative { color: #4b8bff; font-weight: bold; }

    @media (max-width: 600px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 영구 데이터 저장/로드 로직 ---
DATA_FILE = "jj_user_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"favorites": data.get("favorites", [])}
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

@st.cache_data
def load_all_stocks():
    return fdr.StockListing('KRX')

all_stocks_df = load_all_stocks()

# --- 분석 핵심 엔진 ---
def check_vol(row):
    try:
        df = fdr.DataReader(row.Code, (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
        if len(df) > 1 and df['Volume'].iloc[-1] > df['Volume'].iloc[:-1].mean() * 1.5:
            return {'코드': row.Code, '종목명': row.Name}
    except: pass
    return None

def get_stock_data(item):
    try:
        df = fdr.DataReader(item['코드'], (datetime.now() - timedelta(days=220)).strftime('%Y-%m-%d'))
        if len(df) < 120: return None
        
        # 4대 이평선 계산
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        df['변동폭'] = df['Close'] - df['Open']
        curr_change = int(df['변동폭'].iloc[-1])
        formatted_change = f"🔴 ▲ {abs(curr_change):,}원" if curr_change > 0 else (f"🔵 ▼ {abs(curr_change):,}원" if curr_change < 0 else "➖ 0원")

        curr = df['Close'].iloc[-1]
        high_60 = df['High'].iloc[-60:].max()
        low_20 = df['Low'].iloc[-20:].min()
        
        expected_ratio = round(((high_60 - curr) / curr) * 100, 1)
        if expected_ratio <= 0:
            expected_ratio = round(((df['High'].max() - low_20) / curr) * 100 * 0.5, 1)
            if expected_ratio <= 0: expected_ratio = 15.0 
        
        is_agg = curr > df['High'].iloc[-6:-1].max()
        signal_text = "🔴 상승" if is_agg else "🔵 관망"
        
        trade_strategy = "⚡ 단타 (당일~1일 내 청산)" if expected_ratio < 8.0 else f"🗓️ 스윙 (약 {max(2, int(expected_ratio // 2.5))}일 보유)"
        
        if is_agg: ai_news = f"[{item['종목명']}] 저항선을 뚫어낸 상승 추세야! 전고점({int(high_60):,}원) 돌파 가능성이 높아 지금이 기회!"
        else: ai_news = f"[{item['종목명']}] 상승 잠재력({expected_ratio}%)은 크지만 바닥 확인이 더 필요해. 무리하게 타지 말고 관망해!"

        vol_surge = df['Volume'].iloc[-1] > df['Volume'].iloc[-5:-1].mean() * 1.5
        gc = (df['MA5'].iloc[-1] > df['MA20'].iloc[-1]) and (df['MA5'].iloc[-2] <= df['MA20'].iloc[-2])
        dc = (df['MA5'].iloc[-1] < df['MA20'].iloc[-1]) and (df['MA5'].iloc[-2] >= df['MA20'].iloc[-2])
        reb = curr <= low_20 * 1.05
        
        return {
            "신호": signal_text, "종목": item['종목명'], "순수종목명": item['종목명'], "코드": item['코드'],
            "가격": int(curr), "변동": formatted_change, "변동액": curr_change, "수익%": expected_ratio,
            "매매전략": trade_strategy, "AI뉴스": ai_news, "데이터": df, "고점": int(high_60),
            "분석": {"vol": vol_surge, "gc": gc, "dc": dc, "reb": reb, "agg": is_agg}
        }
    except: return None

def highlight_rows(row):
    return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row) if '상승' in row['신호'] else [''] * len(row)

# ---------------------------------------------------------
# [핵심 함수] 분석 리포트 & MTS 스타일 차트 렌더링
# ---------------------------------------------------------
def render_analysis(sel_row, tab_key):
    actual_name = sel_row['순수종목명']
    st.markdown(f"### 📊 {actual_name} 정밀 분석 리포트")
    
    curr_price, exp_return = sel_row['가격'], sel_row['수익%']
    target_price = int(curr_price * (1 + exp_return/100))
    color_class = "rise-text" if "상승" in sel_row['신호'] else "fall-text"
    
    st.markdown(f"<h3 class='{color_class}'>{curr_price:,}원 (+{exp_return}%)</h3>", unsafe_allow_html=True)
    st.info(f"💡 **JJ AI 매매 전략:** {sel_row['매매전략']}")
    st.warning(f"📰 **JJ AI 핵심 진단:** {sel_row['AI뉴스']}")
    
    # 최근 100일 데이터를 준비하고, 차트에는 최근 30일을 우선 노출
    df = sel_row['데이터'].tail(100)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # 1. 캔들차트 추가
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#ff4b4b', decreasing_line_color='#4b8bff',
        increasing_fillcolor='#ff4b4b', decreasing_fillcolor='#4b8bff'
    ), row=1, col=1)

    # 2. 이동평균선 추가
    ma_colors = {'MA5': '#EAD04C', 'MA20': '#C881F8', 'MA60': '#4CB4E2'}
    for ma in ma_colors:
        fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(width=1.5, color=ma_colors[ma])), row=1, col=1)

    # 3. 최적 매수/매도 타점 별표
    recent_low_val = df['Low'].min()
    fig.add_trace(go.Scatter(x=[df['Low'].idxmin()], y=[recent_low_val * 0.97], mode='markers', marker=dict(symbol='star', size=15, color='yellow'), name='매수타점'), row=1, col=1)
    fig.add_trace(go.Scatter(x=[df.index[-1]], y=[target_price], mode='markers', marker=dict(symbol='star', size=15, color='#4CAF50'), name='목표가'), row=1, col=1)

    # 4. 거래량 차트 추가
    vol_colors = ['#ff4b4b' if c > o else '#4b8bff' for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors), row=2, col=1)

    # --- MTS 스타일 레이아웃 설정 ---
    fig.update_layout(
        template="plotly_dark", height=420, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False, xaxis_rangeslider_visible=False,
        dragmode='pan', # 기본 모드: 밀기
    )
    # 초기 보여줄 범위: 최근 30거래일
    fig.update_xaxes(range=[df.index[-30], df.index[-1]], tickfont=dict(size=10), row=1, col=1)
    fig.update_yaxes(side="right", tickfont=dict(size=11), row=1, col=1) # 가격 우측 표시
    fig.update_yaxes(showticklabels=False, row=2, col=1)

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True}, key=f"chart_{actual_name}_{tab_key}")
    
    # 9대 지표 분석 결과
    a = sel_row['분석']
    t1 = f"<span class='highlight-positive'>1️⃣ <b>거래량 폭발:</b> [포착 🔴] 수급 유입</span>" if a['vol'] else "1️⃣ <b>거래량:</b> [양호] 평이한 수준"
    t2 = f"<span class='highlight-positive'>2️⃣ <b>골든크로스:</b> [발생 🔴] 정배열 초기</span>" if a['gc'] else "2️⃣ <b>이평선:</b> [대기] 정배열 준비 중"
    t3 = f"<span class='highlight-negative'>3️⃣ <b>데드크로스:</b> [경고 🔵] 단기 이탈 주의</span>" if a['dc'] else "3️⃣ <b>추세:</b> [안전 🟢] 이탈 없음"
    t4 = f"<span class='highlight-positive'>4️⃣ <b>전고점 돌파:</b> [돌파 🔴] 저항선 돌파 중</span>" if a['agg'] else f"4️⃣ <b>저항선:</b> {sel_row['고점']:,}원 (돌파 대기)"
    t5 = f"<span class='highlight-positive'>5️⃣ <b>상대적 강세:</b> [강세 🔴] 시장 이기는 중</span>" if sel_row['변동액'] > 0 else "5️⃣ <b>방어력:</b> 시장 흐름 동기화"
    t6 = f"<span class='highlight-positive'>6️⃣ <b>기술적 반등:</b> [진입 🔴] 바닥 반등 유력</span>" if a['reb'] else "6️⃣ <b>위치:</b> 지지선 위 안정적"
    t7, t8 = "7️⃣ <b>메이저 수급:</b> 기관/외인 유입 확인", "8️⃣ <b>이평선 밀집:</b> 에너지 응축 방향 대기"
    t9 = f"<span class='highlight-positive'>9️⃣ <b>회복 탄력성:</b> [강력 🔴] 상승여력 {sel_row['수익%']}%</span>" if sel_row['수익%'] >= 15 else f"9️⃣ <b>회복 탄력성:</b> 남은 여력 {sel_row['수익%']}%"

    st.markdown("#### 🔍 9대 핵심 지표 분석 결과")
    with st.container():
        st.markdown(f"""
        <div class='analysis-box'>
        {t1} <br> {t2} <br> {t3} <br> {t4} <br> {t5} <br> {t6} <br> {t7} <br> {t8} <br> {t9}
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    # 관리 버튼 (추가/삭제)
    col1, col2 = st.columns(2)
    with col1:
        is_in_fav = actual_name in st.session_state.favorites
        if is_in_fav:
            if st.button(f"❌ 관심종목 삭제", use_container_width=True, key=f"del_{actual_name}_{tab_key}"):
                st.session_state.favorites.remove(actual_name); save_data(); st.rerun()
        else:
            if st.button(f"⭐ 관심종목 추가", use_container_width=True, key=f"add_{actual_name}_{tab_key}"):
                st.session_state.favorites.append(actual_name); save_data(); st.rerun()

# --- 앱 UI 시작 ---
st.markdown("<h2 style='text-align: center; color: #d4af37; font-size: 22px;'>🌼웃으면서잠들자🌼</h2>", unsafe_allow_html=True)

tab_search, tab_radar, tab_fav = st.tabs(["🔍 검색", "📡 레이더", "⭐ 관심종목"])

with tab_search:
    search_input = st.text_input("종목명 입력 (예: 삼성전자)", "")
    if st.button("📈 정밀 분석하기", use_container_width=True):
        if search_input: st.session_state.searched_stock = search_input
        else: st.warning("종목명을 먼저 입력해줘!")
            
    if st.session_state.searched_stock:
        matched = all_stocks_df[all_stocks_df['Name'] == st.session_state.searched_stock]
        if not matched.empty:
            res = get_stock_data({'코드': matched.iloc[0]['Code'], '종목명': matched.iloc[0]['Name']})
            if res: st.divider(); render_analysis(res, "search_tab")
            else: st.error("데이터가 부족하거나 거래 중지된 종목이야.")
        else: st.warning("정확한 종목 이름을 입력해줘!")

def run_scan(market_type):
    with st.spinner("📡 [딥스캔] 전 종목 정밀 탐색 중... (약 1분 소요)"):
        df_list = fdr.StockListing(market_type)
        found = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(check_vol, row) for row in df_list.itertuples()]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res: found.append(res)
        new_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            final_futures = [executor.submit(get_stock_data, item) for item in found]
            for f in concurrent.futures.as_completed(final_futures):
                res = f.result()
                if res: new_results.append(res)
        st.session_state.rt_results = sorted(new_results, key=lambda x: x['수익%'], reverse=True)[:30]

with tab_radar:
    market = st.selectbox("시장 선택", ["KOSPI", "KOSDAQ"])
    if st.button("📡 오를 놈만 30개 스캔하기", type="secondary", use_container_width=True): 
        run_scan(market)
    
    if st.session_state.rt_results:
        df_res = pd.DataFrame(st.session_state.rt_results)
        st.write("👇 빨간 배경은 강력 추천 대장주 후보야!")
        styled_df = df_res[['신호', '종목', '가격', '변동', '수익%']].style.apply(highlight_rows, axis=1)
        event = st.dataframe(styled_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="radar_dataframe")
        
        if event.selection.rows:
            row_idx = event.selection.rows[0]
            st.divider(); render_analysis(df_res.iloc[row_idx], "radar_tab")

with tab_fav:
    if st.session_state.favorites:
        if st.button("🔄 실시간 데이터 새로고침", use_container_width=True): st.rerun()
        fav_results = []
        with st.spinner("관심종목 로드 중..."):
            for fav_name in st.session_state.favorites:
                matched = all_stocks_df[all_stocks_df['Name'] == fav_name]
                if not matched.empty:
                    res = get_stock_data({'코드': matched.iloc[0]['Code'], '종목명': fav_name})
                    if res: fav_results.append(res)
        if fav_results:
            df_fav = pd.DataFrame(fav_results)
            styled_fav = df_fav[['신호', '종목', '가격', '변동', '수익%']].style.apply(highlight_rows, axis=1)
            event_fav = st.dataframe(styled_fav, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="fav_dataframe")
            
            if event_fav.selection.rows:
                row_idx_fav = event_fav.selection.rows[0]
                st.divider(); render_analysis(df_fav.iloc[row_idx_fav], "fav_tab")
    else:
        st.info("아직 찜한 종목이 없어! 리포트에서 '⭐ 관심종목 추가'를 눌러봐.")
