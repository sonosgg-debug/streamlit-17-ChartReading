"""
app.py
기술적 분석(Technical Analysis) 및 각종 보조지표 기반 투자 의견 제시 대시보드
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime
import textwrap
import importlib

# 하위 모듈 변경 시 메모리 캐시 우회 및 실시간 핫 리로드 보장
import data_loader
import analyzer
import chart_plotter

importlib.reload(data_loader)
importlib.reload(analyzer)
importlib.reload(chart_plotter)

from data_loader import (
    load_krx_data,
    US_STOCKS_DISPLAY,
    get_stock_data,
    resolve_stock_info,
    resolve_stock_selection,
    resolve_ticker,
    POPULAR_KR_STOCKS,
    POPULAR_US_STOCKS,
    PERIOD_YEARS,
    MAJOR_INDICES,
    INDEX_DISPLAY_NAMES,
    get_index_data
)
from analyzer import (
    calculate_technical_indicators,
    evaluate_investment_opinion
)
from chart_plotter import create_financial_chart

# ---------------- 1. 페이지 환경 설정 ----------------
FAVICON_PATH = os.path.join(os.path.dirname(__file__), "favicon.png")

st.set_page_config(
    page_title="Technical Analysis Pro - 기술적 분석 대시보드",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- 2. 커스텀 CSS 스타일링 ----------------
# st.html을 사용하여 마크다운 파서의 간섭 없이 순수 CSS 주입
st.html("""
<style>
    /* 폰트 및 글로벌 레이아웃 (상단 헤더 가림 및 글자 잘림 방지) */
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 2.5rem;
    }

    /* Headers - 00 Bookmarks 폴더 앱과 동일한 #8AB4F8 색상 지정 */
    h1, .app-main-title {
        color: #8AB4F8 !important;
        font-weight: 800 !important;
    }
    
    h2, h3, [data-testid="stMarkdownContainer"] h3, .section-title {
        color: #8AB4F8 !important;
        font-weight: 800 !important;
    }

    .section-title {
        font-size: 1.35rem;
        margin: 16px 0 10px 0;
        letter-spacing: -0.3px;
    }

    /* 대시보드 메인 앱 타이틀 영역 */
    .app-main-header {
        margin-bottom: 20px;
        padding-bottom: 14px;
        border-bottom: 1px solid #2d3748;
    }
    .app-main-title {
        font-size: 1.9rem !important;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #8AB4F8 !important;
        line-height: 1.3;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .app-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-top: 6px;
        line-height: 1.5;
    }
    
    /* 카드 스타일 컴포넌트 */
    .custom-card {
        background-color: #1a1f2c;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }

    /* 5단계 스펙트럼 바 */
    .spectrum-container {
        display: flex;
        width: 100%;
        height: 12px;
        border-radius: 6px;
        overflow: hidden;
        margin: 12px 0 6px 0;
        background-color: #2d3748;
    }
    .spectrum-segment {
        flex: 1;
        transition: all 0.3s ease;
    }
    .spectrum-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: #9ca3af;
        margin-bottom: 14px;
    }

    /* 상세 지표 카드 */
    .metric-card {
        background-color: #1e2433;
        border: 1px solid #2f384f;
        border-radius: 10px;
        padding: 16px;
        height: 100%;
        box-sizing: border-box;
    }
    .metric-card h4 {
        margin: 0 0 10px 0;
        font-size: 0.95rem;
        color: #94a3b8;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-card .status-pill {
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
    }
    .metric-card ul {
        margin: 0;
        padding-left: 18px;
        font-size: 0.85rem;
        color: #e2e8f0;
    }
    .metric-card li {
        margin-bottom: 5px;
        line-height: 1.4;
    }

    /* 가격 전략 테이블 스타일 */
    .strategy-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.88rem;
    }
    .strategy-table th, .strategy-table td {
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid #2d3748;
    }
    .strategy-table th {
        background-color: #1e2433;
        color: #94a3b8;
    }

    /* 푸터 면책조항 */
    .disclaimer-box {
        background-color: #131722;
        border-left: 4px solid #4b5563;
        padding: 14px 18px;
        border-radius: 4px;
        margin-top: 30px;
        font-size: 0.8rem;
        color: #9ca3af;
        line-height: 1.6;
    }

    /* =========================================================
       사이드바 접기(<<) 및 펼치기(>>) 버튼 항상 표시 및 시인성/대비 강화
       ========================================================= */
    /* 1. 사이드바가 열려 있을 때 접기 버튼 (<<) 상시 표시 */
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        opacity: 1 !important;
        display: inline-flex !important;
    }
    
    [data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        opacity: 1 !important;
        background-color: #1e293b !important;       /* 진한 네이비 배경 */
        border: 1.5px solid #38bdf8 !important;     /* 선명한 스카이블루 테두리로 상자 명확화 */
        border-radius: 8px !important;
        width: 38px !important;
        height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    
    /* 상자 내부의 << 아이콘(Material Icon span/svg/문자)을 순백색으로 강제하여 상자와 극명한 대비 구현 */
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }
    
    /* 호버(PC) 및 터치 시 반전 효과 */
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover * {
        color: #0f172a !important;
        fill: #0f172a !important;
    }

    /* 2. 사이드바 헤더 영역 패딩 및 정렬 보정 */
    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* 3. 사이드바가 닫혔을 때 다시 여는 버튼 (>>) 시인성 강화 */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #1e293b !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button *,
    [data-testid="stSidebarCollapsedControl"] span,
    [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapsedControl"] svg {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
    }
</style>
""")


# ---------------- 3. 사이드바 컨트롤 ----------------
st.sidebar.markdown("## 📊 분석 설정")

# 1) 분석 모드 선택 (개별 종목 vs 시장 지수)
analysis_mode = st.sidebar.radio(
    "분석 모드",
    ["📈 개별 종목", "🌐 시장 지수"],
    index=0,
    horizontal=True
)

if analysis_mode == "📈 개별 종목":
    # KRX 종목 데이터 로드 (31 PerformanceChart 방식: 캐싱 및 전 종목 리스트)
    krx_df = load_krx_data()
    if not krx_df.empty:
        krx_display_names = (krx_df['Name'] + " (" + krx_df['Code'] + ")").tolist()
    else:
        krx_display_names = []

    us_display_names = US_STOCKS_DISPLAY

    # 증시 구분
    market_choice = st.sidebar.radio(
        "증시 구분",
        ["한국 (KRX)", "미국 (US)", "전체 (통합)"],
        index=2,
        horizontal=True
    )

    # 종목 선택 (31 PerformanceChart 방식)
    st.sidebar.markdown("### 종목 선택")

    if market_choice == "전체 (통합)":
        stock_options = krx_display_names + us_display_names + ["[직접 입력]"]
        default_target = "삼성전자 (005930)"
    elif market_choice == "한국 (KRX)":
        stock_options = krx_display_names + ["[직접 입력]"]
        default_target = "삼성전자 (005930)"
    else:
        stock_options = us_display_names + ["[직접 입력]"]
        default_target = "애플 (AAPL)"

    default_idx = 0
    for idx, opt in enumerate(stock_options):
        if default_target in opt:
            default_idx = idx
            break

    selected_stock = st.sidebar.selectbox(
        "종목 검색 및 선택",
        options=stock_options,
        index=default_idx,
        help="키보드로 종목명(예: 삼성전기, 삼성전자) 또는 종목코드(예: 009150, 005930)를 입력하여 빠르게 검색할 수 있습니다."
    )

    custom_input = ""
    if selected_stock == "[직접 입력]":
        custom_input = st.sidebar.text_input(
            "종목 직접 입력 (코드/티커/종목명)",
            value="",
            placeholder="예: 삼성전기, 009150, AAPL, TSLA",
            help="한글 종목명(삼성전기, 하이닉스 등), 6자리 종목코드(009150), 미국 티커(AAPL)를 자유롭게 입력하세요."
        ).strip()

    if selected_stock == "[직접 입력]":
        user_ticker = custom_input
    else:
        user_ticker = selected_stock

else:
    # 시장 지수 모드
    st.sidebar.markdown("### 시장 지수 선택")
    selected_index = st.sidebar.selectbox(
        "지수 선택",
        options=INDEX_DISPLAY_NAMES,
        index=0,
        help="분석할 주요 시장 지수(코스피, 코스닥, S&P 500, 나스닥 종합, 필라델피아 반도체)를 선택하세요."
    )
    user_ticker = selected_index
    market_choice = None
    selected_stock = None

# 2) 분석 대상 (봉 주기)
st.sidebar.markdown("### 분석 대상")
timeframe_choice = st.sidebar.radio(
    "봉 주기 선택",
    ["일봉", "주봉", "월봉"],
    index=0,
    horizontal=True
)

# 3) 조회 기간
st.sidebar.markdown("### 조회 기간")
period_choice = st.sidebar.select_slider(
    "기간 선택",
    options=["1Y", "3Y", "5Y", "10Y", "20Y"],
    value="1Y"
)

# 4) 보조 옵션
with st.sidebar.expander("🛠️ 차트 보조지표 설정", expanded=False):
    show_ma = st.checkbox("이동평균선 (5, 20, 60, 120, 200)", value=True)
    show_bb = st.checkbox("볼린저 밴드 (20, 2)", value=True)

# 5) 조회 실행 버튼
st.sidebar.markdown("---")
query_clicked = st.sidebar.button("🚀 분석 조회", type="primary", use_container_width=True)

# 세션 상태 초기화 및 관리
if "analyzed_data" not in st.session_state:
    st.session_state["analyzed_data"] = None

# 첫 진입이거나 조회 버튼 클릭 시 데이터 로딩
if query_clicked or st.session_state["analyzed_data"] is None:
    if analysis_mode == "📈 개별 종목" and selected_stock == "[직접 입력]" and not user_ticker:
        st.sidebar.warning("⚠️ 종목명 또는 종목코드를 입력해 주세요.")
    else:
        with st.spinner("최신 시장 데이터 및 기술적 지표를 계산하고 있습니다..."):
            if analysis_mode == "📈 개별 종목":
                df, metadata, err = get_stock_data(
                    ticker_input=user_ticker if user_ticker else "005930",
                    market=market_choice,
                    timeframe=timeframe_choice,
                    period_key=period_choice
                )
            else:
                df, metadata, err = get_index_data(
                    index_key=selected_index,
                    timeframe=timeframe_choice,
                    period_key=period_choice
                )

            if err:
                st.error(f"⚠️ {err}")
            else:
                df = calculate_technical_indicators(df)
                opinion_res = evaluate_investment_opinion(df)
                st.session_state["analyzed_data"] = {
                    "df": df,
                    "metadata": metadata,
                    "opinion_res": opinion_res,
                    "show_ma": show_ma,
                    "show_bb": show_bb
                }


# ---------------- 4. 메인 대시보드 렌더링 ----------------
# 4.0 최상단 대시보드 메인 타이틀 영역 (항상 최상단에 상시 표시)
st.html("""
<div class="app-main-header">
    <div style="display: flex; justify-content: center; align-items: center; position: relative;">
        <div style="text-align: center;">
            <h1 class="app-main-title" style="justify-content: center; text-align: center;">Technical Analysis Pro</h1>
            <div class="app-subtitle" style="text-align: center;">한국(KRX) 및 미국(US) 글로벌 주식 & 시장 지수 기술적 분석 & 전문가 5단계 투자 의견 대시보드</div>
        </div>
        <div style="position: absolute; right: 0; bottom: 0; font-size: 0.82rem; color: #64748b; padding-bottom: 4px;">
            AI & 퀀트 차트 리딩 시스템 | <span style="color: #10B981; font-weight: 600;">● 시스템 정상 가동</span>
        </div>
    </div>
</div>
""")

data = st.session_state.get("analyzed_data")

if data:
    df = data["df"]
    metadata = data["metadata"]
    opinion = data["opinion_res"]
    show_ma_opt = show_ma
    show_bb_opt = show_bb

    # 4.1 분석 종목 시세 헤더 & 요약 메트릭
    curr_price = metadata["current_price"]
    prev_price = metadata["prev_price"]
    change = metadata["change"]
    change_pct = metadata["change_pct"]
    is_index = metadata.get("is_index", False)

    change_color = "#ef4444" if change > 0 else ("#3b82f6" if change < 0 else "#9CA3AF")
    change_sign = "+" if change > 0 else ""

    if is_index or metadata["currency"] == "pt":
        curr_val_str = f"{curr_price:,.2f} pt"
        curr_delta_str = f"{change_sign}{change_pct:.2f}% ({change_sign}{change:,.2f} pt)"
    elif metadata["currency"] == "USD":
        curr_val_str = f"$ {curr_price:,.2f}"
        curr_delta_str = f"{change_sign}{change_pct:.2f}% ({change_sign}{change:,.2f})"
    else:
        curr_val_str = f"₩ {int(curr_price):,}"
        curr_delta_str = f"{change_sign}{change_pct:.2f}% ({change_sign}{int(change):,})"

    col_title, col_stat1, col_stat2, col_stat3, col_stat4 = st.columns([3.2, 2, 2, 2, 2])
    
    with col_title:
        title_html = f"""
        <div style="padding: 4px 0 8px 0; overflow: visible;">
            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap; line-height: 1.4;">
                <span style="font-size: 2.0rem; font-weight: 800; color: #f8fafc; line-height: 1.3; display: inline-block;">{metadata['name']}</span>
                <span style="font-size: 1.15rem; color: #94a3b8; font-weight: 600; line-height: 1.3;">{metadata['ticker']}</span>
                <span style="background-color: #334155; color: #e2e8f0; padding: 3px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 600;">{metadata['market']}</span>
            </div>
            <div style="font-size: 0.88rem; color: #64748b; margin-top: 6px; line-height: 1.4;">
                분석 대상: <b style="color: #cbd5e1;">{metadata['timeframe']}</b> | 조회 기간: <b style="color: #cbd5e1;">{metadata['period']}</b> | 기준일: {datetime.now().strftime('%Y-%m-%d')}
            </div>
        </div>
        """
        st.html(title_html)

    with col_stat1:
        st.metric(
            label="현재 지수 (종가)" if is_index else "현재가 (종가)",
            value=curr_val_str,
            delta=curr_delta_str
        )

    with col_stat2:
        high_52w = metadata["high_52w"]
        diff_from_high = ((curr_price - high_52w) / high_52w) * 100
        st.metric(
            label="52주 최고치 대비" if is_index else "52주 최고가 대비",
            value=f"{high_52w:,.1f}" if not is_index else f"{high_52w:,.2f} pt",
            delta=f"{diff_from_high:.1f}%",
            delta_color="normal"
        )

    with col_stat3:
        low_52w = metadata["low_52w"]
        diff_from_low = ((curr_price - low_52w) / low_52w) * 100
        st.metric(
            label="52주 최저치 대비" if is_index else "52주 최저가 대비",
            value=f"{low_52w:,.1f}" if not is_index else f"{low_52w:,.2f} pt",
            delta=f"+{diff_from_low:.1f}%",
            delta_color="normal"
        )

    with col_stat4:
        vol_ratio = opinion["indicators"]["vol_ratio"]
        if is_index and metadata["volume"] == 0:
            st.metric(
                label="20일 평균대비 거래량",
                value="미집계",
                delta="지수 특성",
                delta_color="off"
            )
        else:
            st.metric(
                label="20일 평균대비 거래량",
                value=f"{metadata['volume']:,}",
                delta=f"{vol_ratio:.0f}%",
                delta_color="normal" if vol_ratio >= 100 else "off"
            )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 4.2 투자 의견 및 스코어 카드 영역
    badge_bg = opinion["badge_color"]
    score = opinion["total_score"]
    
    # 5단계 스펙트럼 세그먼트 활성화 표시
    active_idx = 0
    if score >= 45:
        active_idx = 4
    elif score >= 15:
        active_idx = 3
    elif score >= -14:
        active_idx = 2
    elif score >= -44:
        active_idx = 1
    else:
        active_idx = 0

    c0 = "#EF4444" if active_idx == 0 else "#4b2121"
    c1 = "#F59E0B" if active_idx == 1 else "#4b381b"
    c2 = "#9CA3AF" if active_idx == 2 else "#374151"
    c3 = "#3B82F6" if active_idx == 3 else "#1e2e4b"
    c4 = "#10B981" if active_idx == 4 else "#164332"

    op0 = "1.0" if active_idx == 0 else "0.35"
    op1 = "1.0" if active_idx == 1 else "0.35"
    op2 = "1.0" if active_idx == 2 else "0.35"
    op3 = "1.0" if active_idx == 3 else "0.35"
    op4 = "1.0" if active_idx == 4 else "0.35"

    l0_color = "#EF4444" if active_idx == 0 else "#64748b"
    l1_color = "#F59E0B" if active_idx == 1 else "#64748b"
    l2_color = "#E2E8F0" if active_idx == 2 else "#64748b"
    l3_color = "#3B82F6" if active_idx == 3 else "#64748b"
    l4_color = "#10B981" if active_idx == 4 else "#64748b"

    l0_w = "700" if active_idx == 0 else "400"
    l1_w = "700" if active_idx == 1 else "400"
    l2_w = "700" if active_idx == 2 else "400"
    l3_w = "700" if active_idx == 3 else "400"
    l4_w = "700" if active_idx == 4 else "400"

    opinion_card_html = f"""
    <div class="custom-card" style="border-left: 6px solid {badge_bg};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="background-color: {badge_bg}; color: #ffffff; padding: 6px 20px; border-radius: 8px; font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px;">
                    {opinion['opinion']}
                </span>
                <span style="color: #94a3b8; font-size: 1.05rem;">
                    기술적 종합 점수: <b style="color: #ffffff; font-size: 1.3rem;">{score:+d}점</b> <span style="font-size: 0.85rem; color: #64748b;">(-100 ~ +100)</span>
                </span>
            </div>
            <div style="font-size: 0.85rem; color: #94a3b8;">
                신호 강도: <b style="color: {badge_bg}; font-size: 1.05rem;">{opinion['opinion_en']}</b>
            </div>
        </div>
        <div class="spectrum-container">
            <div class="spectrum-segment" style="background-color: {c0}; opacity: {op0};"></div>
            <div class="spectrum-segment" style="background-color: {c1}; opacity: {op1};"></div>
            <div class="spectrum-segment" style="background-color: {c2}; opacity: {op2};"></div>
            <div class="spectrum-segment" style="background-color: {c3}; opacity: {op3};"></div>
            <div class="spectrum-segment" style="background-color: {c4}; opacity: {op4};"></div>
        </div>
        <div class="spectrum-labels">
            <span style="color: {l0_color}; font-weight: {l0_w};">매도 (Sell)</span>
            <span style="color: {l1_color}; font-weight: {l1_w};">비중축소 (Underweight)</span>
            <span style="color: {l2_color}; font-weight: {l2_w};">중립 (Neutral)</span>
            <span style="color: {l3_color}; font-weight: {l3_w};">비중확대 (Overweight)</span>
            <span style="color: {l4_color}; font-weight: {l4_w};">매수 (Buy)</span>
        </div>
        <div style="font-size: 0.98rem; line-height: 1.6; color: #cbd5e1; margin-top: 10px;">
            💡 <b>전문가 종합 총평:</b> {opinion['summary']}
        </div>
        <div style="font-size: 0.84rem; color: #94a3b8; background-color: #141824; border: 1px solid #283347; border-radius: 8px; padding: 10px 14px; margin-top: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; line-height: 1.5;">
            <span style="color: #8AB4F8; font-weight: 700; white-space: nowrap;">📊 기술적 종합 점수 산출 기준:</span>
            <span>이동평균선 배열(25%), MACD(20%), RSI(20%), 볼린저 밴드(15%), 스토캐스틱(10%), 거래량(10%)을 종합 가중치로 평가해 -100 ~ +100점으로 산출합니다.</span>
        </div>
    </div>
    """
    st.html(opinion_card_html)

    # 4.3 메인 인터랙티브 차트 영역
    st.html('<div class="section-title">📈 주가 및 보조지표 종합 차트</div>')
    chart_fig = create_financial_chart(
        df=df,
        metadata=metadata,
        sr_levels=opinion["support_resistance"],
        show_bollinger=show_bb_opt,
        show_ma=show_ma_opt,
        target_start_date=metadata["target_start_date"]
    )
    st.plotly_chart(chart_fig, use_container_width=True)

    # 4.4 기술적 분석 세부 진단 (4대 핵심 영역 카드)
    st.html('<div class="section-title">🔬 기술적 지표 세부 진단 및 근거</div>')
    sd = opinion["score_details"]

    col_trend, col_mom, col_macd, col_vol = st.columns(4)

    with col_trend:
        t_status = sd["trend"]["status"]
        t_color = "#10B981" if "상승" in t_status else ("#EF4444" if "하락" in t_status else "#94a3b8")
        notes_li = "".join([f"<li>{note}</li>" for note in sd["trend"]["notes"]])
        st.html(f"""
        <div class="metric-card">
            <h4>
                <span>이동평균 & 추세</span>
                <span class="status-pill" style="background-color: {t_color}22; color: {t_color}; border: 1px solid {t_color};">{t_status}</span>
            </h4>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px;">점수 기여: <b style="color: #ffffff;">{sd['trend']['score']:+d} / {sd['trend']['max']}</b></div>
            <ul>{notes_li}</ul>
        </div>
        """)

    with col_mom:
        m_status = sd["momentum"]["status"]
        m_color = "#10B981" if "강세" in m_status else ("#EF4444" if "약세" in m_status else "#94a3b8")
        notes_li = "".join([f"<li>{note}</li>" for note in sd["momentum"]["notes"]])
        st.html(f"""
        <div class="metric-card">
            <h4>
                <span>모멘텀 (RSI/스토캐스틱)</span>
                <span class="status-pill" style="background-color: {m_color}22; color: {m_color}; border: 1px solid {m_color};">{m_status}</span>
            </h4>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px;">점수 기여: <b style="color: #ffffff;">{sd['momentum']['score']:+d} / {sd['momentum']['max']}</b></div>
            <ul>{notes_li}</ul>
        </div>
        """)

    with col_macd:
        c_status = sd["macd"]["status"]
        c_color = "#10B981" if "매수" in c_status else ("#EF4444" if "매도" in c_status else "#94a3b8")
        notes_li = "".join([f"<li>{note}</li>" for note in sd["macd"]["notes"]])
        st.html(f"""
        <div class="metric-card">
            <h4>
                <span>MACD 추세 강도</span>
                <span class="status-pill" style="background-color: {c_color}22; color: {c_color}; border: 1px solid {c_color};">{c_status}</span>
            </h4>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px;">점수 기여: <b style="color: #ffffff;">{sd['macd']['score']:+d} / {sd['macd']['max']}</b></div>
            <ul>{notes_li}</ul>
        </div>
        """)

    with col_vol:
        v_status = sd["volatility"]["status"]
        v_color = "#10B981" if "양호" in v_status else ("#EF4444" if "부담" in v_status else "#94a3b8")
        notes_li = "".join([f"<li>{note}</li>" for note in sd["volatility"]["notes"]])
        st.html(f"""
        <div class="metric-card">
            <h4>
                <span>볼린저 & 거래량</span>
                <span class="status-pill" style="background-color: {v_color}22; color: {v_color}; border: 1px solid {v_color};">{v_status}</span>
            </h4>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px;">점수 기여: <b style="color: #ffffff;">{sd['volatility']['score']:+d} / {sd['volatility']['max']}</b></div>
            <ul>{notes_li}</ul>
        </div>
        """)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # 4.5 지지/저항선 가격대 및 실전 매매 전략 가이드
    col_sr, col_strat = st.columns([1, 1])
    sr = opinion["support_resistance"]
    strat = opinion["strategy"]

    with col_sr:
        st.html('<div class="section-title">🎯 핵심 지지 및 저항 가격대</div>')
        sr_table_html = f"""
        <div class="custom-card" style="padding: 16px;">
            <table class="strategy-table">
                <thead>
                    <tr>
                        <th>구분</th>
                        <th>가격 ({metadata['currency']})</th>
                        <th>현재가 대비 격차</th>
                        <th>기술적 의미</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="color: #EF4444; font-weight: 700;">2차 저항선</td>
                        <td><b>{sr['resistance_2']:,.1f}</b></td>
                        <td style="color: #EF4444;">{((sr['resistance_2'] - curr_price) / curr_price * 100):+.1f}%</td>
                        <td>중장기 스윙 고점 / 오버슈팅 저항</td>
                    </tr>
                    <tr>
                        <td style="color: #F87171; font-weight: 700;">{"1차 저항선 (상방 목표 레벨)" if is_index else "1차 저항선 (목표가)"}</td>
                        <td><b>{sr['resistance_1']:,.1f}</b></td>
                        <td style="color: #F87171;">{((sr['resistance_1'] - curr_price) / curr_price * 100):+.1f}%</td>
                        <td>단기 볼린저 상단 / 직전 매물대</td>
                    </tr>
                    <tr style="background-color: #1e293b;">
                        <td><b>{"현재 지수" if is_index else "현재 주가"}</b></td>
                        <td><b style="color: #38BDF8;">{curr_price:,.1f}</b></td>
                        <td>기준점</td>
                        <td>최근 종가 기준</td>
                    </tr>
                    <tr>
                        <td style="color: #34D399; font-weight: 700;">1차 지지선</td>
                        <td><b>{sr['support_1']:,.1f}</b></td>
                        <td style="color: #34D399;">{((sr['support_1'] - curr_price) / curr_price * 100):+.1f}%</td>
                        <td>20일 이평선 또는 볼린저 하단 지지</td>
                    </tr>
                    <tr>
                        <td style="color: #10B981; font-weight: 700;">2차 지지선 (바닥선)</td>
                        <td><b>{sr['support_2']:,.1f}</b></td>
                        <td style="color: #10B981;">{((sr['support_2'] - curr_price) / curr_price * 100):+.1f}%</td>
                        <td>최근 스윙 최저점 / 마지노선</td>
                    </tr>
                    <tr style="border-top: 2px solid #374151;">
                        <td style="color: #F43F5E; font-weight: 800;">{"지지 이탈 경계 레벨" if is_index else "권장 손절 기준가"}</td>
                        <td><b style="color: #F43F5E;">{sr['stop_loss']:,.1f}</b></td>
                        <td style="color: #F43F5E;">{((sr['stop_loss'] - curr_price) / curr_price * 100):+.1f}%</td>
                        <td>ATR 2배수 및 1차 지지선 하향 이탈 기준</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        st.html(sr_table_html)

    with col_strat:
        st.html('<div class="section-title">📋 실전 매매 대응 전략</div>')
        strat_html = f"""
        <div class="custom-card">
            <div style="margin-bottom: 16px;">
                <div style="color: #38BDF8; font-weight: 700; font-size: 0.95rem; margin-bottom: 5px;">
                    🟢 신규 매수자 접근 전략 (Entry Strategy)
                </div>
                <div style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5;">
                    {strat['entry_strategy']}
                </div>
            </div>
            <div style="margin-bottom: 16px;">
                <div style="color: #A78BFA; font-weight: 700; font-size: 0.95rem; margin-bottom: 5px;">
                    💼 기존 보유자 대응 전략 (Holding Strategy)
                </div>
                <div style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5;">
                    {strat['holding_strategy']}
                </div>
            </div>
            <div>
                <div style="color: #F87171; font-weight: 700; font-size: 0.95rem; margin-bottom: 5px;">
                    🛡️ 리스크 관리 및 손절 수칙 (Risk Management)
                </div>
                <div style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5;">
                    {strat['risk_management']}
                </div>
            </div>
        </div>
        """
        st.html(strat_html)

    # 4.6 법적 면책 고지
    st.html("""
    <div class="disclaimer-box">
        <b>⚠️ 법적 투자 유의사항 및 면책 고지 (Disclaimer)</b><br>
        본 서비스에서 제공하는 기술적 분석 결과와 투자 의견(매수/비중확대/중립/비중축소/매도)은 과거의 주가 및 거래량 데이터를 기반으로 수학적·통계적 보조지표를 정량화하여 산출한 참고 정보입니다.
        주식 시장은 예측 불가능한 거시 경제 변수, 기업 펀더멘털, 시장 수급 등에 의해 급변할 수 있으며, 과거의 패턴이 미래의 수익을 보장하지 않습니다.
        모든 투자 판단과 그에 따른 최종 손익의 책임은 전적으로 투자자 본인에게 있으므로, 반드시 본인의 투자 목적과 리스크 감내 수준을 고려하여 신중하게 결정하시기 바랍니다.
    </div>
    """)

else:
    st.info("👈 왼쪽 사이드바에서 분석할 종목과 조건을 설정한 후 **'분석 조회'** 버튼을 클릭해 주세요.")
