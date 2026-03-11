"""LangChain 에이전트용 가격 조회 도구 모음"""
import json
from langchain.tools import tool
from app.utils.opensearch_client import get_opensearch_client


@tool
def search_price(item_name: str) -> str:
    """품목명으로 최신 가격을 검색합니다. 예: 쌀, 찹쌀, 콩, 팥, 녹두, 고구마, 감자

    Args:
        item_name: 검색할 품목명
    """
    client = get_opensearch_client()
    query = {
        "query": {
            "match": {
                "item_name": item_name
            }
        },
        "sort": [{"date": {"order": "desc"}}],
        "size": 10,
    }
    result = client.search(index="prices-daily-goods", body=query)
    hits = result.get("hits", {}).get("hits", [])

    if not hits:
        return f"'{item_name}'에 대한 가격 정보를 찾을 수 없습니다."

    lines = []
    for hit in hits:
        src = hit["_source"]
        today = src.get("price_today", 0)
        one_week = src.get("price_1week_ago", 0)
        one_month = src.get("price_1month_ago", 0)

        diff_week = today - one_week if one_week else 0
        diff_month = today - one_month if one_month else 0

        lines.append(
            f"- {src['item_name']} ({src.get('kind_name', '')}): "
            f"오늘 {today:,}원/{src.get('unit', '')} "
            f"(1주전 대비 {diff_week:+,}원, 1개월전 대비 {diff_month:+,}원)"
        )
    return "\n".join(lines)


@tool
def compare_prices(item_name: str, period: str = "1주") -> str:
    """품목의 기간별 가격 변동을 비교합니다. 날짜별 가격 데이터를 테이블로 반환합니다.

    Args:
        item_name: 비교할 품목명
        period: 비교 기간 (예: "1주", "2주", "1개월")
    """
    client = get_opensearch_client()
    query = {
        "query": {
            "match": {
                "item_name": item_name
            }
        },
        "sort": [{"date": {"order": "desc"}}],
        "size": 10,
    }
    result = client.search(index="prices-daily-goods", body=query)
    hits = result.get("hits", {}).get("hits", [])

    if not hits:
        return f"'{item_name}'의 가격 데이터를 찾을 수 없습니다."

    # 각 품종별로 기간 가격 비교 테이블 구성
    names = []
    units = []
    today_prices = []
    day1_prices = []
    week1_prices = []
    week2_prices = []
    month1_prices = []

    for hit in hits:
        src = hit["_source"]
        names.append(f"{src['item_name']}({src.get('kind_name', '')})")
        units.append(src.get("unit", ""))
        today_prices.append(str(src.get("price_today", 0)))
        day1_prices.append(str(src.get("price_1day_ago", 0)))
        week1_prices.append(str(src.get("price_1week_ago", 0)))
        week2_prices.append(str(src.get("price_2week_ago", 0)))
        month1_prices.append(str(src.get("price_1month_ago", 0)))

    table_data = json.dumps({
        "dataTable": {
            "columns": {
                "품목": names,
                "단위": units,
                "오늘": today_prices,
                "1일전": day1_prices,
                "1주전": week1_prices,
                "2주전": week2_prices,
                "1개월전": month1_prices,
            }
        }
    }, ensure_ascii=False)

    # 요약 텍스트
    if hits:
        src = hits[0]["_source"]
        today = src.get("price_today", 0)
        week_ago = src.get("price_1week_ago", 0)
        diff = today - week_ago
        direction = "올랐어" if diff > 0 else "내렸어" if diff < 0 else "그대로야"
        summary = f"{item_name} 1주 전 대비 {abs(diff):,}원 {direction}."
    else:
        summary = f"{item_name} 가격 데이터입니다."

    return f"{summary}\n\n[TABLE_DATA]{table_data}[/TABLE_DATA]"


@tool
def create_price_chart(item_name: str) -> str:
    """품목의 가격 추이 차트를 생성합니다. 당일~1년전까지의 가격 변동을 차트로 보여줍니다.

    Args:
        item_name: 차트를 생성할 품목명
    """
    client = get_opensearch_client()
    query = {
        "query": {
            "match": {
                "item_name": item_name
            }
        },
        "sort": [{"date": {"order": "desc"}}],
        "size": 5,
    }
    result = client.search(index="prices-daily-goods", body=query)
    hits = result.get("hits", {}).get("hits", [])

    if not hits:
        return f"'{item_name}'의 차트 데이터를 찾을 수 없습니다."

    # 첫 번째 품종으로 차트 생성
    src = hits[0]["_source"]
    kind = src.get("kind_name", "")
    categories = ["1년전", "1개월전", "2주전", "1주전", "1일전", "오늘"]
    prices = [
        src.get("price_1year_ago", 0),
        src.get("price_1month_ago", 0),
        src.get("price_2week_ago", 0),
        src.get("price_1week_ago", 0),
        src.get("price_1day_ago", 0),
        src.get("price_today", 0),
    ]

    chart_data = json.dumps({
        "title": {"text": f"{src['item_name']}({kind}) 가격 추이"},
        "chart": {"type": "line"},
        "xAxis": {"categories": categories},
        "yAxis": {"title": {"text": "가격(원)"}},
        "series": [{"name": f"{src['item_name']}({kind})", "data": prices}],
    }, ensure_ascii=False)

    today = src.get("price_today", 0)
    year_ago = src.get("price_1year_ago", 0)
    diff = today - year_ago
    direction = "올랐어" if diff > 0 else "내렸어" if diff < 0 else "그대로야"

    return f"{src['item_name']}({kind}) 1년간 {abs(diff):,}원 {direction}.\n\n[CHART_DATA]{chart_data}[/CHART_DATA]"
