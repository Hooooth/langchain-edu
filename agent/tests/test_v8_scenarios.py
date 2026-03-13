"""자취고수 에이전트 통합 테스트

실제 OpenSearch + OpenAI API를 사용하는 통합 테스트입니다.
실행 조건: .env에 OPENAI_API_KEY, OPENSEARCH_HOST 설정 필요

    uv run pytest tests/test_v8_scenarios.py -v -m integration
"""
import pytest
import json
import uuid
from fastapi.testclient import TestClient
from typing import List, Dict, Any


def parse_sse_events(response_text: str) -> List[Dict[str, Any]]:
    """SSE 응답에서 JSON 이벤트를 파싱합니다."""
    events = []
    for line in response_text.strip().split('\n'):
        if line.startswith('data: '):
            data_str = line[6:]
            if data_str == '[DONE]':
                break
            try:
                events.append(json.loads(data_str))
            except json.JSONDecodeError:
                pass
    return events


def get_done_event(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """이벤트 목록에서 최종 응답(step=done)을 반환합니다."""
    done_events = [e for e in events if e.get("step") == "done"]
    assert len(done_events) > 0, "최종 응답(step=done)이 없습니다"
    return done_events[-1]


def get_tool_call_names(events: List[Dict[str, Any]]) -> List[str]:
    """이벤트 목록에서 호출된 도구 이름을 추출합니다."""
    names = []
    for e in events:
        if e.get("step") == "model" and e.get("tool_calls"):
            names.extend(e["tool_calls"])
    return names


def get_tool_results(events: List[Dict[str, Any]], tool_name: str) -> List[Dict[str, Any]]:
    """이벤트 목록에서 특정 도구의 실행 결과를 반환합니다."""
    return [e for e in events if e.get("step") == "tools" and e.get("name") == tool_name]


@pytest.mark.integration
def test_case1_price_search(client: TestClient, thread_id: str):
    """
    Case 1: 단순 가격 조회
    사용자 질문: "쌀 가격 알려줘"
    기대: search_price 도구 사용, 가격 정보 포함 응답
    """
    response = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "쌀 가격 알려줘"}
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = parse_sse_events(response.text)
    tool_names = get_tool_call_names(events)
    assert "search_price" in tool_names, f"search_price 도구가 호출되어야 합니다. 실제: {tool_names}"

    done = get_done_event(events)
    assert done["role"] == "assistant"
    assert len(done["content"]) > 0


@pytest.mark.integration
def test_case2_price_comparison_table(client: TestClient, thread_id: str):
    """
    Case 2: 가격 비교 (테이블 생성)
    사용자 질문: "감자 가격 비교해줘"
    기대: compare_prices 도구 사용, metadata에 data(테이블) 포함
    """
    response = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "감자 가격 비교해줘"}
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    tool_names = get_tool_call_names(events)
    assert "compare_prices" in tool_names, f"compare_prices 도구가 호출되어야 합니다. 실제: {tool_names}"

    # 최종 응답에 감자 관련 내용 확인
    done = get_done_event(events)
    assert len(done["content"]) > 0
    assert "감자" in done["content"] or "원" in done["content"]


@pytest.mark.integration
def test_case3_price_chart(client: TestClient):
    """
    Case 3: 가격 추이 차트 생성
    사용자 질문: "고구마 가격 추이 보여줘"
    기대: create_price_chart 도구 사용, metadata에 chart 포함
    """
    thread_id = str(uuid.uuid4())

    response = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "고구마 가격 추이 보여줘"}
    )

    assert response.status_code == 200
    events = parse_sse_events(response.text)

    tool_names = get_tool_call_names(events)
    assert "create_price_chart" in tool_names, f"create_price_chart 도구가 호출되어야 합니다. 실제: {tool_names}"

    # 최종 응답에 고구마 관련 내용 확인
    done = get_done_event(events)
    assert len(done["content"]) > 0
    assert "고구마" in done["content"] or "원" in done["content"]


@pytest.mark.integration
def test_case4_multiturn_conversation(client: TestClient):
    """
    Case 4: 멀티턴 대화 (대화 연속성 확인)
    1차: "쌀 가격 알려줘"
    2차: "그거 차트로 보여줘" (같은 thread_id — "쌀"을 기억해야 함)
    기대: 2차에서 이전 대화를 기억하고 쌀 관련 차트 생성
    """
    thread_id = str(uuid.uuid4())

    # 1차 요청
    response1 = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "쌀 가격 알려줘"}
    )
    assert response1.status_code == 200
    events1 = parse_sse_events(response1.text)
    done1 = get_done_event(events1)
    assert len(done1["content"]) > 0

    # 2차 요청 — 같은 thread_id, "그거"로 대화 연속성 확인
    response2 = client.post(
        "/api/v1/chat",
        json={"thread_id": thread_id, "message": "그거 차트로 보여줘"}
    )
    assert response2.status_code == 200
    events2 = parse_sse_events(response2.text)
    done2 = get_done_event(events2)

    has_chart = "chart" in done2.get("metadata", {})
    has_rice_ref = "쌀" in done2.get("content", "")
    assert has_chart or has_rice_ref, "2차 응답에서 쌀 관련 차트 또는 언급이 있어야 합니다 (대화 연속성)"
