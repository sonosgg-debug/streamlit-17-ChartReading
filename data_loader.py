"""
data_loader.py
한국(KRX) 및 미국(US) 주식 시장의 데이터를 불러오고 리샘플링 및 정제하는 모듈
31 PerformanceChart 방식을 적용하여 KRX 전체 상장 종목 캐싱 및 고도화된 종목 검색/해석 기능 지원
"""

import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import FinanceDataReader as fdr
import streamlit as st

# KRX 전 종목 데이터 로드 및 24시간 캐싱 (31 PerformanceChart 방식)
@st.cache_data(ttl=86400)
def load_krx_data() -> pd.DataFrame:
    """
    KRX 종목 목록을 가져와서 코드가 포함된 데이터프레임을 반환합니다.
    로컬 krx_cache.csv가 있으면 우선 참조/백업하여 안정적인 오프라인/지연 방지 구동을 보장합니다.
    """
    cache_file = os.path.join(os.path.dirname(__file__), "krx_cache.csv")
    try:
        # 실시간 데이터 로드 시도
        df = fdr.StockListing('KRX')
        df_cleaned = df[['Code', 'Name', 'Market']].copy()
        # 로컬 백업 파일 저장
        df_cleaned.to_csv(cache_file, index=False, encoding='utf-8-sig')
        return df_cleaned
    except Exception:
        # 실시간 로드 실패 시 로컬 캐시 시도
        if os.path.exists(cache_file):
            try:
                return pd.read_csv(cache_file, dtype={'Code': str}, encoding='utf-8-sig')
            except Exception:
                try:
                    return pd.read_csv(cache_file, dtype={'Code': str})
                except Exception:
                    pass

        # 캐시 파일도 없는 경우, 주요 대형주 폴백 데이터 반환
        fallback_data = [
            {"Code": "005930", "Name": "삼성전자", "Market": "KOSPI"},
            {"Code": "000660", "Name": "SK하이닉스", "Market": "KOSPI"},
            {"Code": "005935", "Name": "삼성전자우", "Market": "KOSPI"},
            {"Code": "009150", "Name": "삼성전기", "Market": "KOSPI"},
            {"Code": "035720", "Name": "카카오", "Market": "KOSPI"},
            {"Code": "035420", "Name": "NAVER", "Market": "KOSPI"},
            {"Code": "005380", "Name": "현대차", "Market": "KOSPI"},
            {"Code": "000270", "Name": "기아", "Market": "KOSPI"},
            {"Code": "207940", "Name": "삼성바이오로직스", "Market": "KOSPI"},
            {"Code": "068270", "Name": "셀트리온", "Market": "KOSPI"},
            {"Code": "051910", "Name": "LG화학", "Market": "KOSPI"},
            {"Code": "373220", "Name": "LG에너지솔루션", "Market": "KOSPI"},
            {"Code": "006400", "Name": "삼성SDI", "Market": "KOSPI"},
            {"Code": "247540", "Name": "에코프로비엠", "Market": "KOSDAQ"},
            {"Code": "086520", "Name": "에코프로", "Market": "KOSDAQ"},
        ]
        return pd.DataFrame(fallback_data)


# 주요 미국 주식 목록 (한국어 종목명 + 티커, 31 PerformanceChart 및 주요 ETF)
US_STOCKS_DISPLAY = [
    "애플 (AAPL)",
    "마이크로소프트 (MSFT)",
    "엔비디아 (NVDA)",
    "테슬라 (TSLA)",
    "아마존 (AMZN)",
    "알파벳A (GOOGL)",
    "메타 (META)",
    "버크셔해서웨이 (BRK-B)",
    "브로드컴 (AVGO)",
    "TSMC (TSM)",
    "일라이릴리 (LLY)",
    "JP모건 (JPM)",
    "월마트 (WMT)",
    "비자 (V)",
    "엑슨모빌 (XOM)",
    "넷플릭스 (NFLX)",
    "코스트코 (COST)",
    "ASML (ASML)",
    "AMD (AMD)",
    "퀄컴 (QCOM)",
    "팔란티어 (PLTR)",
    "아이온큐 (IONQ)",
    "인텔 (INTC)",
    "S&P 500 ETF (SPY)",
    "나스닥 100 ETF (QQQ)",
    "반도체 ETF (SOXX)"
]

# 미국 대표 종목 프리셋 (하위 호환)
POPULAR_US_STOCKS = {
    "AAPL": "Apple (애플)",
    "MSFT": "Microsoft (마이크로소프트)",
    "NVDA": "NVIDIA (엔비디아)",
    "TSLA": "Tesla (테슬라)",
    "GOOGL": "Alphabet (구글)",
    "AMZN": "Amazon (아마존)",
    "META": "Meta (메타)",
    "AMD": "AMD (어드밴스드 마이크로 디바이스)",
    "NFLX": "Netflix (넷플릭스)",
    "AVGO": "Broadcom (브로드컴)",
    "PLTR": "Palantir (팔란티어)",
    "SPY": "S&P 500 ETF (SPY)",
    "QQQ": "Invesco QQQ (나스닥 100 ETF)",
    "SOXX": "iShares Semiconductor ETF (반도체 ETF)"
}

# 한국 대표 종목 프리셋 (하위 호환)
POPULAR_KR_STOCKS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스",
    "005380": "현대차",
    "000270": "기아",
    "068270": "셀트리온",
    "035420": "NAVER",
    "035720": "카카오",
    "005490": "POSCO홀딩스",
    "247540": "에코프로비엠",
    "086520": "에코프로",
    "105560": "KB금융",
    "055550": "신한지주",
    "012330": "현대모비스"
}

# 기간별 연도 매핑
PERIOD_YEARS = {
    "1Y": 1,
    "3Y": 3,
    "5Y": 5,
    "10Y": 10,
    "20Y": 20
}

# 별칭 사전 (32 FinancialChart / 31 PerformanceChart 공통)
COMMON_ALIASES = {
    "삼전": "005930",
    "하닉": "000660",
    "하이닉스": "000660",
    "현대자동차": "005380",
    "LG엔솔": "373220",
    "엘지에너지솔루션": "373220",
    "에코프로비엠": "247540",
    "에코프로": "086520",
    "네이버": "035420",
    "카카오": "035720",
    "포스코홀딩스": "005490",
}

US_NAME_MAP = {
    "애플": "AAPL",
    "마이크로소프트": "MSFT",
    "엔비디아": "NVDA",
    "테슬라": "TSLA",
    "아마존": "AMZN",
    "구글": "GOOGL",
    "알파벳": "GOOGL",
    "메타": "META",
    "넷플릭스": "NFLX",
    "브로드컴": "AVGO",
    "팔란티어": "PLTR",
    "아이온큐": "IONQ",
    "인텔": "INTC",
    "AMD": "AMD",
    "버크셔": "BRK-B",
    "코스트코": "COST"
}

@st.cache_data(ttl=86400)
def get_us_stock_name(symbol: str) -> str:
    """yfinance를 이용해 미국 주식의 기업명을 가져옵니다."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        name = info.get('shortName') or info.get('longName') or symbol
        if name and len(name) > 25:
            name = name[:22] + "..."
        return name
    except Exception:
        return symbol


def resolve_stock_info(input_str: str, krx_df: pd.DataFrame = None) -> tuple[str, str, str, str]:
    """
    사용자가 선택하거나 입력한 문자열을 분석하여 
    (clean_ticker, display_name, market, currency) 4개 요소를 반환합니다.
    - 한국 주식: 6자리 종목코드('009150'), 종목명('삼성전기'), 시장('KOSPI' 또는 'KOSDAQ'), 통화('KRW')
    - 미국 주식: 티커 심볼('AAPL'), 종목명('Apple' 또는 '애플'), 시장('미국 (US)'), 통화('USD')
    """
    if krx_df is None:
        krx_df = load_krx_data()

    if not input_str or input_str == "선택 안 함":
        return "005930", "삼성전자", "KOSPI", "KRW"

    input_clean = input_str.strip()

    # 1. '종목명 (코드/티커)' 포맷 파싱 (예: '삼성전기 (009150)', '애플 (AAPL)')
    if "(" in input_clean and input_clean.endswith(")"):
        code_part = input_clean.split("(")[-1].replace(")", "").strip()
        name_part = input_clean.split("(")[0].strip()

        # 한국 6자리 종목 코드인 경우
        if code_part.isdigit() and len(code_part) == 6:
            code_match = krx_df[krx_df['Code'] == code_part]
            if not code_match.empty:
                market = code_match.iloc[0]['Market']
                name = code_match.iloc[0]['Name']
                return code_part, name, market, "KRW"
            return code_part, name_part, "한국 (KRX)", "KRW"
        else:
            # 미국 주식 티커
            symbol = code_part.upper()
            return symbol, name_part, "미국 (US)", "USD"

    # 2. 파이프 기호 포맷 파싱 (예: '005930 | 삼성전자')
    if " | " in input_clean:
        part0 = input_clean.split(" | ")[0].strip()
        part1 = input_clean.split(" | ")[1].strip()
        if part0.isdigit():
            code_match = krx_df[krx_df['Code'] == part0]
            market = code_match.iloc[0]['Market'] if not code_match.empty else "한국 (KRX)"
            return part0, part1, market, "KRW"
        else:
            return part0.upper(), part1, "미국 (US)", "USD"

    # 3. 별칭 사전 확인
    clean_no_space = input_clean.replace(" ", "")
    if clean_no_space in COMMON_ALIASES:
        alias_code = COMMON_ALIASES[clean_no_space]
        code_match = krx_df[krx_df['Code'] == alias_code]
        if not code_match.empty:
            return alias_code, code_match.iloc[0]['Name'], code_match.iloc[0]['Market'], "KRW"

    # 4. 한국 주식 코드로 검색 (접미사 .KS, .KQ 제거)
    code_clean = input_clean
    if code_clean.endswith(('.KS', '.KQ', '.ks', '.kq')):
        code_clean = code_clean[:-3]

    if code_clean.isdigit():
        code_padded = code_clean.zfill(6)
        code_match = krx_df[krx_df['Code'] == code_padded]
        if not code_match.empty:
            return code_padded, code_match.iloc[0]['Name'], code_match.iloc[0]['Market'], "KRW"
        else:
            return code_padded, f"종목코드({code_padded})", "한국 (KRX)", "KRW"

    # 5. 한국 주식 종목명 정확 일치 (공백/대소문자 무시)
    name_match = krx_df[krx_df['Name'].str.lower() == input_clean.lower()]
    if not name_match.empty:
        return name_match.iloc[0]['Code'], name_match.iloc[0]['Name'], name_match.iloc[0]['Market'], "KRW"

    names_no_space = krx_df['Name'].astype(str).str.replace(" ", "").str.lower()
    nospace_match = krx_df[names_no_space == clean_no_space.lower()]
    if not nospace_match.empty:
        return nospace_match.iloc[0]['Code'], nospace_match.iloc[0]['Name'], nospace_match.iloc[0]['Market'], "KRW"

    # 6. 한국 주식 종목명 부분 일치 검색
    partial_match = krx_df[names_no_space.str.contains(clean_no_space.lower(), regex=False)]
    if not partial_match.empty:
        starts = krx_df[names_no_space.str.startswith(clean_no_space.lower())]
        chosen = starts.iloc[0] if not starts.empty else partial_match.iloc[0]
        return chosen['Code'], chosen['Name'], chosen['Market'], "KRW"

    # 7. 미국 주식 한글명 매핑
    for us_name, symbol in US_NAME_MAP.items():
        if us_name in clean_no_space:
            return symbol, get_us_stock_name(symbol), "미국 (US)", "USD"

    # 8. 미국 주식 및 해외 티커
    symbol = input_clean.upper()
    display_name = POPULAR_US_STOCKS.get(symbol, get_us_stock_name(symbol))
    return symbol, display_name, "미국 (US)", "USD"


def resolve_ticker(input_query: str, market: str = None, krx_df: pd.DataFrame = None) -> tuple[str, str]:
    """
    31 PerformanceChart 및 기존 함수 호환: (ticker, stock_name) 반환
    """
    clean_ticker, display_name, _, _ = resolve_stock_info(input_query, krx_df=krx_df)
    return clean_ticker, display_name


def resolve_stock_selection(selected_display: str, krx_df: pd.DataFrame = None) -> tuple[str, str]:
    """
    선택된 '종목명 (코드/티커)' 문자열을 파싱하여 티커와 표시 이름으로 변환 (31 PerformanceChart 호환)
    """
    clean_ticker, display_name, _, _ = resolve_stock_info(selected_display, krx_df=krx_df)
    return clean_ticker, display_name


def fetch_raw_data(ticker: str, market: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    시장 구분(한국/미국)에 맞추어 주가 데이터를 수집합니다.
    """
    df = pd.DataFrame()
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    clean_ticker = ticker.replace(".KS", "").replace(".KQ", "").replace(".ks", "").replace(".kq", "")
    is_kr_market = market in ["한국 (KRX)", "KOSPI", "KOSDAQ"] or clean_ticker.isdigit()

    if is_kr_market:
        try:
            # FinanceDataReader 우선 시도 (순수 6자리 코드 필요)
            df = fdr.DataReader(clean_ticker, start_str, end_str)
            if df.empty or len(df) < 5:
                # yfinance로 보조 시도 (.KS or .KQ)
                primary_suffix = ".KQ" if market == "KOSDAQ" else ".KS"
                secondary_suffix = ".KS" if primary_suffix == ".KQ" else ".KQ"
                
                df_yf = yf.download(f"{clean_ticker}{primary_suffix}", start=start_str, end=end_str, progress=False)
                if df_yf.empty or len(df_yf) < 5:
                    df_yf = yf.download(f"{clean_ticker}{secondary_suffix}", start=start_str, end=end_str, progress=False)
                if not df_yf.empty:
                    df = df_yf
        except Exception:
            # 오류 시 yfinance 폴백
            try:
                for suffix in [".KS", ".KQ"]:
                    df_yf = yf.download(f"{clean_ticker}{suffix}", start=start_str, end=end_str, progress=False)
                    if not df_yf.empty:
                        df = df_yf
                        break
            except Exception:
                pass
    else:
        # 미국 시장
        try:
            df = yf.download(ticker, start=start_str, end=end_str, progress=False)
        except Exception:
            try:
                df = fdr.DataReader(ticker, start_str, end_str)
            except Exception:
                pass

    if df.empty:
        return pd.DataFrame()

    # MultiIndex 컬럼 평탄화 (yfinance의 최신 버전 대응)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 컬럼 표준화
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    })

    # 필수 컬럼 존재 확인
    req_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in req_cols:
        if col not in df.columns:
            return pd.DataFrame()

    # 결측치 제거 및 타입 변환
    df = df[req_cols].dropna()
    for col in req_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()

    # 날짜 인덱스 타임존 제거
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df = df.sort_index()
    return df


def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    일봉 데이터를 주봉(Weekly) 또는 월봉(Monthly)으로 리샘플링합니다.
    """
    if timeframe == "일봉":
        return df

    agg_rules = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }

    if timeframe == "주봉":
        # 주 단위 리샘플링 (금요일 기준)
        resampled = df.resample("W-FRI").agg(agg_rules).dropna()
    elif timeframe == "월봉":
        # 월 단위 리샘플링 (월말 기준)
        resampled = df.resample("ME").agg(agg_rules).dropna()
    else:
        resampled = df

    return resampled


def get_stock_data(ticker_input: str, market: str = None, timeframe: str = "일봉", period_key: str = "1Y"):
    """
    티커 및 기간 설정을 바탕으로 주가 데이터를 불러오고 전처리합니다.
    기술적 지표 계산(200선 등)을 위해 기간 시작 전 여유 버퍼를 확보한 후 슬라이싱합니다.
    """
    clean_ticker, stock_name, resolved_market, currency = resolve_stock_info(ticker_input)
    years = PERIOD_YEARS.get(period_key, 1)

    end_date = datetime.now()
    # 지표 계산 버퍼: 일봉의 경우 최소 1년(또는 기간의 30%) 추가 데이터 확보
    buffer_days = max(365, int(years * 365 * 0.3))
    start_date = end_date - timedelta(days=years * 365 + buffer_days)
    target_start_date = end_date - timedelta(days=years * 365)

    market_for_fetch = resolved_market if resolved_market in ["KOSPI", "KOSDAQ", "한국 (KRX)"] else (market if market else resolved_market)
    raw_df = fetch_raw_data(clean_ticker, market_for_fetch, start_date, end_date)
    if raw_df.empty or len(raw_df) < 15:
        return None, None, f"'{ticker_input}'({stock_name}) 종목 데이터를 조회할 수 없습니다. 티커 또는 종목명을 확인해 주세요."

    # 봉 주기에 맞게 리샘플링
    resampled_df = resample_data(raw_df, timeframe)
    if len(resampled_df) < 10:
        return None, None, f"'{stock_name}' 종목의 {timeframe} 데이터 수가 충분하지 않습니다."

    # 메타데이터 계산 (최신 시세 기준)
    latest = resampled_df.iloc[-1]
    prev = resampled_df.iloc[-2] if len(resampled_df) > 1 else latest
    
    current_price = float(latest["Close"])
    prev_price = float(prev["Close"])
    change = current_price - prev_price
    change_pct = (change / prev_price * 100) if prev_price != 0 else 0.0

    # 52주(최근 1년) 최고/최저가
    one_year_ago = end_date - timedelta(days=365)
    recent_1y_df = raw_df[raw_df.index >= one_year_ago]
    if not recent_1y_df.empty:
        high_52w = float(recent_1y_df["High"].max())
        low_52w = float(recent_1y_df["Low"].min())
    else:
        high_52w = float(raw_df["High"].max())
        low_52w = float(raw_df["Low"].min())

    display_market = resolved_market if resolved_market in ["KOSPI", "KOSDAQ"] else ("한국 (KRX)" if currency == "KRW" else "미국 (US)")

    metadata = {
        "ticker": clean_ticker,
        "name": stock_name,
        "market": display_market,
        "currency": currency,
        "current_price": current_price,
        "prev_price": prev_price,
        "change": change,
        "change_pct": change_pct,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "volume": int(latest["Volume"]),
        "timeframe": timeframe,
        "period": period_key,
        "target_start_date": target_start_date
    }

    return resampled_df, metadata, None
