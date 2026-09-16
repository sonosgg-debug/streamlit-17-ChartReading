"""
analyzer.py
각종 기술적 보조지표(이동평균선, 볼린저 밴드, RSI, MACD, 스토캐스틱, 거래량 등)를 계산하고,
정량적 스코어링을 통해 5단계 투자 의견과 전문가 분석 해설을 생성하는 모듈
"""

import pandas as pd
import numpy as np
import ta

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    주가 데이터프레임에 각종 기술적 보조지표 컬럼을 추가합니다.
    """
    df = df.copy()

    # 1. 이동평균선 (SMA: 5, 20, 60, 120, 200)
    df["SMA_5"] = df["Close"].rolling(window=5).mean()
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["SMA_60"] = df["Close"].rolling(window=60).mean()
    df["SMA_120"] = df["Close"].rolling(window=120).mean()
    df["SMA_200"] = df["Close"].rolling(window=200).mean()

    # 지수이동평균선 (EMA: 12, 26)
    df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()

    # 2. 볼린저 밴드 (Bollinger Bands: 20, 2)
    bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Lower"] = bb.bollinger_lband()
    df["BB_Percent"] = bb.bollinger_pband()
    df["BB_Width"] = bb.bollinger_wband()

    # 3. 모멘텀: RSI (14)
    rsi_indicator = ta.momentum.RSIIndicator(close=df["Close"], window=14)
    df["RSI"] = rsi_indicator.rsi()

    # 4. 모멘텀: Stochastic Slow (%K: 14-3, %D: 3)
    stoch = ta.momentum.StochasticOscillator(
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        window=14,
        smooth_window=3
    )
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # 5. 추세: MACD (12, 26, 9)
    macd = ta.trend.MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()

    # 6. 거래량: 20일 거래량 이평선 및 거래량 변화율
    df["Vol_SMA20"] = df["Volume"].rolling(window=20).mean()
    df["Vol_Ratio"] = (df["Volume"] / df["Vol_SMA20"].replace(0, np.nan)) * 100

    # 7. 변동성: ATR (14)
    atr = ta.volatility.AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14)
    df["ATR"] = atr.average_true_range()

    return df


def calculate_support_resistance(df: pd.DataFrame, window: int = 40):
    """
    최근 N봉의 스윙 고점과 저점, 볼린저 밴드를 활용해 핵심 지지/저항 가격대를 산출합니다.
    """
    recent = df.tail(window)
    current_price = float(df["Close"].iloc[-1])
    
    # 최근 최고가와 최저가
    local_high = float(recent["High"].max())
    local_low = float(recent["Low"].min())
    
    # 20일 이평선 및 볼린저 밴드
    sma20 = float(df["SMA_20"].iloc[-1]) if "SMA_20" in df and not pd.isna(df["SMA_20"].iloc[-1]) else current_price
    bb_upper = float(df["BB_Upper"].iloc[-1]) if "BB_Upper" in df and not pd.isna(df["BB_Upper"].iloc[-1]) else current_price * 1.05
    bb_lower = float(df["BB_Lower"].iloc[-1]) if "BB_Lower" in df and not pd.isna(df["BB_Lower"].iloc[-1]) else current_price * 0.95
    atr = float(df["ATR"].iloc[-1]) if "ATR" in df and not pd.isna(df["ATR"].iloc[-1]) else (current_price * 0.02)

    # 1차 지지선: 현재가 바로 아래의 주요 레벨 (20일선, 볼린저 하단, 또는 최근 저점)
    below_levels = sorted([lvl for lvl in [sma20, bb_lower, local_low] if lvl < current_price], reverse=True)
    sup_1 = below_levels[0] if below_levels else current_price - (atr * 1.5)
    sup_2 = below_levels[1] if len(below_levels) > 1 else local_low

    # 1차 저항선: 현재가 바로 위의 주요 레벨 (20일선, 볼린저 상단, 또는 최근 고점)
    above_levels = sorted([lvl for lvl in [sma20, bb_upper, local_high] if lvl > current_price])
    res_1 = above_levels[0] if above_levels else current_price + (atr * 1.5)
    res_2 = above_levels[1] if len(above_levels) > 1 else local_high

    # 손절 권장가: 1차 지지선 하회 혹은 현재가 - 2.0 * ATR
    stop_loss = max(sup_1 * 0.98, current_price - (atr * 2.0))
    # 1차 목표가
    target_price = res_1

    return {
        "support_1": sup_1,
        "support_2": sup_2,
        "resistance_1": res_1,
        "resistance_2": res_2,
        "stop_loss": stop_loss,
        "target_price": target_price,
        "atr": atr
    }


def evaluate_investment_opinion(df: pd.DataFrame) -> dict:
    """
    최신 기술적 지표들을 정량 평가하여 종합 점수(-100 ~ +100)와 5단계 투자 의견을 도출합니다.
    5단계: 매수(Buy), 비중확대(Overweight), 중립(Neutral), 비중축소(Underweight), 매도(Sell)
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    close = float(latest["Close"])
    sma5 = float(latest["SMA_5"]) if pd.notna(latest.get("SMA_5")) else close
    sma20 = float(latest["SMA_20"]) if pd.notna(latest.get("SMA_20")) else close
    sma60 = float(latest["SMA_60"]) if pd.notna(latest.get("SMA_60")) else close
    sma120 = float(latest["SMA_120"]) if pd.notna(latest.get("SMA_120")) else close
    sma200 = float(latest["SMA_200"]) if pd.notna(latest.get("SMA_200")) else close

    rsi = float(latest["RSI"]) if pd.notna(latest.get("RSI")) else 50.0
    stoch_k = float(latest["Stoch_K"]) if pd.notna(latest.get("Stoch_K")) else 50.0
    stoch_d = float(latest["Stoch_D"]) if pd.notna(latest.get("Stoch_D")) else 50.0
    prev_stoch_k = float(prev["Stoch_K"]) if pd.notna(prev.get("Stoch_K")) else 50.0
    prev_stoch_d = float(prev["Stoch_D"]) if pd.notna(prev.get("Stoch_D")) else 50.0

    macd_line = float(latest["MACD"]) if pd.notna(latest.get("MACD")) else 0.0
    macd_sig = float(latest["MACD_Signal"]) if pd.notna(latest.get("MACD_Signal")) else 0.0
    macd_hist = float(latest["MACD_Hist"]) if pd.notna(latest.get("MACD_Hist")) else 0.0
    prev_macd_hist = float(prev["MACD_Hist"]) if pd.notna(prev.get("MACD_Hist")) else 0.0

    bb_pct = float(latest["BB_Percent"]) if pd.notna(latest.get("BB_Percent")) else 0.5
    bb_width = float(latest["BB_Width"]) if pd.notna(latest.get("BB_Width")) else 10.0
    vol_ratio = float(latest["Vol_Ratio"]) if pd.notna(latest.get("Vol_Ratio")) else 100.0

    # 영역별 세부 진단 결과 및 점수
    score_details = {}
    
    # ---------------- 1. 추세 분석 (최대 30점) ----------------
    trend_score = 0
    trend_notes = []

    # 이평선 정배열/역배열
    if sma5 > sma20 and sma20 > sma60:
        if sma60 > sma120:
            trend_score += 15
            trend_notes.append("단기·중기·장기 이평선 완벽한 정배열(상승 추세 구축)")
        else:
            trend_score += 10
            trend_notes.append("단기 및 중기 이평선 정배열(상승 전환 국면)")
    elif sma5 < sma20 and sma20 < sma60:
        if sma60 < sma120:
            trend_score -= 15
            trend_notes.append("단기·중기·장기 이평선 역배열(하락 추세 지속)")
        else:
            trend_score -= 10
            trend_notes.append("단기 및 중기 이평선 역배열(약세 국면)")
    else:
        trend_score += 0
        trend_notes.append("이평선 혼조세(박스권 횡보 양상)")

    # 20일선(생명선) 위치
    if close > sma20:
        trend_score += 10
        trend_notes.append("주가가 20일 생명선 상단에 위치하여 지지력 유효")
    else:
        trend_score -= 10
        trend_notes.append("주가가 20일 생명선 하단에 위치하여 단기 저항 압력 존재")

    # 200일선(대세 판단선) 위치
    if pd.notna(latest.get("SMA_200")):
        if close > sma200:
            trend_score += 5
            trend_notes.append("200일 장기 추세선 상회로 중장기 상승 기조 유지")
        else:
            trend_score -= 5
            trend_notes.append("200일 장기 추세선 하회로 중장기 보수적 접근 필요")

    score_details["trend"] = {
        "score": trend_score,
        "max": 30,
        "status": "상승세 (Bullish)" if trend_score > 5 else ("하락세 (Bearish)" if trend_score < -5 else "중립 (Neutral)"),
        "notes": trend_notes
    }

    # ---------------- 2. 모멘텀 지표 (최대 25점) ----------------
    momentum_score = 0
    momentum_notes = []

    # RSI 진단
    if rsi >= 70:
        momentum_score -= 8
        momentum_notes.append(f"RSI {rsi:.1f}로 과매수(Overbought) 영역 진입, 단기 차익실현 매물 경계")
    elif rsi <= 30:
        momentum_score += 12
        momentum_notes.append(f"RSI {rsi:.1f}로 과매도(Oversold) 구간 도달, 기술적 반등 기대 가능")
    elif 50 <= rsi < 70:
        momentum_score += 10
        momentum_notes.append(f"RSI {rsi:.1f}로 중립선(50) 상회하며 안정적 매수 모멘텀 유지")
    else:
        momentum_score -= 5
        momentum_notes.append(f"RSI {rsi:.1f}로 중립선(50) 하회하며 매수 탄력 둔화")

    # Stochastic Slow 크로스 진단
    if stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
        momentum_score += 10
        momentum_notes.append("스토캐스틱 골든크로스 발생(단기 반등 매수 신호)")
    elif stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
        momentum_score -= 10
        momentum_notes.append("스토캐스틱 데드크로스 발생(단기 조정 매도 신호)")
    elif stoch_k > stoch_d:
        momentum_score += 5
        momentum_notes.append("스토캐스틱 %K선이 %D선 상단 유지 중")
    else:
        momentum_score -= 5
        momentum_notes.append("스토캐스틱 %K선이 %D선 하단 위치 중")

    score_details["momentum"] = {
        "score": momentum_score,
        "max": 25,
        "status": "강세 (Strong)" if momentum_score > 5 else ("약세 (Weak)" if momentum_score < -5 else "중립 (Neutral)"),
        "notes": momentum_notes
    }

    # ---------------- 3. MACD 추세 강도 (최대 25점) ----------------
    macd_score = 0
    macd_notes = []

    # MACD 시그널 크로스
    if macd_line > macd_sig:
        macd_score += 12
        if macd_hist > prev_macd_hist:
            macd_score += 3
            macd_notes.append("MACD 시그널 상회 및 히스토그램 양봉 확장(상승 탄력 가속)")
        else:
            macd_notes.append("MACD 시그널 상회 유지 중이나 히스토그램 탄력 다소 완만")
    else:
        macd_score -= 12
        if macd_hist < prev_macd_hist:
            macd_score -= 3
            macd_notes.append("MACD 시그널 하회 및 히스토그램 음봉 확장(하락 모멘텀 지속)")
        else:
            macd_notes.append("MACD 시그널 하회 중이나 하락 탄력 소폭 둔화")

    # MACD 제로선 위치
    if macd_line > 0:
        macd_score += 10
        macd_notes.append("MACD 제로(0)선 상단에 위치하여 대세 상승 사이클 영역")
    else:
        macd_score -= 10
        macd_notes.append("MACD 제로(0)선 하단에 위치하여 대세 하락 사이클 영역")

    score_details["macd"] = {
        "score": macd_score,
        "max": 25,
        "status": "매수 신호 (Bullish)" if macd_score > 5 else ("매도 신호 (Bearish)" if macd_score < -5 else "중립 (Neutral)"),
        "notes": macd_notes
    }

    # ---------------- 4. 변동성 및 수급 (최대 20점) ----------------
    vol_score = 0
    vol_notes = []

    # 볼린저 밴드 위치 (%B)
    if bb_pct > 1.0:
        vol_score -= 5
        vol_notes.append("볼린저 밴드 상단 밴드 초과 돌파(단기 과열, 밴드 내 회귀 가능성)")
    elif bb_pct < 0.0:
        vol_score += 8
        vol_notes.append("볼린저 밴드 하단 밴드 이탈(과매도권, 단기 지지 반등 노림수)")
    elif 0.5 <= bb_pct <= 0.85:
        vol_score += 8
        vol_notes.append("볼린저 밴드 중심선~상단 구간 내 안정적인 밴드 상승 라이딩")
    else:
        vol_score -= 3
        vol_notes.append("볼린저 밴드 중심선 하단에 머물며 밴드 하단 탐색")

    # 거래량 수급 상태
    is_zero_volume = (latest.get("Volume", 0) == 0) or (df["Volume"].sum() == 0)
    if is_zero_volume:
        vol_notes.append("지수/종목 특성상 거래량이 미집계되어 수급 지표는 중립으로 반영")
    elif vol_ratio >= 150:
        if close > prev["Close"]:
            vol_score += 12
            vol_notes.append(f"20일 평균 대비 거래량 {vol_ratio:.0f}% 급증하며 양봉 형성(강력한 매수 수급 유입)")
        else:
            vol_score -= 12
            vol_notes.append(f"20일 평균 대비 거래량 {vol_ratio:.0f}% 급증하며 음봉 형성(차익/투매 매물 출회)")
    elif vol_ratio >= 90:
        if close >= prev["Close"]:
            vol_score += 5
            vol_notes.append(f"평균 수준의 양호한 거래량({vol_ratio:.0f}%) 동반")
        else:
            vol_score -= 3
            vol_notes.append(f"평균 수준의 거래량({vol_ratio:.0f}%) 동반한 조정")
    else:
        vol_score -= 2
        vol_notes.append(f"거래량 20일 평균 대비 {vol_ratio:.0f}% 수준으로 거래 한산")

    score_details["volatility"] = {
        "score": vol_score,
        "max": 20,
        "status": "양호 (Favorable)" if vol_score > 3 else ("부담 (Cautious)" if vol_score < -3 else "중립 (Neutral)"),
        "notes": vol_notes
    }

    # 종합 점수 합산 (-100 ~ +100)
    total_score = trend_score + momentum_score + macd_score + vol_score
    total_score = max(-100, min(100, total_score))

    # 5단계 투자 의견 판정
    # 매도(Sell) - 비중축소(Underweight) - 중립(Neutral) - 비중확대(Overweight) - 매수(Buy)
    if total_score >= 45:
        opinion = "매수 (Buy)"
        opinion_en = "BUY"
        badge_color = "#10B981"  # Emerald Green
        opinion_summary = "추세, 모멘텀, 거래량 등 핵심 기술적 지표가 일제히 매수 신호를 보내고 있습니다. 상승 추세가 강력하게 유지되고 있어 적극적인 매수 또는 기존 포지션 유지가 유리한 국면입니다."
    elif total_score >= 15:
        opinion = "비중확대 (Overweight)"
        opinion_en = "OVERWEIGHT"
        badge_color = "#3B82F6"  # Blue
        opinion_summary = "우상향 추세 기조가 유효하거나 건전한 눌림목 조정 후 반등 흐름이 관측됩니다. 지지선 근처에서 분할 매수로 포트폴리오 비중을 늘려가기에 적절한 시점입니다."
    elif total_score >= -14:
        opinion = "중립 (Neutral)"
        opinion_en = "NEUTRAL"
        badge_color = "#6B7280"  # Gray
        opinion_summary = "매수세와 매도세가 팽팽하게 맞서며 뚜렷한 추세 없이 박스권 횡보를 보이고 있습니다. 섣부른 추격 매수보다는 확실한 방향성 돌파가 확인될 때까지 관망(Hold)을 권장합니다."
    elif total_score >= -44:
        opinion = "비중축소 (Underweight)"
        opinion_en = "UNDERWEIGHT"
        badge_color = "#F59E0B"  # Amber
        opinion_summary = "단기 고점 징후가 나타나거나 핵심 지지선에 대한 하방 압력이 커지고 있습니다. 상승 탄력이 둔화되고 있으므로 리스크 관리를 위해 일부 차익실현 및 비중 축소를 고려할 때입니다."
    else:
        opinion = "매도 (Sell)"
        opinion_en = "SELL"
        badge_color = "#EF4444"  # Red
        opinion_summary = "이평선 역배열 및 하락 추세가 심화되고 있으며, MACD와 모멘텀 지표 모두 하방을 지목하고 있습니다. 추가 하락 리스크가 높으므로 손절 기준 준수 및 현금 비중 확대가 시급합니다."

    # 지지/저항 및 가격 가이드라인 계산
    sr_levels = calculate_support_resistance(df)

    # 전략 제언
    strategy_commentary = generate_strategy_commentary(
        opinion, total_score, close, sr_levels, score_details
    )

    return {
        "opinion": opinion,
        "opinion_en": opinion_en,
        "badge_color": badge_color,
        "total_score": total_score,
        "summary": opinion_summary,
        "score_details": score_details,
        "support_resistance": sr_levels,
        "strategy": strategy_commentary,
        "indicators": {
            "close": close,
            "sma5": sma5,
            "sma20": sma20,
            "sma60": sma60,
            "sma120": sma120,
            "sma200": sma200,
            "rsi": rsi,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "macd": macd_line,
            "macd_sig": macd_sig,
            "macd_hist": macd_hist,
            "bb_upper": float(latest["BB_Upper"]) if pd.notna(latest.get("BB_Upper")) else close,
            "bb_lower": float(latest["BB_Lower"]) if pd.notna(latest.get("BB_Lower")) else close,
            "bb_width": bb_width,
            "vol_ratio": vol_ratio
        }
    }


def generate_strategy_commentary(opinion: str, total_score: int, close: float, sr: dict, score_details: dict) -> dict:
    """
    실전 투자자를 위한 구체적인 포지션별(신규 매수자 / 기존 보유자) 대응 전략을 작성합니다.
    """
    sup_1 = sr["support_1"]
    res_1 = sr["resistance_1"]
    stop_loss = sr["stop_loss"]
    target = sr["target_price"]

    if "Buy" in opinion:
        entry_strategy = f"1차 지지선({sup_1:,.1f})을 지지 기반으로 삼고, 현재가 부근 또는 단기 눌림목 발생 시 분할 매수 전략이 유효합니다."
        holding_strategy = f"1차 목표가({target:,.1f}) 도달 시 분할 익절을 검토하되, 20일 이동평균선을 이탈하지 않는 한 추세 추종(Trend Following)으로 수익을 극대화하십시오."
        risk_management = f"손절 기준가는 {stop_loss:,.1f}로 설정하며, 이를 종가 기준으로 하향 이탈할 경우 즉각적인 리스크 관리가 요구됩니다."
    elif "Overweight" in opinion:
        entry_strategy = f"상승 추세로의 안착을 확인하며 분할 매수로 비중을 늘려가는 전략이 적합합니다. {sup_1:,.1f} 선을 지지선으로 설정하십시오."
        holding_strategy = f"단기 저항선({res_1:,.1f}) 돌파 여부를 주시하며, 돌파 성공 시 목표가({target:,.1f})까지 홀딩을 권장합니다."
        risk_management = f"손절가는 {stop_loss:,.1f} 수준으로 설정하여 예상치 못한 추세 이탈에 대비하십시오."
    elif "Neutral" in opinion:
        entry_strategy = f"현재는 방향성이 결정되지 않은 박스권 국면입니다. 상단 저항선({res_1:,.1f})을 거래량과 함께 돌파하거나 하단 지지선({sup_1:,.1f})에서 지지가 확인될 때까지 신규 진입을 자제하십시오."
        holding_strategy = f"보유 중이라면 단기 박스권 상단({res_1:,.1f}) 부근에서 비중을 일부 축소하고, 하단 지지선 이탈 시 손절을 준비하는 보수적 태도가 필요합니다."
        risk_management = f"지지선 {sup_1:,.1f} 이탈 시 단기 급락 가능성이 있으므로 손절선({stop_loss:,.1f})을 철저히 준수하십시오."
    elif "Underweight" in opinion:
        entry_strategy = f"하방 압력이 높은 구간이므로 성급한 저가 매수(물타기)를 삼가고, 지표의 바닥 확인 시그널이 뜰 때까지 기다려야 합니다."
        holding_strategy = f"반등 시 1차 저항선({res_1:,.1f}) 부근을 비중 축소 및 현금화 기회로 활용하십시오."
        risk_management = f"손절 기준가 {stop_loss:,.1f} 이탈 시 손실 폭 확대를 방지하기 위해 적극적인 비중 축소를 실행하십시오."
    else:  # Sell
        entry_strategy = f"신규 매수는 절대 금물이며, 기술적 낙폭 과대에 따른 일시적 반등(Dead Cat Bounce)에 유의해야 합니다."
        holding_strategy = f"추세적 하락이 진행 중이므로 반등 시마다 매도하여 현금 비중을 100% 가깝게 확보하는 것이 유리합니다."
        risk_management = f"주요 지지선이 붕괴된 상태이므로 무조건적인 추가 매수를 지양하고 자본 보존을 최우선으로 두십시오."

    return {
        "entry_strategy": entry_strategy,
        "holding_strategy": holding_strategy,
        "risk_management": risk_management
    }
