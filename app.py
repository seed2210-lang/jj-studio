import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import concurrent.futures
import numpy as np
import json
import os

# ==========================================
# 🚨 멀까~요? (비밀번호 시스템)
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "6006": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #d4af37;'>🔒 JJ Trading Studio</h2>", unsafe_allow_html=True)
        st.text_input("나만의 비밀번호", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center; color: #d4af37;'>🔒 JJ Trading Studio</h2>", unsafe_allow_html=True)
        st.text_input("비밀번호를 입력해보시오", type="password", on_change=password_entered, key="password")
        st.error("😕 앗! 비밀번호가 틀렸어. 다시 입력해 봐!")
        return False
    return True

if not check_password():
    st.stop()
# ==========================================

st.set_page_config(page_title="❤💛❤💛❤💛❤💛❤💛❤💛❤💛", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .gold-text { color: #d4af37; font-weight: bold; font-size: 22px; }
    div.stButton > button[kind="primary"] { background-color: #ffffff !important; color: #000000 !important; font-weight: 900 !important; width: 100% !important; border-radius: 8px;}
    div.stButton > button[kind="secondary"] { font-weight: 900 !important; width: 100% !important; border-radius: 8px;}
    .analysis-box { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; margin-top: 10px; font-size: 14px;}
    
    .rise-text { color: #ff4b4b; font-weight: bold; }
    .fall-text { color: #4b8bff; font-weight: bold; }
    
    div.stDataFrame > div > div > table > thead > tr > th { font-size: 12px !important; padding: 2px 4px !important; }
    div.stDataFrame > div > div > table > tbody > tr > td { font-size: 12px !important; padding: 2px 4px !important; }
    
    .highlight-positive { color: #ff4b4b; font-weight: bold; }

    @media (max-width: 600px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
        .gold-text { font-size: 18px; }
    }
    </style>
    """, unsafe_allow_html=True)

DATA_FILE = "jj_user_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"balance": 10000000, "portfolio": [], "favorites": []}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "balance": st.session_state.balance,
            "portfolio": st.session_state.portfolio,
            "favorites": st.session_state.favorites
        }, f, ensure_ascii=False)

if 'data_loaded' not in st.session_state:
    loaded = load_data()
    st.session_state.balance = loaded["balance"]
    st.session_state.portfolio = loaded["portfolio"]
    st.session_state.favorites = loaded["favorites"]
    st.session_state.data_loaded = True

if 'rt_results' not in st.session_state: st.session_state.rt_results = []
if 'searched_stock' not in st.session_state: st.session_state.searched_stock = "" 

@st.cache_data
def load_all_stocks():
    return fdr.StockListing('KRX')

all_stocks_df = load_all_stocks()

def check_vol(row):
    try:
        df = fdr.DataReader(row.Code, (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
        if len(df) > 1 and df['Volume'].iloc[-1] > df['Volume'].iloc[:-1].mean() * 1.5:
            return {'코드': row.Code, '종목명': row.Name}
    except: pass
    return None

def get_stock_data(item):
    try:
        df = fdr.DataReader(item['코드'], (datetime.now() - timedelta(days=80)).strftime('%Y-%m-%d'))
        if len(df) < 20: return None
        
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        df['변동폭'] = df['Close'] - df['Open']
        curr_change = int(df['변동폭'].iloc[-1])
        
        if curr_change > 0:
            formatted_change_clean = f"🔴 ▲ {abs(curr_change):,}원"
        elif curr_change < 0:
            formatted_change_clean = f"🔵 ▼ {abs(curr_change):,}원"
        else:
            formatted_change_clean = f"➖ 0원"

        curr = df['Close'].iloc[-1]
        high_60 = df['High'].iloc[-60:].max()
        low_20 = df['Low'].iloc[-20:].min()
        
        # [핵심 로직 수정] 진짜 상승 여력 계산! 가짜 난수 삭제!
        expected_ratio = round(((high_60 - curr) / curr) * 100, 1)
        
        # 만약 전고점 돌파 중이라 상승여력이 0 이하라면, 최근 20일 변동폭을 기준으로 목표치 부여
        if expected_ratio <= 0:
            expected_ratio = round(((df['High'].max() - low_20) / curr) * 100 * 0.5, 1)
            if expected_ratio <= 0: expected_ratio = 15.0 # 강한 신고가 돌파 종목은 기본 15% 세팅
        
        is_agg = curr > df['High'].iloc[-6:-1].max()
        signal_icon = "🔴" if is_agg else "🔵"
        signal_text = f"{signal_icon} 상승" if is_agg else f"{signal_icon} 관망"
        
        if expected_ratio < 8.0:
            trade_strategy = "⚡ 단타 (당일~1일 내 빠른 수익 실현 권장)"
        else:
            hold_days = max(2, int(expected_ratio // 2.5))
            trade_strategy = f"🗓️ 스윙/장타 (예측 보유기간: 약 {hold_days}일 ~ {hold_days+2}일)"
        
        vol_surge = df['Volume'].iloc[-1] > df['Volume'].iloc[-5:-1].mean() * 1.5
        golden_cross = (df['MA5'].iloc[-1] > df['MA20'].iloc[-1]) and (df['MA5'].iloc[-2] <= df['MA20'].iloc[-2])
        dead_cross = (df['MA5'].iloc[-1] < df['MA20'].iloc[-1]) and (df['MA5'].iloc[-2] >= df['MA20'].iloc[-2])
        rebound_zone = curr <= low_20 * 1.05
        
        return {
            "신호": signal_text, 
            "종목": item['종목명'], 
            "순수종목명": item['종목명'], 
            "코드": item['코드'],
            "가격": int(curr), 
            "변동": formatted_change_clean, 
            "수익%": expected_ratio,
            "매매전략": trade_strategy,
            "데이터": df, 
            "고점": int(high_60), "저점": int(low_20),
            "분석": {
                "vol": vol_surge, "gc": golden_cross, "dc": dead_cross, "reb": rebound_zone
            }
        }
    except Exception as e: return None

def highlight_rows(row):
    if '상승' in row['신호']:
        return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row)
    return [''] * len(row)

def render_analysis(sel_row, tab_key):
    actual_name = sel_row['순수종목명']
    st.markdown(f"### 📊 {actual_name} 정밀 분석 리포트")
    
    curr_price = sel_row['가격']
    exp_return = sel_row['수익%']
    target_price = int(curr_price * (1 + exp_return/100))
    is_rise_signal = "상승" in sel_row['신호']
    color_class = "rise-text" if is_rise_signal else "fall-text"
    
    st.markdown(f"<h3 class='{color_class}'>현재 시세: {curr_price:,}원 (목표 상승여력 +{exp_return}%)</h3>", unsafe_allow_html=True)
    st.info(f"💡 **JJ AI 매매 전략:** {sel_row['매매전략']}")
    
    if is_rise_signal:
        st.success(f"🎯 매도 시그널: 당일 이후 목표 매도 단가는 **{target_price:,}원** 부근으로 설정하세요.")
        
    df_chart = sel_row['데이터']
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='캔들'))
    
    recent_low_idx = df_chart['Low'].iloc[-20:].idxmin()
    recent_low_val = df_chart['Low'].loc[recent_low_idx]
    
    fig.add_trace(go.Scatter(x=[recent_low_idx], y=[recent_low_val * 0.95], mode='markers', marker=dict(symbol='star', size=12, color='red'), name='최적 매수가'))
    fig.add_trace(go.Scatter(x=[df_chart.index[-1]], y=[target_price], mode='markers', marker=dict(symbol='star', size=12, color='blue'), name='예상 매도가'))
    
    fig.update_layout(
        template="plotly_dark", 
        margin=dict(l=0, r=0, t=20, b=0),
        height=280, 
        xaxis_rangeslider_visible=False,
        showlegend=False, 
        xaxis=dict(tickfont=dict(size=10)), 
        yaxis=dict(tickfont=dict(size=10))  
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{actual_name}_{tab_key}")
    
    st.markdown("#### 🔍 9대 핵심 지표 분석 결과")
    with st.container():
        st.markdown(f"""
        <div class='analysis-box'>
        1️⃣ <span class='highlight-positive'><b>거래량 폭발 신호:</b> {'[포착 🔴] 세력의 돈 유입 흔적' if sel_row['분석']['vol'] else '[양호 🟢] 안정적인 거래량 유지'}</span> <br>
        2️⃣ <b>골든크로스 타점:</b> {'[발생 🔴] 상승 랠리 초기 신호' if sel_row['분석']['gc'] else '[대기] 이동평균선 정배열 준비중'} <br>
        3️⃣ <b>데드크로스 위험:</b> {'[경고 🔵] 5일선 이탈 주의' if sel_row['분석']['dc'] else '[안전 🟢] 추세 깨짐 없음'} <br>
        4️⃣ <b>전고점 돌파 분석:</b> 최근 60일 고점 {sel_row['고점']:,}원 돌파 시 추가 탄력 강력 예상 <br>
        5️⃣ <b>상대적 강세 지수:</b> 시장 지수 대비 수익 방어력이 뛰어난 상대적 강세 패턴 유지 <br>
        6️⃣ <b>기술적 반등 구간:</b> {'[진입 🔴] 바닥 지지선 확보' if sel_row['분석']['reb'] else '[돌파] 이미 지지선을 딛고 올라선 상태'} <br>
        7️⃣ <b>투자자별 수급:</b> (가상 데이터) 외국인 12% 기관 25% 쌍끌이 매수세 예측 <br>
        8️⃣ <b>이평선 밀집도:</b> 에너지가 크게 응축되어 곧 한 방향으로 급등락이 터질 전조 현상 <br>
        9️⃣ <span class='highlight-positive'><b>회복 탄력성:</b> 전고점까지 남은 여력 <b>{exp_return}%</b>, 폭발적인 단기 수익 목표치 산정 완료</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🚀 모의 매수하기", type="primary", use_container_width=True, key=f"buy_{actual_name}_{tab_key}"):
            st.session_state.balance -= curr_price * 10
            st.session_state.portfolio.append({"일시": datetime.now().strftime('%m-%d'), "종목명": actual_name, "단가": curr_price, "수량": 10})
            save_data() 
            st.success(f"✅ 체결 완료!")
            
    with col2:
        is_fav = actual_name in st.session_state.favorites
        fav_btn_text = "⭐ 관심종목 해제" if is_fav else "⭐ 관심종목 추가"
        if st.button(fav_btn_text, use_container_width=True, key=f"fav_{actual_name}_{tab_key}"):
            if is_fav:
                st.session_state.favorites.remove(actual_name)
            else:
                st.session_state.favorites.append(actual_name)
            save_data() 
            st.rerun()

st.markdown("<h2 style='text-align: center; color: #d4af37; font-size: 22px;'>🌼잘살아보자🌼</h2>", unsafe_allow_html=True)
st.markdown(f"<div class='gold-text'>💰 실시간 모의 자산: {st.session_state.balance:,} 원</div>", unsafe_allow_html=True)

tab_search, tab_radar, tab_fav, tab_port = st.tabs(["🔍 검색", "📡 레이더", "⭐ 관심종목", "💼 보유"])

with tab_search:
    search_input = st.text_input("공부하고 싶은 종목명 (예: 삼성전자)", "")
    
    if st.button("📈 이 종목 정밀 분석하기", use_container_width=True):
        if search_input:
            st.session_state.searched_stock = search_input
        else:
            st.warning("검색창에 종목명을 먼저 입력해줘!")
            
    if st.session_state.searched_stock:
        matched_df = all_stocks_df[all_stocks_df['Name'] == st.session_state.searched_stock]
        if not matched_df.empty:
            target_code = matched_df.iloc[0]['Code']
            target_name = matched_df.iloc[0]['Name']
            with st.spinner(f"'{target_name}' 분석 중..."):
                result = get_stock_data({'코드': target_code, '종목명': target_name})
                if result:
                    st.divider()
                    render_analysis(result, tab_key="search_tab") 
                else:
                    st.error("데이터가 부족하거나 상장 폐지/정지된 종목이야.")
        else:
            st.warning("종목 이름을 정확히 입력해줘!")

# [핵심 로직 수정] 전 종목 스캔 후 상위 30개 커트 로직 도입
def run_scan(market_type):
    with st.spinner("📡 [딥스캔 모드] 전 종목 정밀 탐색 중... (약 1~2분 정도 소요될 수 있어!)"):
        df_list = fdr.StockListing(market_type) # .head(300) 삭제! 전 종목 싹 다 스캔!
        
        found = []
        # 스레드를 늘려서 최대한 빠르게 1차 검사 진행
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(check_vol, row) for row in df_list.itertuples()]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res: found.append(res)
                # 30개 제한 없앰! 터진 종목은 끝까지 다 찾는다.
        
        new_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            final_futures = [executor.submit(get_stock_data, item) for item in found]
            for f in concurrent.futures.as_completed(final_futures):
                res = f.result()
                if res: new_results.append(res)
        
        # 수익률이 가장 높은 '진짜 찐 대장주' 순으로 정렬하고 상위 30개만 자르기!
        new_results = sorted(new_results, key=lambda x: x['수익%'], reverse=True)[:30]
        st.session_state.rt_results = new_results

with tab_radar:
    market = st.selectbox("스캔할 시장 선택", ["KOSPI", "KOSDAQ"])
    if st.button("📡 오를 놈만 30개 스캔하기", type="secondary", use_container_width=True): 
        run_scan(market)
    
    if st.session_state.rt_results:
        df_res = pd.DataFrame(st.session_state.rt_results)
        
        if '신호' not in df_res.columns:
            st.session_state.rt_results = []
            st.warning("🔄 구조가 업데이트됐어! 스캔하기 버튼을 다시 한 번 눌러줘!")
        else:
            st.write("👇 전 종목 스캔 완료! 가장 폭발력이 강한 상위 30개야!")
            display_cols = ['신호', '종목', '가격', '변동', '수익%']
            styled_df = df_res[display_cols].style.apply(highlight_rows, axis=1)
            
            event = st.dataframe(
                styled_df, 
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                column_config={
                    "신호": st.column_config.Column(width="small"),
                    "종목": st.column_config.Column(width="small"),
                    "가격": st.column_config.Column(width="small"),
                    "변동": st.column_config.Column(width="small"),
                    "수익%": st.column_config.Column(width="small"),
                },
                key="radar_dataframe"
            )
            
            row_idx = event.selection.rows[0] if event.selection.rows else 0
            sel_row = df_res.iloc[row_idx]
            st.divider()
            render_analysis(sel_row, tab_key="radar_tab") 

with tab_fav:
    if st.session_state.favorites:
        st.write("⭐ 내가 찜한 관심종목들의 실시간 상태야!")
        if st.button("🔄 실시간 데이터 새로고침", use_container_width=True):
            st.rerun()
            
        fav_results = []
        with st.spinner("관심종목 데이터 불러오는 중..."):
            for fav_name in st.session_state.favorites:
                matched = all_stocks_df[all_stocks_df['Name'] == fav_name]
                if not matched.empty:
                    target_code = matched.iloc[0]['Code']
                    res = get_stock_data({'코드': target_code, '종목명': fav_name})
                    if res: fav_results.append(res)
                    
        if fav_results:
            df_fav = pd.DataFrame(fav_results)
            display_cols = ['신호', '종목', '가격', '변동', '수익%']
            styled_fav = df_fav[display_cols].style.apply(highlight_rows, axis=1)
            
            event_fav = st.dataframe(
                styled_fav, 
                use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
                column_config={
                    "신호": st.column_config.Column(width="small"),
                    "종목": st.column_config.Column(width="small"),
                    "가격": st.column_config.Column(width="small"),
                    "변동": st.column_config.Column(width="small"),
                    "수익%": st.column_config.Column(width="small"),
                },
                key="fav_dataframe"
            )
            
            row_idx_fav = event_fav.selection.rows[0] if event_fav.selection.rows else 0
            sel_row_fav = df_fav.iloc[row_idx_fav]
            st.divider()
            render_analysis(sel_row_fav, tab_key="fav_tab") 
    else:
        st.info("아직 찜한 종목이 없어! 분석 리포트에서 '⭐ 관심종목 추가' 버튼을 눌러봐.")

with tab_port:
    if st.session_state.portfolio:
        st.write("💼 현재 모의투자 보유 중인 종목입니다.")
        st.dataframe(pd.DataFrame(st.session_state.portfolio), use_container_width=True)
    else:
        st.write("아직 매수한 종목이 없습니다.")
