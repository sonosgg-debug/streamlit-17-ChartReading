"""
chart_plotter.py
Plotly를 활용하여 캔들스틱, 이동평균선, 볼린저 밴드, 거래량, MACD, RSI를
하나의 시간축으로 동기화한 고해상도 금융 인터랙티브 차트를 생성하는 모듈
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_financial_chart(
    df: pd.DataFrame,
    metadata: dict,
    sr_levels: dict,
    show_bollinger: bool = True,
    show_ma: bool = True,
    target_start_date=None
) -> go.Figure:
    """
    주가 및 각종 보조지표 서브플롯 차트를 생성합니다.
    - Row 1: 주가 캔들스틱 + 이동평균선 + 볼린저 밴드 + 지지/저항선
    - Row 2: 거래량 및 20일 거래량 이평선
    - Row 3: MACD (MACD Line, Signal, Histogram)
    - Row 4: RSI (14) 및 과매수/과매도 밴드
    """
    # 4개 행의 서브플롯 생성
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.52, 0.14, 0.18, 0.16],
        subplot_titles=(
            f"<b>{metadata['name']} ({metadata['ticker']}) - {metadata['timeframe']} 차트</b>",
            "<b>거래량 (Volume)</b>",
            "<b>MACD (12, 26, 9)</b>",
            "<b>RSI (14)</b>"
        )
    )

    # ---------------- 1. Row 1: 주가 및 오버레이 ----------------
    # 1) 볼린저 밴드 (배경 레이어로 먼저 배치하여 채움이 캔들과 이평선 뒤에 은은하고 선명하게 깔리도록 구성)
    if show_bollinger and "BB_Upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["BB_Upper"],
                name="BB 상단 (20,2)",
                line=dict(color="#00E5FF", width=2.0),  # 선명한 실선 경계
                hoverinfo="name+y"
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["BB_Lower"],
                name="BB 하단 (20,2)",
                line=dict(color="#00E5FF", width=2.0),  # 선명한 실선 경계
                fill="tonexty",
                fillcolor="rgba(0, 229, 255, 0.07)",  # 투명도를 높여 차트 봉(양봉/음봉) 색상이 전혀 가려지지 않는 은은한 채움
                hoverinfo="name+y"
            ),
            row=1, col=1
        )

    # 2) 캔들스틱 (볼린저 밴드 채움 위에 전면 배치)
    candle = go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="주가 (OHLC)",
        increasing_line_color="#ef4444",  # 선명한 레드 (상승)
        decreasing_line_color="#3b82f6",  # 선명한 블루 (하락)
        showlegend=False
    )
    fig.add_trace(candle, row=1, col=1)

    # 3) 이동평균선
    if show_ma:
        ma_configs = [
            ("SMA_5", "5선", "#93C5FD", 1.0),     # 라이트 블루
            ("SMA_20", "20선(생명선)", "#F59E0B", 1.8), # 앰버 골드
            ("SMA_60", "60선(수급선)", "#10B981", 1.4), # 그린
            ("SMA_120", "120선(경기선)", "#8B5CF6", 1.2), # 바이올렛
            ("SMA_200", "200선(대세선)", "#EC4899", 1.5), # 핑크
        ]
        for col, label, color, width in ma_configs:
            if col in df.columns and df[col].notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[col],
                        name=label,
                        line=dict(color=color, width=width),
                        hoverinfo="name+y"
                    ),
                    row=1, col=1
                )

    # 지지선 / 저항선 수평 가이드라인
    if sr_levels:
        sup_1 = sr_levels["support_1"]
        res_1 = sr_levels["resistance_1"]
        curr_price = metadata["current_price"]

        # 1차 저항선 라인 (빨간 점선 저항선 + 오른쪽 끝 선명한 옐로우 폰트)
        fig.add_hline(
            y=res_1,
            line_dash="dot",
            line_color="rgba(239, 68, 68, 0.75)",
            line_width=1.3,
            annotation_text=f" 1차 저항선 ({res_1:,.1f})",
            annotation_position="top right",
            annotation_font=dict(size=11, color="#FFE600", family="sans-serif"),
            row=1, col=1
        )
        # 1차 지지선 라인 (초록 점선 지지선 + 오른쪽 끝 선명한 옐로우 폰트)
        fig.add_hline(
            y=sup_1,
            line_dash="dot",
            line_color="rgba(16, 185, 129, 0.75)",
            line_width=1.3,
            annotation_text=f" 1차 지지선 ({sup_1:,.1f})",
            annotation_position="bottom right",
            annotation_font=dict(size=11, color="#FFE600", family="sans-serif"),
            row=1, col=1
        )

    # ---------------- 2. Row 2: 거래량 (Volume) ----------------
    is_zero_vol = bool(df["Volume"].sum() == 0)
    if is_zero_vol:
        fig.add_annotation(
            text="해당 지수는 산출 특성상 자체 거래량이 집계되지 않습니다",
            xref="x2", yref="y2",
            x=df.index[len(df) // 2], y=0,
            showarrow=False,
            font=dict(size=12, color="#94a3b8"),
            row=2, col=1
        )
    else:
        # 주가 상승/하락 여부에 따른 거래량 바 색상 (29 MultiIndicatorEnsemble과 일관된 선명한 레드/블루)
        vol_colors = np.where(df["Close"] >= df["Open"], "#ef4444", "#3b82f6")
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="거래량",
                marker=dict(color=vol_colors),
                showlegend=False
            ),
            row=2, col=1
        )
        if "Vol_SMA20" in df.columns and df["Vol_SMA20"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Vol_SMA20"],
                    name="거래량 20선",
                    line=dict(color="#F59E0B", width=1.2),
                    hoverinfo="name+y"
                ),
                row=2, col=1
            )

    # ---------------- 3. Row 3: MACD ----------------
    if "MACD" in df.columns:
        # MACD Histogram (29 MultiIndicatorEnsemble과 동일하게 0선 이상 레드, 미만 블루 적용)
        hist_colors = np.where(df["MACD_Hist"] >= 0, "#ef4444", "#3b82f6")
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["MACD_Hist"],
                name="MACD 히스토그램",
                marker=dict(color=hist_colors),
                showlegend=False
            ),
            row=3, col=1
        )
        # MACD Line (파란 히스토그램 위에서도 선명하게 돋보이는 맑은 스카이블루)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["MACD"],
                name="MACD",
                line=dict(color="#38bdf8", width=1.5),
                hoverinfo="name+y"
            ),
            row=3, col=1
        )
        # MACD Signal (선명한 로즈 레드)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["MACD_Signal"],
                name="Signal",
                line=dict(color="#f43f5e", width=1.5),
                hoverinfo="name+y"
            ),
            row=3, col=1
        )
        # 0선 기준선
        fig.add_hline(y=0, line_color="rgba(156, 163, 175, 0.4)", line_width=1, row=3, col=1)

    # ---------------- 4. Row 4: RSI ----------------
    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["RSI"],
                name="RSI (14)",
                line=dict(color="#8B5CF6", width=1.5),
                hoverinfo="name+y"
            ),
            row=4, col=1
        )
        # 과매수(70)선 & 과매도(30)선
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="rgba(239, 68, 68, 0.6)",
            line_width=1,
            annotation_text="과매수 (70)",
            annotation_position="top left",
            annotation_font=dict(size=9, color="#EF4444"),
            row=4, col=1
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="rgba(16, 185, 129, 0.6)",
            line_width=1,
            annotation_text="과매도 (30)",
            annotation_position="bottom left",
            annotation_font=dict(size=9, color="#10B981"),
            row=4, col=1
        )
        fig.add_hrect(
            y0=30,
            y1=70,
            fillcolor="rgba(139, 92, 246, 0.05)",
            line_width=0,
            row=4, col=1
        )

    # ---------------- 오른쪽 Y축 활성화 더미 트레이스 ----------------
    # Plotly에서 yaxis5~8을 활성화하여 오른쪽에 좌측과 동일한 단위 및 눈금이 동시에 표시되도록 함
    first_idx = df.index[0]

    # Row 1 (가격/지수) 오른쪽 Y축 더미 트레이스
    fig.add_trace(
        go.Scatter(
            x=[first_idx],
            y=[df["Close"].iloc[0]],
            yaxis="y5",
            xaxis="x",
            showlegend=False,
            opacity=0,
            hoverinfo="skip"
        )
    )

    # Row 2 (거래량) 오른쪽 Y축 더미 트레이스
    if not is_zero_vol:
        fig.add_trace(
            go.Scatter(
                x=[first_idx],
                y=[df["Volume"].iloc[0]],
                yaxis="y6",
                xaxis="x2",
                showlegend=False,
                opacity=0,
                hoverinfo="skip"
            )
        )

    # Row 3 (MACD) 오른쪽 Y축 더미 트레이스
    if "MACD" in df.columns and df["MACD"].notna().any():
        macd_valid = df["MACD"].dropna()
        fig.add_trace(
            go.Scatter(
                x=[macd_valid.index[0]],
                y=[macd_valid.iloc[0]],
                yaxis="y7",
                xaxis="x3",
                showlegend=False,
                opacity=0,
                hoverinfo="skip"
            )
        )

    # Row 4 (RSI) 오른쪽 Y축 더미 트레이스
    if "RSI" in df.columns and df["RSI"].notna().any():
        rsi_valid = df["RSI"].dropna()
        fig.add_trace(
            go.Scatter(
                x=[rsi_valid.index[0]],
                y=[rsi_valid.iloc[0]],
                yaxis="y8",
                xaxis="x4",
                showlegend=False,
                opacity=0,
                hoverinfo="skip"
            )
        )

    # ---------------- 레이아웃 및 스타일링 ----------------
    # 사용자가 요청한 조회 기간에 맞춰 기본 x축 줌 범위 설정
    xaxis_range = None
    if target_start_date is not None:
        xaxis_range = [target_start_date, df.index[-1]]

    # 일봉 차트의 경우 주말(토/일) 및 시장 휴장일(공휴일) 공백 제거 (봉이 끊기지 않고 연속 연결)
    rangebreaks_config = []
    is_daily = (metadata.get("timeframe") == "일봉") or (
        len(df) > 1 and (df.index[1:] - df.index[:-1]).median() <= pd.Timedelta(days=3)
    )
    if is_daily and len(df) > 1:
        rangebreaks_config.append(dict(bounds=["sat", "mon"]))  # 토요일~월요일 아침 주말 숨김
        all_b_days = pd.date_range(start=df.index[0], end=df.index[-1], freq="B")
        holidays = [d.strftime("%Y-%m-%d") for d in all_b_days if d not in df.index]
        if holidays:
            rangebreaks_config.append(dict(values=holidays))  # 평일 휴장일(명절, 공휴일) 숨김

    price_title = "지수" if metadata.get("is_index") else "가격"

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1E293B",
        plot_bgcolor="#0F172A",
        margin=dict(l=55, r=55, t=75, b=30),
        height=830,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(15, 23, 42, 0.8)",        # 다크 배경
            bordercolor="rgba(148, 163, 184, 0.4)",  # 은은한 반투명 경계선
            font=dict(color="#f8fafc", size=12)     # 선명한 텍스트
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.005,          # 타이틀 아랫줄, 차트 상단 바로 위에 위치
            xanchor="center",
            x=0.5,            # 범례 가운데 정렬
            bgcolor="rgba(30, 41, 59, 0.85)",
            bordercolor="#334155",
            borderwidth=1,
            font=dict(size=10, color="#f8fafc")
        ),
        xaxis=dict(
            rangeslider=dict(visible=False),
            range=xaxis_range,
            showgrid=True,
            gridcolor="#334155"
        ),
        xaxis2=dict(rangeslider=dict(visible=False), showgrid=True, gridcolor="#334155"),
        xaxis3=dict(rangeslider=dict(visible=False), showgrid=True, gridcolor="#334155"),
        xaxis4=dict(rangeslider=dict(visible=False), showgrid=True, gridcolor="#334155"),
        yaxis1=dict(title=price_title, showgrid=True, gridcolor="#334155", automargin=True),
        yaxis2=dict(title="거래량", showgrid=True, gridcolor="#334155", automargin=True),
        yaxis3=dict(title="MACD", showgrid=True, gridcolor="#334155", automargin=True),
        yaxis4=dict(title="RSI", range=[0, 100], showgrid=True, gridcolor="#334155", automargin=True),
        yaxis5=dict(
            title=price_title,
            overlaying="y",
            matches="y",
            side="right",
            showgrid=False,
            automargin=True
        ),
        yaxis6=dict(
            title="거래량" if not is_zero_vol else None,
            overlaying="y2",
            matches="y2",
            side="right",
            showgrid=False,
            automargin=True
        ),
        yaxis7=dict(
            title="MACD",
            overlaying="y3",
            matches="y3",
            side="right",
            showgrid=False,
            automargin=True
        ),
        yaxis8=dict(
            title="RSI",
            range=[0, 100],
            overlaying="y4",
            matches="y4",
            side="right",
            showgrid=False,
            automargin=True
        )
    )

    # 일봉 차트의 모든 서브플롯 X축에 주말/공휴일 공백 제거 적용
    if rangebreaks_config:
        fig.update_xaxes(rangebreaks=rangebreaks_config)

    # 어노테이션 스타일링: 1차 저항선/지지선은 선명한 옐로우(#FFE600), 서브플롯 타이틀은 #8AB4F8 적용
    for i, ann in enumerate(fig['layout']['annotations']):
        text = str(ann.text) if ann.text else ""
        if "1차 저항선" in text or "1차 지지선" in text:
            ann['font'] = dict(color='#FFE600', size=11, family='sans-serif')
        elif "과매수" in text:
            ann['font'] = dict(color='#EF4444', size=9)
        elif "과매도" in text:
            ann['font'] = dict(color='#10B981', size=9)
        else:
            # 서브플롯 타이틀 ("차트", "거래량", "MACD", "RSI")
            ann['font'] = dict(color='#8AB4F8', size=13)
            # 첫 번째 메인 차트 타이틀은 범례 윗줄 중앙에 배치
            if i == 0:
                ann.update(y=1.055, yanchor='bottom', x=0.5, xanchor='center')

    return fig
