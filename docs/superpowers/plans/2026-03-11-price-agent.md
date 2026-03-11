# 생필품 가격 에이전트 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공공데이터 포털 참가격 API 데이터를 OpenSearch에 적재하고, 자취고수 페르소나의 LangChain 에이전트로 가격 조회/비교/차트 기능 구현

**Architecture:** 데이터 수집 스크립트가 공공데이터 API → OpenSearch로 적재. LangChain 에이전트는 @tool 도구 3개(검색, 비교, 차트)로 OpenSearch를 조회하여 응답. 기존 process_query()의 스트리밍 파싱 로직은 그대로 유지.

**Tech Stack:** LangChain v1.0, LangGraph (create_react_agent), ChatOpenAI, opensearch-py, httpx

---

## Chunk 1: 환경 설정 및 의존성

### Task 1: 의존성 추가

**Files:**
- Modify: `agent/pyproject.toml:6-16`

- [ ] **Step 1: opensearch-py 의존성 추가**

`agent/pyproject.toml`의 dependencies에 추가:

```toml
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "langchain>=1.0.0",
    "langchain-openai>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.25.0",
    "opik>=1.10.4",
    "opensearch-py>=2.4.0",
]
```

- [ ] **Step 2: 의존성 설치**

실행: `cd agent && uv sync`
예상: opensearch-py 및 관련 패키지 설치 완료

- [ ] **Step 3: 커밋**

```bash
git add agent/pyproject.toml agent/uv.lock
git commit -m "feat: opensearch-py 의존성 추가"
```

### Task 2: 환경 변수 설정

**Files:**
- Modify: `agent/app/core/config.py:15-42`
- Modify: `agent/.env`
- Modify: `agent/env.sample`

- [ ] **Step 1: config.py에 OpenSearch, 공공데이터 설정 추가**

`agent/app/core/config.py`의 Settings 클래스에 추가:

```python
class Settings(BaseSettings):
    # API 설정
    API_V1_PREFIX: str
    CORS_ORIGINS: List[str] = ["*"]

    # LangChain 설정
    OPENAI_API_KEY: str
    OPENAI_MODEL: str

    # OpenSearch 설정
    OPENSEARCH_HOST: str = "https://localhost:9200"
    OPENSEARCH_USERNAME: str = "admin"
    OPENSEARCH_PASSWORD: str = "admin"
    OPENSEARCH_VERIFY_CERTS: bool = False

    # 공공데이터 포털
    PUBLIC_DATA_API_KEY: str = ""

    # DeepAgents 설정
    DEEPAGENT_RECURSION_LIMIT: int = 20

    OPIK: OpikSettings | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
```

- [ ] **Step 2: .env에 실제 값 추가**

`agent/.env`에 추가:

```env
# OpenSearch
OPENSEARCH_HOST=https://bigdata04.didim365.co:9201
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=Fpemdnemzpdl123$
OPENSEARCH_VERIFY_CERTS=false

# 공공데이터 포털
PUBLIC_DATA_API_KEY=g6JAyYA1Rw3V5kKpRO52c4FjsbfFx8XedX8G%2BL2mMgunFRdMEB03lnF1mw3H71LupTA%2FRdjiYkqYbWB8Xr%2FAPA%3D%3D
```

- [ ] **Step 3: env.sample 업데이트**

`agent/env.sample`에 키 이름만 추가 (값은 비움):

```env
API_V1_PREFIX = "/api/v1"
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
DEEPAGENT_RECURSION_LIMIT=20

# OpenSearch
OPENSEARCH_HOST=https://localhost:9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin
OPENSEARCH_VERIFY_CERTS=false

# 공공데이터 포털
PUBLIC_DATA_API_KEY=your_public_data_api_key
```

- [ ] **Step 4: 서버 실행으로 설정 확인**

실행: `cd agent && uv run python -c "from app.core.config import settings; print(settings.OPENSEARCH_HOST)"`
예상: `https://bigdata04.didim365.co:9201`

- [ ] **Step 5: 커밋**

```bash
git add agent/app/core/config.py agent/env.sample
git commit -m "feat: OpenSearch, 공공데이터 환경 변수 추가"
```

---

## Chunk 2: 데이터 수집 모듈

### Task 3: OpenSearch 클라이언트 유틸리티

**Files:**
- Create: `agent/app/utils/opensearch_client.py`

- [ ] **Step 1: OpenSearch 클라이언트 생성 유틸리티 작성**

```python
from opensearchpy import OpenSearch
from app.core.config import settings


def get_opensearch_client() -> OpenSearch:
    """OpenSearch 클라이언트를 생성하여 반환합니다."""
    client = OpenSearch(
        hosts=[settings.OPENSEARCH_HOST],
        http_auth=(settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD),
        verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
        ssl_show_warn=False,
    )
    return client
```

- [ ] **Step 2: 연결 테스트**

실행: `cd agent && uv run python -c "from app.utils.opensearch_client import get_opensearch_client; c = get_opensearch_client(); print(c.info())"`
예상: OpenSearch 클러스터 정보 출력 (버전, 이름 등)

- [ ] **Step 3: 커밋**

```bash
git add agent/app/utils/opensearch_client.py
git commit -m "feat: OpenSearch 클라이언트 유틸리티 추가"
```

### Task 4: 공공데이터 API 조사 및 수집 스크립트

**Files:**
- Create: `agent/scripts/collect_prices.py`

- [ ] **Step 1: 공공데이터 API 응답 구조 확인**

참가격 생필품 가격정보 API를 테스트 호출하여 실제 응답 필드를 확인합니다.
간단한 테스트 스크립트로 1건만 호출:

```python
"""공공데이터 참가격 API 응답 구조 확인용 테스트 스크립트"""
import httpx
from app.core.config import settings

# 참가격 API 엔드포인트 (실제 URL은 공공데이터 포털에서 확인 필요)
url = "http://www.kamis.or.kr/service/price/xml.do"
params = {
    "action": "dailyPriceByCategoryList",
    "p_product_cls_code": "01",
    "p_country_code": "1101",
    "p_regday": "2026-03-11",
    "p_convert_kg_yn": "N",
    "p_cert_key": settings.PUBLIC_DATA_API_KEY,
    "p_cert_id": "didim365",
    "p_returntype": "json",
}

resp = httpx.get(url, params=params, verify=False)
print(resp.json())
```

실행: `cd agent && uv run python scripts/collect_prices.py`
예상: API 응답 JSON 출력 → 필드 구조 확인 후 아래 Step 2의 매핑을 조정

- [ ] **Step 2: 수집 스크립트 작성**

API 응답 필드에 맞춰 OpenSearch 문서로 변환하여 적재:

```python
"""공공데이터 참가격 생필품 가격정보 → OpenSearch 적재 스크립트"""
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.utils.opensearch_client import get_opensearch_client

INDEX_NAME = "prices-daily-goods"

# 참가격 API 기본 URL (KAMIS 농산물유통정보)
API_URL = "http://www.kamis.or.kr/service/price/xml.do"


def fetch_prices(date: str, category_code: str = "01", country_code: str = "1101"):
    """공공데이터 API에서 가격 정보를 조회합니다."""
    params = {
        "action": "dailyPriceByCategoryList",
        "p_product_cls_code": category_code,
        "p_country_code": country_code,
        "p_regday": date,
        "p_convert_kg_yn": "N",
        "p_cert_key": settings.PUBLIC_DATA_API_KEY,
        "p_cert_id": "didim365",
        "p_returntype": "json",
    }
    resp = httpx.get(API_URL, params=params, verify=False)
    resp.raise_for_status()
    return resp.json()


def create_index_if_not_exists(client):
    """인덱스가 없으면 생성합니다."""
    if not client.indices.exists(index=INDEX_NAME):
        mapping = {
            "mappings": {
                "properties": {
                    "item_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "item_code": {"type": "keyword"},
                    "category_name": {"type": "keyword"},
                    "price": {"type": "integer"},
                    "unit": {"type": "keyword"},
                    "market_name": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "date": {"type": "date", "format": "yyyy-MM-dd"},
                }
            }
        }
        client.indices.create(index=INDEX_NAME, body=mapping)
        print(f"인덱스 '{INDEX_NAME}' 생성 완료")


def index_prices(client, items: list, date: str):
    """가격 데이터를 OpenSearch에 적재합니다."""
    count = 0
    for item in items:
        # API 응답 필드에 맞춰 매핑 조정 필요
        doc = {
            "item_name": item.get("item_name", ""),
            "item_code": item.get("item_code", ""),
            "category_name": item.get("category_name", ""),
            "price": int(item.get("dpr1", "0").replace(",", "") or 0),
            "unit": item.get("unit", ""),
            "market_name": item.get("market_name", ""),
            "region": item.get("country_name", ""),
            "date": date,
        }
        client.index(index=INDEX_NAME, body=doc)
        count += 1
    return count


def main():
    """메인 실행 함수"""
    import argparse
    parser = argparse.ArgumentParser(description="참가격 생필품 가격 데이터 수집")
    parser.add_argument("--date", default="2026-03-11", help="조회 날짜 (YYYY-MM-DD)")
    args = parser.parse_args()

    client = get_opensearch_client()
    create_index_if_not_exists(client)

    data = fetch_prices(args.date)

    # API 응답 구조에 맞춰 아이템 리스트 추출 (실제 응답 확인 후 조정)
    items = data.get("price", {}).get("item", []) if isinstance(data.get("price"), dict) else []

    if not items:
        print("수집할 데이터가 없습니다. API 응답을 확인하세요.")
        print(f"응답: {data}")
        return

    count = index_prices(client, items, args.date)
    print(f"{args.date} 데이터 {count}건 적재 완료")


if __name__ == "__main__":
    main()
```

참고: API 응답 구조는 Step 1에서 확인한 후 `fetch_prices`, `index_prices`의 필드 매핑을 조정해야 합니다.

- [ ] **Step 3: 수집 스크립트 실행**

실행: `cd agent && uv run python scripts/collect_prices.py --date 2026-03-11`
예상: "2026-03-11 데이터 N건 적재 완료"

- [ ] **Step 4: 적재 데이터 확인**

실행: `cd agent && uv run python -c "from app.utils.opensearch_client import get_opensearch_client; c = get_opensearch_client(); print(c.search(index='prices-daily-goods', body={'query': {'match_all': {}}, 'size': 2}))"`
예상: 적재된 문서 2건 출력

- [ ] **Step 5: 커밋**

```bash
git add agent/scripts/collect_prices.py
git commit -m "feat: 공공데이터 참가격 수집 스크립트 추가"
```

---

## Chunk 3: 에이전트 도구 구현

### Task 5: search_price 도구

**Files:**
- Create: `agent/app/agents/tools.py`

- [ ] **Step 1: search_price 도구 작성**

```python
"""LangChain 에이전트용 가격 조회 도구 모음"""
import json
from langchain.tools import tool
from app.utils.opensearch_client import get_opensearch_client


@tool
def search_price(item_name: str) -> str:
    """품목명으로 최신 가격을 검색합니다. 예: 계란, 우유, 양파, 라면

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
        lines.append(
            f"- {src['item_name']}: {src['price']:,}원 "
            f"({src.get('unit', '')}) "
            f"[{src.get('market_name', '')} / {src.get('region', '')}] "
            f"({src['date']})"
        )
    return "\n".join(lines)
```

- [ ] **Step 2: 도구 단독 테스트**

실행: `cd agent && uv run python -c "from app.agents.tools import search_price; print(search_price.invoke('계란'))"`
예상: 계란 가격 정보 텍스트 출력 (데이터가 적재되어 있어야 함)

- [ ] **Step 3: 커밋**

```bash
git add agent/app/agents/tools.py
git commit -m "feat: search_price 도구 구현"
```

### Task 6: compare_prices 도구

**Files:**
- Modify: `agent/app/agents/tools.py`

- [ ] **Step 1: compare_prices 도구 추가**

`agent/app/agents/tools.py`에 추가:

```python
from datetime import datetime, timedelta


def _parse_period(period: str) -> str:
    """기간 문자열을 시작 날짜로 변환합니다."""
    now = datetime.now()
    if "주" in period:
        weeks = int("".join(filter(str.isdigit, period)) or "1")
        start = now - timedelta(weeks=weeks)
    elif "개월" in period or "달" in period:
        months = int("".join(filter(str.isdigit, period)) or "1")
        start = now - timedelta(days=months * 30)
    else:
        start = now - timedelta(weeks=1)
    return start.strftime("%Y-%m-%d")


@tool
def compare_prices(item_name: str, period: str = "1주") -> str:
    """품목의 기간별 가격 변동을 비교합니다. 날짜별 가격 데이터를 테이블로 반환합니다.

    Args:
        item_name: 비교할 품목명
        period: 비교 기간 (예: "1주", "2주", "1개월")
    """
    client = get_opensearch_client()
    start_date = _parse_period(period)

    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"item_name": item_name}},
                    {"range": {"date": {"gte": start_date}}},
                ]
            }
        },
        "sort": [{"date": {"order": "asc"}}],
        "size": 100,
    }
    result = client.search(index="prices-daily-goods", body=query)
    hits = result.get("hits", {}).get("hits", [])

    if not hits:
        return f"'{item_name}'의 {period} 가격 데이터를 찾을 수 없습니다."

    # 날짜별 평균 가격 집계
    date_prices = {}
    for hit in hits:
        src = hit["_source"]
        d = src["date"]
        if d not in date_prices:
            date_prices[d] = []
        date_prices[d].append(src["price"])

    dates = sorted(date_prices.keys())
    avg_prices = [round(sum(date_prices[d]) / len(date_prices[d])) for d in dates]

    # 테이블 데이터 구성 (프론트엔드 GridViewer 형식)
    table_data = json.dumps({
        "dataTable": {
            "columns": {
                "날짜": dates,
                "평균가격(원)": [str(p) for p in avg_prices],
            }
        }
    }, ensure_ascii=False)

    # 요약 텍스트
    if len(avg_prices) >= 2:
        diff = avg_prices[-1] - avg_prices[0]
        direction = "올랐어" if diff > 0 else "내렸어" if diff < 0 else "그대로야"
        summary = f"{item_name} {period} 동안 {abs(diff):,}원 {direction}."
    else:
        summary = f"{item_name} 가격 데이터입니다."

    return f"{summary}\n\n[TABLE_DATA]{table_data}[/TABLE_DATA]"
```

- [ ] **Step 2: 도구 단독 테스트**

실행: `cd agent && uv run python -c "from app.agents.tools import compare_prices; print(compare_prices.invoke({'item_name': '계란', 'period': '1주'}))"`
예상: 가격 비교 요약 텍스트 + 테이블 JSON 출력

- [ ] **Step 3: 커밋**

```bash
git add agent/app/agents/tools.py
git commit -m "feat: compare_prices 도구 구현"
```

### Task 7: create_price_chart 도구

**Files:**
- Modify: `agent/app/agents/tools.py`

- [ ] **Step 1: create_price_chart 도구 추가**

`agent/app/agents/tools.py`에 추가:

```python
@tool
def create_price_chart(item_name: str, period: str = "1개월") -> str:
    """품목의 가격 추이 차트를 생성합니다. Highcharts 형식의 차트 데이터를 반환합니다.

    Args:
        item_name: 차트를 생성할 품목명
        period: 차트 기간 (예: "1주", "1개월", "3개월")
    """
    client = get_opensearch_client()
    start_date = _parse_period(period)

    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"item_name": item_name}},
                    {"range": {"date": {"gte": start_date}}},
                ]
            }
        },
        "sort": [{"date": {"order": "asc"}}],
        "size": 100,
    }
    result = client.search(index="prices-daily-goods", body=query)
    hits = result.get("hits", {}).get("hits", [])

    if not hits:
        return f"'{item_name}'의 {period} 차트 데이터를 찾을 수 없습니다."

    # 날짜별 평균 가격 집계
    date_prices = {}
    for hit in hits:
        src = hit["_source"]
        d = src["date"]
        if d not in date_prices:
            date_prices[d] = []
        date_prices[d].append(src["price"])

    dates = sorted(date_prices.keys())
    avg_prices = [round(sum(date_prices[d]) / len(date_prices[d])) for d in dates]

    # Highcharts 형식 차트 데이터
    chart_data = json.dumps({
        "title": {"text": f"{item_name} 가격 추이 ({period})"},
        "chart": {"type": "line"},
        "xAxis": {"categories": dates},
        "yAxis": {"title": {"text": "가격(원)"}},
        "series": [{"name": item_name, "data": avg_prices}],
    }, ensure_ascii=False)

    return f"{item_name} {period} 가격 추이 차트입니다.\n\n[CHART_DATA]{chart_data}[/CHART_DATA]"
```

- [ ] **Step 2: 도구 단독 테스트**

실행: `cd agent && uv run python -c "from app.agents.tools import create_price_chart; print(create_price_chart.invoke({'item_name': '계란', 'period': '1개월'}))"`
예상: 차트 요약 텍스트 + Highcharts JSON 출력

- [ ] **Step 3: 커밋**

```bash
git add agent/app/agents/tools.py
git commit -m "feat: create_price_chart 도구 구현"
```

---

## Chunk 4: 에이전트 조립

### Task 8: 시스템 프롬프트 수정

**Files:**
- Modify: `agent/app/agents/prompts.py`

- [ ] **Step 1: 자취고수 페르소나 프롬프트 작성**

`agent/app/agents/prompts.py` 전체를 교체:

```python
system_prompt = """너는 "자취고수"야. 자취 경험 10년차 선배로, 후배 자취생에게 장보기 꿀팁을 알려주는 역할이야.

# 성격:
- 반말 사용, 친근하고 편한 톤
- 실용적인 조언 위주
- 가끔 ㅋㅋ, ㅠㅠ 같은 이모티콘 사용
- 돈 아끼는 걸 중요하게 생각함

# 역할:
- 생필품 가격 정보를 조회해서 알려줌
- 저렴한 품목 기반으로 요리나 장보기 추천
- 가격 비교가 필요하면 테이블로 보여줌
- 가격 추이가 궁금하면 차트로 보여줌

# 행동 규칙:
- 가격 정보가 필요하면 반드시 도구(search_price, compare_prices, create_price_chart)를 사용해서 실제 데이터를 확인해
- 추측으로 가격을 말하지 마
- 저녁이나 요리 추천 요청이 오면, 먼저 여러 품목 가격을 조회해서 요즘 싼 재료를 파악한 뒤 추천해
- 가격 비교 요청이 오면 compare_prices 도구를 사용해
- 가격 추이/그래프 요청이 오면 create_price_chart 도구를 사용해

# 말투 예시:
- "야 계란 지금 30개에 5,980원이야. 하나로마트 가면 좀 더 싸더라"
- "요즘 양파가 개싸졌어ㅋㅋ 계란볶음밥 해먹어. 재료비 3천원이면 2끼 해결"
- "우유 지난주보다 200원 올랐어ㅠ 1+1 행사하는 데 노려봐"
"""
```

- [ ] **Step 2: 커밋**

```bash
git add agent/app/agents/prompts.py
git commit -m "feat: 자취고수 페르소나 시스템 프롬프트 작성"
```

### Task 9: _create_agent() 실제 에이전트 연결

**Files:**
- Modify: `agent/app/services/agent_service.py:20-26`

- [ ] **Step 1: _create_agent() 수정**

`agent/app/services/agent_service.py`의 `_create_agent` 메서드를 교체:

```python
def _create_agent(self, thread_id: uuid.UUID = None):
    """LangChain 에이전트 생성"""
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
    from langgraph.checkpoint.memory import InMemorySaver
    from app.core.config import settings
    from app.agents.prompts import system_prompt
    from app.agents.tools import search_price, compare_prices, create_price_chart

    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
    )

    tools = [search_price, compare_prices, create_price_chart]

    checkpointer = InMemorySaver()

    self.agent = create_react_agent(
        llm,
        tools,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )
```

- [ ] **Step 2: 서버 실행 테스트**

실행: `cd agent && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
예상: 서버 정상 기동, 에러 없음

- [ ] **Step 3: curl로 채팅 테스트**

실행:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "11111111-1111-1111-1111-111111111111", "message": "계란 가격 알려줘"}'
```
예상: SSE 스트리밍 응답 — step: "model" → step: "tools" → step: "done"

- [ ] **Step 4: 커밋**

```bash
git add agent/app/services/agent_service.py
git commit -m "feat: _create_agent()에 실제 LangChain 에이전트 연결"
```

### Task 10: dummy.py 정리

**Files:**
- Delete: `agent/app/agents/dummy.py`

- [ ] **Step 1: dummy.py 삭제**

실행: `rm agent/app/agents/dummy.py`

- [ ] **Step 2: 전체 서버 동작 확인**

실행: `cd agent && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
예상: dummy.py 없이도 정상 기동 (agent_service.py가 더 이상 import하지 않으므로)

- [ ] **Step 3: 커밋**

```bash
git add -A
git commit -m "refactor: dummy.py mock 에이전트 삭제"
```

---

## Chunk 5: 통합 테스트

### Task 11: 전체 시나리오 테스트

**Files:**
- 없음 (수동 테스트)

- [ ] **Step 1: 백엔드 + 프론트엔드 실행**

```bash
# 터미널 1
cd agent && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 2
cd ui && pnpm dev
```

- [ ] **Step 2: 시나리오 1 — 단순 가격 조회**

브라우저에서 http://localhost:5173 접속
입력: "계란 얼마야?"
예상: 자취고수 톤으로 가격 정보 답변

- [ ] **Step 3: 시나리오 2 — 가격 비교**

입력: "우유 가격 지난주랑 비교해줘"
예상: 텍스트 답변 + GridViewer에 테이블 표시

- [ ] **Step 4: 시나리오 3 — 저녁 추천**

입력: "오늘 저녁 뭐 해먹지?"
예상: 에이전트가 여러 품목 가격 조회 후 저렴한 재료 기반 메뉴 추천

- [ ] **Step 5: 시나리오 4 — 가격 추이**

입력: "라면 가격 추이 보여줘"
예상: 텍스트 답변 + ChartViewer에 라인 차트 표시

- [ ] **Step 6: 최종 커밋 및 푸시**

```bash
git add -A
git commit -m "feat: 생필품 가격 에이전트 구현 완료"
git push origin main
```
