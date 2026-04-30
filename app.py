import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import numpy as np
import json
import os

# ==========================================
# 🚨 비밀번호 시스템 (6006)
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "6006": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h4 style='text-align: center; color: #d4af37;'> 🍀오늘도쨔잔!!☘</h4>", unsafe_allow_html=True)
        st.text_input("헤헿💛", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

# --- 앱 설정 ---
st.set_page_config(page_title="💰 데이터 스튜디오 💰", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"]  { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .analysis-box { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 12px; margin-top: 5px; }
    .price-card { background: #1c2128; padding: 15px; border-radius: 15px; text-align: center; border: 1px solid #30363d; }
    .indicator-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .ind-item { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; border: 1px solid #444; }
    .ss-badge { color: #ff4b4b; border: 2px solid #ff4b4b; padding: 2px 8px; border-radius: 5px; font-weight: 900; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 ---
DATA_FILE = "jj_user_data.json"
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"favorites": []}
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"favorites": st.session_state.favorites}, f, ensure_ascii=False)

if 'data_loaded' not in st.session_state:
    loaded = load_data(); st.session_state.favorites = loaded.get("favorites", []); st.session_state.data_loaded = True
if 'rt_results' not in st.session_state: st.session_state.rt_results = []
if 'searched_stock' not in st.session_state: st.session_state.searched_stock = "" 

# [초고속 필터] 시가총액 상위 종목만 가져오기
@st.cache_data(ttl=3600)
def load_active_stocks():
    try:
        df = fdr.StockListing('KRX')
        # 시가총액(Marcap) 기준으로 내림차순 정렬 후 상위 1,200개만 남김 (잡주 제거)
        active_df = df.sort_values(by='Marcap', ascending=False).head(1200)
        return active_df
    except:
        return pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']})

all_stocks_df = load_active_stocks()

# --- 정밀 분석 엔진 (120일 기점) ---
def analyze_logic(item):
    try:
        # 분석 기간을 120일로 최적화
        df = fdr.DataReader(item['코드'], (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'))
        if len(df) < 60: return None # 최소 60일 데이터 필요
        
        close = df['Close']
        ma5 = close.rolling(5).mean(); ma20 = close.rolling(20).mean(); ma60 = close.rolling(60).mean()
        
        # RSI 
        delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/(loss+1e-9))))
        
        # OBV
        obv = (np.sign(close.diff()) * df['Volume']).fillna(0).cumsum()
        
        curr, high_60, low_20 = close.iloc[-1], df['High'].iloc[-60:].max(), df['Low'].iloc[-20:].min()
        support = round(ma20.iloc[-1] if curr > ma20.iloc[-1] else ma60.iloc[-1], 0)
        buy_min, buy_max = round(support * 0.99, 0), round(support * 1.02, 0)
        target_exit = round(high_60, 0)
        stop_loss = round(support * 0.96, 0)
        
        # 12대 블랙박스 지표
        scores = [
            df['Volume'].iloc[-1] > df['Volume'].iloc[-5:-1].mean()*1.3, # 1.거래량폭발
            ma5.iloc[-1] > ma20.iloc[-1], # 2.골든크로스
            curr > df['Open'].iloc[-1], # 3.단기양봉
            curr > df['High'].iloc[-10:-1].max(), # 4.전고돌파
            30 < rsi.iloc[-1] < 70, # 5.RSI안전권
            curr <= low_20 * 1.15, # 6.바닥지지
            (df['High'].iloc[-20:].max() - df['Low'].iloc[-20:].min())/curr < 0.1, # 7.에너지응축
            obv.iloc[-1] > obv.iloc[-5], # 8.수급우향
            (rsi.iloc[-1] > rsi.iloc[-5]) and (curr < close.iloc[-5]), # 9.매집신호(다이버전스)
            curr > ma20.iloc[-1], # 10.중심선위
            ((high_60 - curr)/curr*100) >= 15, # 11.탄력성
            ma20.iloc[-1] > ma20.iloc[-10] # 12.추세안정
        ]
        total_score = sum(scores)
        is_buy_zone = buy_min <= curr <= buy_max
        
        if total_score >= 10 and is_buy_zone: tier = "👑 SS"
        elif total_score >= 8: tier = "💎 S"
        else: tier = "✅ A"

        return {
            "등급": tier, "종목": item['종목명'], "코드": item['코드'], "가격": int(curr),
            "수익%": round(((high_60 - curr) / curr) * 100, 1),
            "진입가": f"{int(buy_min):,} ~ {int(buy_max):,}", "목표가": f"{int(target_exit):,}", "손절가": f"{int(stop_loss):,}",
            "점수": total_score, "지표": scores, "상태": "🎯진입가능" if is_buy_zone else "⏳대기"
        }
    except: return None

# --- 화면 렌더링 ---
def render_compact(res, key):
    st.markdown(f"#### <span class='ss-badge'>{res['등급']}</span> {res['종목']} ({res['상태']})", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f"<div class='price-card'><small>진입 권장</small><br><b style='color:#ff4b4b; font-size:16px;'>{res['진입가']}</b></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='price-card'><small>목표(익절)</small><br><b style='color:#4CAF50; font-size:16px;'>{res['목표가']}</b></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='price-card'><small>철저 손절</small><br><b style='color:#4b8bff; font-size:16px;'>{res['손절가']}</b></div>", unsafe_allow_html=True)

    names = ["거래량", "골든C", "양봉", "전고돌파", "RSI안전", "바닥지지", "응축", "수급우향", "매집신호", "중심선위", "탄력성", "추세안정"]
    indicators_html = "".join([f"<span class='ind-item' style='background:{'rgba(255,75,75,0.15)' if val else 'transparent'}; border-color:{'#ff4b4b' if val else '#444'}; color:{'#ff4b4b' if val else '#777'}'>{name}</span>" for name, val in zip(names, res['지표'])])
    st.markdown(f"<div class='analysis-box'><b>🔍 분석 (통과: {res['점수']}/12)</b><div class='indicator-grid'>{indicators_html}</div></div>", unsafe_allow_html=True)
    
    if st.button(f"{'❌ 삭제' if res['종목'] in st.session_state.favorites else '⭐ 보물함 추가'}", key=f"btn_{res['종목']}_{key}", use_container_width=True):
        if res['종목'] in st.session_state.favorites: st.session_state.favorites.remove(res['종목'])
        else: st.session_state.favorites.append(res['종목'])
        save_data(); st.rerun()
    st.divider()

# --- 앱 본체 ---
st.markdown("<h4 style='text-align: center; color: #d4af37;'>🌷무조건잘된다니까🌷</h4>", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(["🔍검색", "📡SS레이더", "⭐보물함"])

with t1:
    s_in = st.text_input("종목명", "")
    if st.button("즉시 분석", use_container_width=True): st.session_state.searched_stock = s_in
    if st.session_state.searched_stock:
        m = all_stocks_df[all_stocks_df['Name'] == st.session_state.searched_stock]
        if not m.empty:
            with st.spinner("정밀 분석 중..."):
                res = analyze_logic({'코드': m.iloc[0]['Code'], '종목명': m.iloc[0]['Name']})
                if res: render_compact(res, "search")
        else: st.warning("정확한 이름을 입력해줘!")

with t2:
    if st.button("📡 [터보 스캔] SS등급 추출", use_container_width=True):
        try:
            # 1,200개 상위 종목만 타겟으로 삼아 속도 2배 이상 향상
            p_bar = st.progress(0, text="📡 우량 종목 스캔 중...")
            final = []
            # 병렬 일꾼 수를 20개로 최적화 (서버 차단 방지)
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
                futures = [ex.submit(analyze_logic, {'코드': r.Code, '종목명': r.Name}) for r in all_stocks_df.itertuples()]
                for i, f in enumerate(concurrent.futures.as_completed(futures)):
                    res = f.result()
                    if res: final.append(res)
                    if i % 20 == 0:
                        p_bar.progress((i+1)/len(all_stocks_df), text=f"💎 {i+1}/{len(all_stocks_df)} 종목 분석 완료...")
            
            # 등급 -> 점수 -> 수익률 순으로 정렬하여 상위 30개만 표시
            st.session_state.rt_results = sorted(final, key=lambda x: (x['등급'], x['점수'], x['수익%']), reverse=True)[:30]
            p_bar.empty()
        except: st.error("거래소 서버 지연! 잠시 후 다시 해봐.")
    
    if st.session_state.rt_results:
        for i, r in enumerate(st.session_state.rt_results): render_compact(r, f"radar_{i}")

with t3:
    if st.session_state.favorites:
        if st.button("🔄 보물함 새로고침", use_container_width=True): st.rerun()
        fav_l = []
        with st.spinner("보물함 정밀 분석 중..."):
            for fn in st.session_state.favorites:
                m = all_stocks_df[all_stocks_df['Name'] == fn]
                if not m.empty:
                    res = analyze_logic({'코드': m.iloc[0]['Code'], '종목명': fn})
                    if res: fav_l.append(res)
        for i, r in enumerate(fav_l): render_compact(r, f"fav_{i}")
    else: st.info("보물함이 비어 있어!")
