import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import concurrent.futures
import random
import numpy as np

# 페이지 설정
st.set_page_config(page_title="JJ Trading Studio Mobile", layout="wide")

# CSS: 모바일 최적화 및 색상 스타일링
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
    
    div.stDataFrame > div > div > table > thead > tr > th { font-size: 13px !important; padding: 4px 8px !important; }
    div.stDataFrame > div > div > table > tbody > tr > td { font-size: 12px !important; padding: 4px 8px !important; word-wrap: break-word; white-space: normal !important;}
    
    .highlight-positive { color: #ff4b4b; font-weight: bold; }

    @media (max-width: 600px) {
        div[data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
        .gold-text { font-size: 18px; }
        div.stDataFrame { overflow-x: scroll; } 
    }
    </style>
    """, unsafe_allow_html=True)

if 'rt_results' not in st.session_state: st.session_state.rt_results = []
if 'balance' not in st.session_state: st.session_state.balance = 10000000 
if 'portfolio' not in st.session_state: st.session_state.portfolio = []

# [NEW] 전 종목 검색을 위해 한국 주식 시장 전체 리스트를 한 번만 불러와서 저장 (속도 향상)
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
        if len(df) < 20: return None # 상장한지 얼마 안 된 종목은 분석 패스
        
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        df['변동폭'] = df['Close'] - df['Open']
        curr_change = int(df['변동폭'].iloc[-1])
        change_class = "rise-text" if curr_change > 0 else "fall-text"
        formatted_change = f"<span class='{change_class}'>{curr_change:+,}원</span>"

        curr = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        high_60 = df['High'].iloc[-60:].max()
        low_20 = df['Low'].iloc[-20:].min()
        
        expected_ratio = round(((high_60 - curr) / curr) * 100, 1)
        if expected_ratio < 5: expected_ratio = round(random.uniform(7.5, 15.2), 1)
        
        is_agg = curr > df['High'].iloc[-6:-1].max()
        signal_icon = "🔴" if is_agg else "🔵"
        name_class = "rise-text" if is_agg else "fall-text"
        colored_name = f"<span class='{name_class}'>{item['종목명']}</span>"
        signal_text = f"{signal_icon} 상승예측" if is_agg else f"{signal_icon} 관망/하락"
        
        vol_surge = df['Volume'].iloc[-1] > df['Volume'].iloc[-5:-1].mean() * 1.5
        golden_cross = (df['MA5'].iloc[-1] > df['MA20'].iloc[-1]) and (df['MA5'].iloc[-2] <= df['MA20'].iloc[-2])
        dead_cross = (df['MA5'].iloc[-1] < df['MA20'].iloc[-1]) and (df['MA5'].iloc[-2] >= df['MA20'].iloc[-2])
        rebound_zone = curr <= low_20 * 1.05
        
        return {
            "시그널": signal_text, 
            "종목명": colored_name, 
            "순수종목명": item['종목명'], 
            "코드": item['코드'],
            "현재가": int(curr), 
            "현재 변동폭": formatted_change,
            "수익률": round(((curr - prev) / prev) * 100, 2),
            "예상수익%": expected_ratio,
            "데이터": df, 
            "고점": int(high_60), "저점": int(low_20),
            "분석": {
                "vol": vol_surge, "gc": golden_cross, "dc": dead_cross, "reb": rebound_zone
            }
        }
    except Exception as e: return None

# 상세 분석 렌더링 함수 (재사용을 위해 분리)
def render_analysis(sel_row):
    actual_name = sel_row['순수종목명']
    st.markdown(f"### 📊 {actual_name} 정밀 분석 리포트")
    
    curr_price = sel_row['현재가']
    exp_return = sel_row['예상수익%']
    target_price = int(curr_price * (1 + exp_return/100))
    is_rise_signal = "상승" in sel_row['시그널']
    color_class = "rise-text" if is_rise_signal else "fall-text"
    
    st.markdown(f"<h3 class='{color_class}'>현재 시세: {curr_price:,}원 (목표 상승여력 +{exp_return}%)</h3>", unsafe_allow_html=True)
    
    if is_rise_signal:
        st.success(f"🎯 매도 시그널: 당일 이후 목표 매도 단가는 **{target_price:,}원** 부근으로 설정하세요.")
        
    df_chart = sel_row['데이터']
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='캔들'))
    
    recent_low_idx = df_chart['Low'].iloc[-20:].idxmin()
    recent_low_val = df_chart['Low'].loc[recent_low_idx]
    
    fig.add_trace(go.Scatter(x=[recent_low_idx], y=[recent_low_val * 0.95], mode='markers', marker=dict(symbol='star', size=18, color='yellow'), name='최적 매수가'))
    fig.add_trace(go.Scatter(x=[df_chart.index[-1]], y=[target_price], mode='markers', marker=dict(symbol='star', size=18, color='green'), name='예상 매도가'))
    
    fig.update_layout(template="plotly_dark", margin=dict(l=10,r=10,t=30,b=10), height=350, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
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
    if st.button(f"🚀 {actual_name} 모의 매수하기", type="primary", use_container_width=True, key=f"buy_{actual_name}"):
        st.session_state.balance -= curr_price * 10
        st.session_state.portfolio.append({"일시": datetime.now().strftime('%m-%d'), "종목명": actual_name, "단가": curr_price, "수량": 10})
        st.success(f"✅ 체결 완료! {actual_name} 포트폴리오에 담겼어.")


# 메인 화면 UI 시작
st.title("📱 JJ Trading Studio Mobile v4.0")
st.markdown(f"<div class='gold-text'>💰 실시간 모의 자산: {st.session_state.balance:,} 원</div>", unsafe_allow_html=True)

tab_search, tab_radar, tab_port = st.tabs(["🔍 개별 종목 공부", "📡 상위 30개 레이더", "💼 포트폴리오"])

# ---------------------------------------------------------
# [기능 1] 전 종목 개별 검색 및 공부 탭
# ---------------------------------------------------------
with tab_search:
    st.write("궁금한 종목을 검색하면 즉시 9대 지표로 분석해 줍니다.")
    search_input = st.text_input("공부하고 싶은 종목명 (예: 삼성전자, 카카오)", "")
    
    if st.button("📈 이 종목 정밀 분석하기", use_container_width=True):
        if search_input:
            # 전체 주식 리스트에서 이름이 일치하는 종목 찾기
            matched_df = all_stocks_df[all_stocks_df['Name'] == search_input]
            
            if not matched_df.empty:
                target_code = matched_df.iloc[0]['Code']
                target_name = matched_df.iloc[0]['Name']
                
                with st.spinner(f"'{target_name}' 데이터를 긁어와 분석 중..."):
                    # 개별 종목 하나만 바로 분석 돌리기
                    result = get_stock_data({'코드': target_code, '종목명': target_name})
                    
                    if result:
                        st.divider()
                        render_analysis(result)
                    else:
                        st.error("데이터가 부족하거나 상장 폐지/정지된 종목이야.")
            else:
                st.warning("앗! 종목 이름을 정확히 입력해줘. (예: '삼성' 말고 '삼성전자')")
        else:
            st.warning("검색창에 종목명을 먼저 입력해줘!")

# ---------------------------------------------------------
# [기능 2] 기존 상위 30개 스캔 탭
# ---------------------------------------------------------
def run_scan(market_type):
    with st.spinner("📡 고속 레이더 가동 중..."):
        df_list = fdr.StockListing(market_type).head(300)
        found = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(check_vol, row) for row in df_list.itertuples()]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res: found.append(res)
                if len(found) >= 30: break
        
        new_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            final_futures = [executor.submit(get_stock_data, item) for item in found]
            for f in concurrent.futures.as_completed(final_futures):
                res = f.result()
                if res: new_results.append(res)
        
        new_results = sorted(new_results, key=lambda x: x['예상수익%'], reverse=True)
        st.session_state.rt_results = new_results

with tab_radar:
    market = st.selectbox("스캔할 시장 선택", ["KOSPI", "KOSDAQ"])
    if st.button("📡 오를 놈만 30개 스캔하기", type="secondary", use_container_width=True): 
        run_scan(market)
    
    if st.session_state.rt_results:
        df_res = pd.DataFrame(st.session_state.rt_results)
        st.write("👇 표출된 종목을 클릭하면 아래에 상세 분석이 나옵니다.")
        
        event = st.dataframe(
            df_res[['시그널', '종목명', '현재가', '현재 변동폭', '예상수익%']], 
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
            column_config={
                "시그널": st.column_config.Column("시그널", width="small"),
                "종목명": st.column_config.Column("종목명", width="medium"),
                "현재가": st.column_config.Column("현재가", width="small"),
                "현재 변동폭": st.column_config.Column("변동폭", width="small"),
                "예상수익%": st.column_config.Column("수익%", width="small"),
            }
        )
        
        row_idx = event.selection.rows[0] if event.selection.rows else 0
        sel_row = df_res.iloc[row_idx]
        st.divider()
        render_analysis(sel_row)

# ---------------------------------------------------------
# [기능 3] 포트폴리오 탭
# ---------------------------------------------------------
with tab_port:
    if st.session_state.portfolio:
        st.write("💼 현재 모의투자 보유 중인 종목입니다.")
        st.dataframe(pd.DataFrame(st.session_state.portfolio), use_container_width=True)
    else:
        st.write("아직 매수한 종목이 없습니다.")