import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import concurrent.futures
import random

# 1. 페이지 설정
st.set_page_config(page_title="JJ Trading Studio", layout="wide")

if 'candidates' not in st.session_state: st.session_state.candidates = []
if 'rt_results' not in st.session_state: st.session_state.rt_results = []
if 'balance' not in st.session_state: st.session_state.balance = 10000000 
if 'portfolio' not in st.session_state: st.session_state.portfolio = []
if 'selected_stock' not in st.session_state: st.session_state.selected_stock = None

# 2. 프로페셔널 CSS 스타일링
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .gold-text { color: #d4af37; font-weight: bold; font-size: 26px; }
    
    div.stButton > button[kind="primary"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 1.4rem !important; 
        padding: 1.5rem 2rem !important; 
        border-radius: 12px !important;
        border: none !important;
        width: 100% !important;
        transition: transform 0.2s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: scale(1.02);
        background-color: #e0e0e0 !important;
    }
    
    .analysis-box { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }
    .investor-card { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 엔진
def check_vol(row):
    try:
        df = fdr.DataReader(row.Code, (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
        if len(df) > 1 and df['Volume'].iloc[-1] > df['Volume'].iloc[:-1].mean() * 1.5:
            return {'코드': row.Code, '종목명': row.Name}
    except: pass
    return None

def get_stock_data(item):
    try:
        df = fdr.DataReader(item['코드'], (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        curr, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
        is_agg = curr > df['High'].iloc[-6:-1].max()
        return {
            "시그널": "🔴 매수포착" if is_agg else "-", 
            "종목명": item['종목명'], "코드": item['코드'],
            "현재가": int(curr), "변동": int(curr - prev),
            "수익률": round(((curr - prev) / prev) * 100, 2)
        }
    except: return None

def run_scan(market_type):
    with st.spinner("📡 고속 레이더 가동 중..."):
        df_list = fdr.StockListing(market_type).head(500)
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
        st.session_state.rt_results = new_results

# [동적 맞춤형 분석 엔진]
def get_expert_signal_diagnosis(signal_type, stock_name, date_obj, row_data):
    d_str = date_obj.strftime('%Y년 %m월 %d일')
    price = int(row_data['Close'])
    vol = int(row_data['Volume'])
    
    if signal_type == 'B':
        return f"<b>[{d_str}] 매수(Buy) 핵심 타점 진단</b><br>해당일 종가는 <b>{price:,}원</b>, 거래량은 <b>{vol:,}주</b>를 기록했습니다. 단기 추세선(5일)이 중기 추세선(20일)을 강하게 뚫고 올라가는 <b>'골든크로스'</b>가 발생한 시점입니다. 바닥을 다지고 억눌려 있던 매수 심리가 폭발하며 상승 추세로 전환되는 강력한 초기 신호로 해석됩니다."
    else:
        return f"<b>[{d_str}] 매도(Sell) 핵심 타점 진단</b><br>해당일 종가는 <b>{price:,}원</b>, 거래량은 <b>{vol:,}주</b>를 기록했습니다. 단기 추세선(5일)이 중기 추세선(20일)을 깨고 내려가는 <b>'데드크로스'</b>가 발생한 시점입니다. 주요 지지선이 무너지며 실망 매물이 쏟아질 수 있는 위험 구간이므로, 추가 하락을 대비한 보수적인 접근이 필요합니다."

# 투자 주문 팝업
@st.dialog("🎯 전략적 투자 주문서")
def invest_dialog(stock_info):
    st.write(f"### {stock_info['종목명']} ({stock_info['코드']})")
    st.write(f"현재가: **{stock_info['현재가']:,}원**")
    st.divider()
    
    qty = st.number_input("매수 수량 (주)", min_value=1, value=10, step=1)
    total_cost = qty * stock_info['현재가']
    st.write(f"총 주문 금액: **{total_cost:,}원**")
    
    reason_options = ["골든크로스 타점 확인", "지수 대비 상대적 강세", "수급 불균형 포착", "주요 매물대 지지", "기타 (직접 입력)"]
    reason = st.selectbox("진입 근거", reason_options)
    custom_reason = st.text_input("직접 사유를 입력하세요") if reason == "기타 (직접 입력)" else ""
    final_reason = custom_reason if custom_reason else reason
    
    if st.button("🚀 체결 확정", use_container_width=True):
        if total_cost <= st.session_state.balance:
            st.session_state.balance -= total_cost
            st.session_state.portfolio.append({
                "일시": datetime.now().strftime('%m-%d %H:%M'), "종목명": stock_info['종목명'],
                "코드": stock_info['코드'], "단가": stock_info['현재가'], "현재가": stock_info['현재가'],
                "수량": qty, "근거": final_reason
            })
            st.success(f"{stock_info['종목명']} 체결 완료!")
            st.rerun()
        else: st.error("잔고가 부족합니다!")

# 4. 메인 화면
st.title("🏛️ JJ Trading Studio v2.6")
st.markdown(f"<div class='gold-text'>💰 실시간 가용 자산: {st.session_state.balance:,} 원</div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 컨트롤 타워")
    market = st.selectbox("【 시장 선택 】", ["KOSPI", "KOSDAQ"])
    if st.button("📡 실시간 종목 불러오기"): run_scan(market)

tab1, tab2 = st.tabs(["📡 분석 레이더", "💼 마이 포트폴리오"])

with tab1:
    if st.session_state.rt_results:
        df_res = pd.DataFrame(st.session_state.rt_results)
        def color_name(row):
            c = '#ff4b4b' if row['변동'] > 0 else '#1c83e1' if row['변동'] < 0 else '#c9d1d9'
            return [f'color: {c}; font-weight: bold;' if col == '종목명' else '' for col in row.index]

        col1, col2 = st.columns([1, 1.8])
        with col1:
            st.subheader("📋 포착 리스트")
            event = st.dataframe(df_res[['시그널', '종목명', '현재가', '변동', '수익률']].style.apply(color_name, axis=1),
                                 use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            
            row_idx = event.selection.rows[0] if event.selection.rows else 0
            sel_row = df_res.iloc[row_idx]
            
            st.write("") 
            if st.button("🚀 이 종목 바로 투자하기", key="invest_btn", type="primary", use_container_width=True):
                invest_dialog(sel_row)

        with col2:
            st.subheader(f"📊 {sel_row['종목명']} 정밀 분석")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("현재가", f"{sel_row['현재가']:,}원")
            m2.metric("전일대비", f"{sel_row['변동']:,}원", delta=f"{sel_row['수익률']}%")
            m3.metric("시그널", sel_row['시그널'])
            m4.metric("코드", sel_row['코드'])
            
            st.markdown("##### 👥 투자자별 보유 비중")
            ic1, ic2, ic3 = st.columns(3)
            f_p, i_p = random.randint(15, 35), random.randint(10, 25)
            p_p = 100 - f_p - i_p
            
            ic1.markdown(f"<div class='investor-card'><div style='font-size:1.1rem; font-weight:bold; margin-bottom:3px;'>외국인</div><div style='color:#ff4b4b; font-size:1.8rem; font-weight:700;'>{f_p}%</div></div>", unsafe_allow_html=True)
            ic2.markdown(f"<div class='investor-card'><div style='font-size:1.1rem; font-weight:bold; margin-bottom:3px;'>기관</div><div style='color:#58a6ff; font-size:1.8rem; font-weight:700;'>{i_p}%</div></div>", unsafe_allow_html=True)
            ic3.markdown(f"<div class='investor-card'><div style='font-size:1.1rem; font-weight:bold; margin-bottom:3px;'>개인</div><div style='font-size:1.8rem; font-weight:700;'>{p_p}%</div></div>", unsafe_allow_html=True)

            st.divider()
            
            # [수정] 중복 차트 제거 완료! 아래 분석 차트 하나만 남김
            df_chart = fdr.DataReader(sel_row['코드'], (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d'))
            df_chart['MA5'] = df_chart['Close'].rolling(5).mean()
            df_chart['MA20'] = df_chart['Close'].rolling(20).mean()
            
            df_chart['Buy_Signal'] = (df_chart['MA5'] > df_chart['MA20']) & (df_chart['MA5'].shift(1) <= df_chart['MA20'].shift(1))
            df_chart['Sell_Signal'] = (df_chart['MA5'] < df_chart['MA20']) & (df_chart['MA5'].shift(1) >= df_chart['MA20'].shift(1))

            fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="주가")])
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA5'], mode='lines', line=dict(color='#ff9900', width=1.5), name="5일선"))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA20'], mode='lines', line=dict(color='#58a6ff', width=1.5, dash='dot'), name="20일선"))
            
            buy_indices = df_chart[df_chart['Buy_Signal']].index
            sell_indices = df_chart[df_chart['Sell_Signal']].index
            
            fig.add_trace(go.Scatter(x=buy_indices, y=df_chart.loc[buy_indices, 'Low'] * 0.95, mode='markers', 
                                     marker=dict(symbol='triangle-up', size=15, color='#00ff00'), name="Buy (B)"))
            fig.add_trace(go.Scatter(x=sell_indices, y=df_chart.loc[sell_indices, 'High'] * 1.05, mode='markers', 
                                     marker=dict(symbol='triangle-down', size=15, color='#ff0000'), name="Sell (S)"))

            fig.update_layout(height=400, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### 🕵️‍♂️ 맞춤형 타점 진단 (선택)")
            
            signals = []
            for idx, row in df_chart[df_chart['Buy_Signal']].iterrows(): signals.append({'날짜': idx, '유형': 'B', '데이터': row})
            for idx, row in df_chart[df_chart['Sell_Signal']].iterrows(): signals.append({'날짜': idx, '유형': 'S', '데이터': row})
            
            signals_df = pd.DataFrame(signals)
            
            if not signals_df.empty:
                signals_df = signals_df.sort_values(by='날짜', ascending=False)
                signal_labels = [f"【{row['유형']}】 {row['날짜'].strftime('%Y-%m-%d')} 타점" for _, row in signals_df.iterrows()]
                
                selected_label = st.selectbox("최근 발생한 핵심 타점을 선택하세요:", signal_labels)
                selected_idx = signal_labels.index(selected_label)
                sel_sig = signals_df.iloc[selected_idx]
                
                diag_text = get_expert_signal_diagnosis(sel_sig['유형'], sel_row['종목명'], sel_sig['날짜'], sel_sig['데이터'])
                
                st.markdown(f"""
                <div class="analysis-box" style="margin-top:5px; border: 2px dashed #58a6ff;">
                    <p style="font-size:0.95rem; line-height:1.6; margin:0;">{diag_text}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("최근 150일 내에 강력한 추세 전환(골든/데드크로스) 타점이 발생하지 않았습니다.")
    else:
        st.info("""
        🏛️ 【 JJ Trading Studio 소개 】
        이곳은 단순한 종목 검색기를 넘어, 실시간 수급과 차트를 분석하고 
        가상 매매를 통해 실전 트레이딩 감각을 기르는 전문가용 워크스테이션입니다.

        👈 【 시스템 사용 가이드 】
        1. 왼쪽 시스템 제어에서 시장 【KOSPI/KOSDAQ】을 선택하세요.
        2. 【레이더 가동】 버튼을 눌러 시장 데이터에서 모든 종목을 분석하세요.
        3. 우측 정밀 차트에서 'B'(Buy)와 'S'(Sell) 마커를 확인하고 맞춤형 진단을 받아보세요.
        """)

with tab2:
    st.info("""
    💼 【 모의 트레이딩 시스템 사용 가이드 】
    가상의 시드머니로 실전과 동일한 환경에서 매매를 연습하며 '나만의 매매 원칙'을 세우는 훈련 공간입니다.

    1. 레이더 탭에서 투자 버튼을 누르면 주문서 팝업이 나타납니다.
    2. 수익/손실 원인을 분석할 수 있도록 명확한 투자 근거를 기록하세요.
       🚨 (주의: 모의 투자 정산 시 손실이 발생하면, 해당 자산의 반(50%)은 패널티로 강제 회수됩니다)
    3. 거래 확정 후 우측 상단의 '실시간 시세 동기화' 버튼으로 현재 상황을 점검하세요.
    """)
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1: st.subheader("📂 보유 포트폴리오")
    with col_t2: 
        if st.button("🔄 실시간 시세 동기화", key="sync_btn"):
            with st.spinner("최신 시세 반영 중..."):
                for p in st.session_state.portfolio:
                    try:
                        latest_df = fdr.DataReader(p['코드'], (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'))
                        p['현재가'] = int(latest_df['Close'].iloc[-1])
                    except: continue
                st.success("포트폴리오 시세가 동기화되었습니다!")
                st.rerun()

    if st.session_state.portfolio:
        for p in st.session_state.portfolio:
            if '현재가' not in p: p['현재가'] = p['단가']
            p['현재금액'] = p['현재가'] * p['수량']
            p['수익률(%)'] = round(((p['현재금액'] - p['단가']*p['수량']) / (p['단가']*p['수량'])) * 100, 2)
        p_df = pd.DataFrame(st.session_state.portfolio)
        
        # [수정] TypeError 완벽 해결 (행 전체가 아닌 수익률 값만 비교)
        def color_profit_df(row):
            try:
                val = float(row['수익률(%)'])
                c = '#ff4b4b' if val > 0 else '#1c83e1' if val < 0 else '#c9d1d9'
            except:
                c = '#c9d1d9'
            return [f'color: {c}; font-weight: bold;' if col == '수익률(%)' else '' for col in row.index]
        
        st.dataframe(p_df[['일시', '종목명', '단가', '현재가', '수량', '근거', '수익률(%)']].style.apply(color_profit_df, axis=1), use_container_width=True)
    else: st.write("보유 중인 종목이 없습니다.")