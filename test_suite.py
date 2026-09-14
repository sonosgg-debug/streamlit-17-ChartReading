"""
test_suite.py
다양한 종목, 주기, 기간에 대한 기술적 분석 엔진 통합 테스트
"""

from data_loader import get_stock_data
from analyzer import calculate_technical_indicators, evaluate_investment_opinion
from chart_plotter import create_financial_chart

def test_scenario(name, ticker, market, timeframe, period):
    print(f"Testing [{name}] - Ticker: {ticker}, Market: {market}, Timeframe: {timeframe}, Period: {period}")
    df, meta, err = get_stock_data(ticker, market, timeframe, period)
    if err:
        print(f"  FAILED to load data: {err}")
        return False
    
    df = calculate_technical_indicators(df)
    eval_res = evaluate_investment_opinion(df)
    fig = create_financial_chart(df, meta, eval_res["support_resistance"], target_start_date=meta["target_start_date"])
    
    print(f"  SUCCESS: Rows={len(df)}, Opinion={eval_res['opinion']}, Score={eval_res['total_score']}, ChartTraces={len(fig.data)}")
    return True

if __name__ == "__main__":
    scenarios = [
        ("KR Samsung 1Y Daily", "005930", "한국 (KRX)", "일봉", "1Y"),
        ("KR Hynix 3Y Weekly", "000660", "한국 (KRX)", "주봉", "3Y"),
        ("KR Naver 5Y Monthly", "035420", "한국 (KRX)", "월봉", "5Y"),
        ("US Apple 1Y Daily", "AAPL", "미국 (US)", "일봉", "1Y"),
        ("US Nvidia 5Y Weekly", "NVDA", "미국 (US)", "주봉", "5Y"),
        ("US Tesla 10Y Monthly", "TSLA", "미국 (US)", "월봉", "10Y"),
    ]

    all_passed = True
    for sc in scenarios:
        ok = test_scenario(*sc)
        if not ok:
            all_passed = False

    print("\n------------------------------")
    print("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED!")
