import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures
import numpy as np
import json
import os

# ==========================================
# 🚨 보안 시스템 (6006)
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "6006": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h4 style='text-align: center; color: #d4af37;'> 🍀오늘도쨔잔!!🍀</h4>", unsafe_allow_html=True)
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
    .analysis-box { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 10px; margin-top: 5px; }
    .price-container { display: flex; justify-content: space-between; gap: 5px; margin-bottom: 5px; }
    .price-card { background: #1c2128; padding: 10px 5px; border-radius: 10px; text-align: center; border: 1px solid #30363d; flex: 1; }
    .indicator-grid { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
    .ind-item { padding: 2px 8px; border-radius: 15px; font-size: 10px; font-weight: bold; border: 1px solid #444; }
    .ss-badge { color: #ff4b4b; border: 1.5px solid #ff4b4b; padding: 1px 6px; border-radius: 5px; font-weight: 900; font-size: 14px; }
    .curr-price { color: #ffffff; font-size: 18px; font-weight: bold; margin-left: 10px; }
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

@st.cache_data(ttl=3600)
def load_active_stocks():
    try:
        df = fdr.StockListing('KRX')
        df['Name'] = df['Name'].str.strip()
        active_df = df.sort_values(by='Marcap', ascending=False).head(1200)
        return active_df
    except:
        return pd.DataFrame({'Code': ['005930'], 'Name': ['삼성전자']})

all_stocks_df = load_active_stocks()

# --- 정밀 분석 엔진 (120일 기점) ---
def analyze_logic(item):
    try:
        # 타임아웃을 짧게 걸어 무한 로딩 방지
        df = fdr.DataReader(item['코드'], (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'))
        if df is None or len(df) < 60: return None
        
        close = df['Close']
        ma5 = close.rolling(5).mean(); ma20 = close.rolling(20).mean(); ma60 = close.rolling(60).mean()
        delta = close.diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/(loss+1e-9))))
        obv = (np.sign(close.diff()) * df['Volume']).fillna(0).cumsum()
        
        curr, high_60, low_20 = close.iloc[-1], df['High'].iloc[-60:].max(), df['Low'].iloc[-20:].min()
        support = round(ma20.iloc[-1] if curr > ma20.iloc[-1] else ma60.iloc[-1], 0)
        buy_min, buy_max = round(support * 0.99, 0), round(support * 1.02, 0)
        target_exit, stop_loss = round(high_60, 0), round(support * 0.96, 0)
        
        scores = [
            df['Volume'].iloc[-1] > df['Volume'].iloc[-5:-1].mean()*1.3,
            ma5.iloc[-1] > ma20.iloc[-1],
            curr > df['Open'].iloc[-1],
            curr > df['High'].iloc[-10:-1].max(),
            30 < rsi.iloc[-1] < 70,
            curr <= low_20 * 1.15,
            (df['High'].iloc[-20:].max() - df['Low'].iloc[-20:].min())/curr < 0.1,
            obv.iloc[-1] > obv.iloc[-5],
            (rsi.iloc[-1] > rsi.iloc[-5]) and (curr < close.iloc[-5]),
            curr > ma20.iloc[-1],
            ((high_60 - curr)/curr*100) >= 15,
            ma20.iloc[-1] > ma20.iloc[-10]
        ]
        total_score = sum(scores)
        is_buy_zone = buy_min <= curr <= buy_max
        tier = "👑 SS" if total_score >= 10 and is_buy_zone else ("💎 S" if total_score >= 8 else "✅ A")

        return {
            "등급": tier, "종목": item['종목명'], "코드": item['코드'], "가격": int(curr),
            "수익%": round(((high_60 - curr) / curr) * 100, 1),
            "진입가": f"{int(buy_min):,}", "목표가": f"{int(target_exit):,}", "손절가": f"{int(stop_loss):,}",
            "점수": total_score, "지표": scores, "상태": "🎯진입가능" if is_buy_zone else "⏳대기"
        }
    except: return None

# --- 한 화면에 쏙 들어오는 콤팩트 렌더링 ---
def render_compact(res, key):
    # 타이틀: 등급 + 종목명 + 현재 시세
    st.markdown(f"""
        <div style='display: flex; align-items: center; margin-bottom: 5px;'>
            <span class='ss-badge'>{res['등급']}</span>
            <span style='font-size: 18px; font-weight: bold; margin-left: 8px;'>{res['종목']}</span>
            <span class='curr-price'>{res['가격']:,}원</span>
            <span style='font-size: 12px; color: #777; margin-left: auto;'>{res['상태']}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # 가로 3단 가격 배치
    st.markdown(f"""
        <div class='price-container'>
            <div class='price-card'><small style='color:#777'>진입가</small><br><b style='color:#ff4b4b'>{res['진입가']}</b></div>
            <div class='price-card'><small style='color:#777'>목표가</small><br><b style='color:#4CAF50'>{res['목표가']}</b></div>
            <div class='price-card'><small style='color:#777'>손절가</small><br><b style='color:#4b8bff'>{res['손절가']}</b></div>
        </div>
    """, unsafe_allow_html=True)

    # 12대 지표 그리드
    names = ["거래량", "골든C", "양봉", "전고돌파", "RSI안전", "바닥지지", "응축", "수급우향", "매집신호", "중심선위", "탄력성", "추세안정"]
    indicators_html = "".join([f"<span class='ind-item' style='background:{'rgba(255,75,75,0.15)' if val else 'transparent'}; border-color:{'#ff4b4b' if val else '#444'}; color:{'#ff4b4b' if val else '#777'}'>{name}</span>" for name, val in zip(names, res['지표'])])
    st.markdown(f"<div class='analysis-box'><div class='indicator-grid'>{indicators_html}</div></div>", unsafe_allow_html=True)
    
    if st.button(f"{'❌ 보물함 삭제' if res['종목'] in st.session_state.favorites else '⭐ 보물함 추가'}", key=f"btn_{res['종목']}_{key}", use_container_width=True):
        if res['종목'] in st.session_state.favorites: st.session_state.favorites.remove(res['종목'])
        else: st.session_state.favorites.append(res['종목'])
        save_data(); st.rerun()
    st.divider()

# --- 앱 메인 레이아웃 ---
st.markdown("<h4 style='text-align: center; color: #d4af37;'>🌷무조건잘된다니까🌷</h4>", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(["🔍검색", "📡SS레이더", "⭐보물함"])

with t1:
    s_in = st.text_input("종목명 입력", "")
    if st.button("즉시 분석", use_container_width=True):
        st.session_state.searched_stock = s_in.strip()

    if st.session_state.searched_stock:
        m = all_stocks_df[all_stocks_df['Name'] == st.session_state.searched_stock]
        if not m.empty:
            with st.spinner(f"'{st.session_state.searched_stock}' 분석 중..."):
                res = analyze_logic({'코드': m.iloc[0]['Code'], '종목명': m.iloc[0]['Name']})
                if res: render_compact(res, "search")
                else: st.error("❌ 현재 거래소 서버 점검 시간인 것 같아. (밤/주말)")
        else:
            st.warning("정확한 종목 이름을 입력해줘!")

with t2:
    if st.button("📡 [터보 스캔] SS등급 추출", use_container_width=True):
        try:
            p_bar = st.progress(0, text="📡 우량 종목 스캔 중...")
            final = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
                futures = [ex.submit(analyze_logic, {'코드': r.Code, '종목명': r.Name}) for r in all_stocks_df.itertuples()]
                for i, f in enumerate(concurrent.futures.as_completed(futures)):
                    res = f.result()
                    if res: final.append(res)
                    if i % 50 == 0: p_bar.progress((i+1)/len(all_stocks_df), text=f"💎 {i+1}개 종목 검사 완료...")
            st.session_state.rt_results = sorted(final, key=lambda x: (x['등급'], x['점수'], x['수익%']), reverse=True)[:30]
            p_bar.empty()
            if not final: st.error("❌ 데이터 응답이 없어. 거래소 점검 시간인지 확인해줘!")
        except: st.error("❌ 거래소 서버 연결 실패!")
    
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
        if not fav_l: st.error("❌ 지금은 데이터를 불러올 수 없어. (점검 시간)")
        for i, r in enumerate(fav_l): render_compact(r, f"fav_{i}")
    else: st.info("보물함이 비어 있어!")
