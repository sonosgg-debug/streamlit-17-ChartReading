"""
data_loader.py
한국(KRX) 및 미국(US) 주식 시장의 데이터를 불러오고 리샘플링 및 정제하는 모듈
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import FinanceDataReader as fdr

# 한국 대표 종목 프리셋
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

# 미국 대표 종목 프리셋
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

# 기간별 연도 매핑
PERIOD_YEARS = {
    "1Y": 1,
    "3Y": 3,
    "5Y": 5,
    "10Y": 10,
    "20Y": 20
}

def resolve_ticker(input_query: str, market: str) -> tuple[str, str]:
    """
    사용자가 입력한 종목명이나 티커를 실제 조회 가능한 티커와 이름으로 변환합니다.
    """
    query = input_query.strip()
    if not query:
        if market == "한국 (KRX)":
            return "005930", "삼성전자"
        else:
            return "AAPL", "Apple (애플)"

    if market == "한국 (KRX)":
        # 1. 프리셋에서 티커 일치
        if query in POPULAR_KR_STOCKS:
            return query, POPULAR_KR_STOCKS[query]
        # 2. 프리셋에서 종목명 일치
        for code, name in POPULAR_KR_STOCKS.items():
            if query.lower() in name.lower():
                return code, name
        # 3. 6자리 숫자 티커인 경우
        if len(query) == 6 and query.isdigit():
            return query, f"종목코드({query})"
        # 4. 숫자 앞 0 채우기 (예: 5930 -> 005930)
        if query.isdigit() and len(query) < 6:
            code = query.zfill(6)
            return code, POPULAR_KR_STOCKS.get(code, f"종목코드({code})")
        return query, query
    else:
        # 미국 주식
        upper_query = query.upper()
        if upper_query in POPULAR_US_STOCKS:
            return upper_query, POPULAR_US_STOCKS[upper_query]
        for ticker, name in POPULAR_US_STOCKS.items():
            if query.lower() in name.lower():
                return ticker, name
        return upper_query, upper_query


def fetch_raw_data(ticker: str, market: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    시장 구분(한국/미국)에 맞추어 주가 데이터를 수집합니다.
    """
    df = pd.DataFrame()
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    if market == "한국 (KRX)":
        try:
            # FinanceDataReader 우선 시도
            df = fdr.DataReader(ticker, start_str, end_str)
            if df.empty or len(df) < 5:
                # yfinance로 보조 시도 (.KS or .KQ)
                yf_ticker = f"{ticker}.KS"
                df_yf = yf.download(yf_ticker, start=start_str, end=end_str, progress=False)
                if df_yf.empty or len(df_yf) < 5:
                    yf_ticker = f"{ticker}.KQ"
                    df_yf = yf.download(yf_ticker, start=start_str, end=end_str, progress=False)
                if not df_yf.empty:
                    df = df_yf
        except Exception:
            # 오류 시 yfinance 폴백
            try:
                for suffix in [".KS", ".KQ"]:
                    df_yf = yf.download(f"{ticker}{suffix}", start=start_str, end=end_str, progress=False)
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


def get_stock_data(ticker_input: str, market: str, timeframe: str, period_key: str = "1Y"):
    """
    티커 및 기간 설정을 바탕으로 주가 데이터를 불러오고 전처리합니다.
    기술적 지표 계산(200선 등)을 위해 기간 시작 전 여유 버퍼를 확보한 후 슬라이싱합니다.
    """
    ticker, stock_name = resolve_ticker(ticker_input, market)
    years = PERIOD_YEARS.get(period_key, 1)

    end_date = datetime.now()
    # 지표 계산 버퍼: 일봉의 경우 최소 1년(또는 기간의 30%) 추가 데이터 확보
    buffer_days = max(365, int(years * 365 * 0.3))
    start_date = end_date - timedelta(days=years * 365 + buffer_days)
    target_start_date = end_date - timedelta(days=years * 365)

    raw_df = fetch_raw_data(ticker, market, start_date, end_date)
    if raw_df.empty or len(raw_df) < 15:
        return None, None, f"'{ticker}' 종목 데이터를 조회할 수 없습니다. 티커 또는 시장 구분을 확인해 주세요."

    # 봉 주기에 맞게 리샘플링
    resampled_df = resample_data(raw_df, timeframe)
    if len(resampled_df) < 10:
        return None, None, f"'{ticker}' 종목의 {timeframe} 데이터 수가 충분하지 않습니다."

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

    currency = "KRW" if market == "한국 (KRX)" else "USD"

    metadata = {
        "ticker": ticker,
        "name": stock_name,
        "market": market,
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
