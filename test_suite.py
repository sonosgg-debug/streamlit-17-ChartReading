"""
test_suite.py
다양한 종목, 지수, 주기, 기간에 대한 기술적 분석 엔진 통합 테스트
"""

from data_loader import get_stock_data, get_index_data, INDEX_DISPLAY_NAMES
from analyzer import calculate_technical_indicators, evaluate_investment_opinion
from chart_plotter import create_financial_chart

def test_scenario(name, ticker, market, timeframe, period):
    print(f"Testing Stock [{name}] - Ticker: {ticker}, Market: {market}, Timeframe: {timeframe}, Period: {period}")
    df, meta, err = get_stock_data(ticker, market, timeframe, period)
    if err:
        print(f"  FAILED to load data: {err}")
        return False
    
    df = calculate_technical_indicators(df)
    eval_res = evaluate_investment_opinion(df)
    fig = create_financial_chart(df, meta, eval_res["support_resistance"], target_start_date=meta["target_start_date"])
    
    print(f"  SUCCESS: Rows={len(df)}, Opinion={eval_res['opinion']}, Score={eval_res['total_score']}, ChartTraces={len(fig.data)}")
    return True

def test_index_scenario(index_name, timeframe, period):
    print(f"Testing Index [{index_name}] - Timeframe: {timeframe}, Period: {period}")
    df, meta, err = get_index_data(index_name, timeframe, period)
    if err:
        print(f"  FAILED to load index data: {err}")
        return False
    
    df = calculate_technical_indicators(df)
    eval_res = evaluate_investment_opinion(df)
    fig = create_financial_chart(df, meta, eval_res["support_resistance"], target_start_date=meta["target_start_date"])
    
    print(f"  SUCCESS: Rows={len(df)}, Price={meta['current_price']:.2f}{meta['currency']}, Opinion={eval_res['opinion']}, Score={eval_res['total_score']}, ChartTraces={len(fig.data)}")
    return True

if __name__ == "__main__":
    scenarios = [
        ("KR Samsung 1Y Daily", "005930", "한국 (KRX)", "일봉", "1Y"),
        ("KR Hynix 3Y Weekly", "000660", "한국 (KRX)", "주봉", "3Y"),
        ("KR Naver 5Y Monthly", "035420", "한국 (KRX)", "월봉", "5Y"),
        ("KR Samsung Electro-Mechanics by Name", "삼성전기", "한국 (KRX)", "일봉", "1Y"),
        ("KR Samsung Electro-Mechanics by Code", "009150", "한국 (KRX)", "일봉", "1Y"),
        ("KR Samsung Electro-Mechanics Formatted", "삼성전기 (009150)", "전체 (통합)", "일봉", "1Y"),
        ("US Nvidia Formatted", "엔비디아 (NVDA)", "전체 (통합)", "일봉", "1Y"),
        ("US Apple 1Y Daily", "AAPL", "미국 (US)", "일봉", "1Y"),
        ("US Nvidia 5Y Weekly", "NVDA", "미국 (US)", "주봉", "5Y"),
        ("US Tesla 10Y Monthly", "TSLA", "미국 (US)", "월봉", "10Y"),
    ]

    index_scenarios = [
        # 새 표준 지수 명칭
        ("KOSPI", "일봉", "1Y"),
        ("KOSDAQ", "일봉", "1Y"),
        ("S&P 500", "일봉", "1Y"),
        ("NASDAQ", "주봉", "3Y"),
        ("Philadelphia Semi (SOX)", "월봉", "5Y"),
        # 하위 호환성 검증
        ("코스피 (KOSPI)", "일봉", "1Y"),
        ("나스닥 종합 (NASDAQ)", "주봉", "3Y"),
    ]

    all_passed = True
    print("=== 개별 종목 테스트 ===")
    for sc in scenarios:
        ok = test_scenario(*sc)
        if not ok:
            all_passed = False

    print("\n=== 시장 지수 테스트 ===")
    for idx_name, tf, per in index_scenarios:
        ok = test_index_scenario(idx_name, tf, per)
        if not ok:
            all_passed = False

    print("\n------------------------------")
    print("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED!")

