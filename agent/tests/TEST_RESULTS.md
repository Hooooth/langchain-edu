# 테스트 결과 (2026-03-13)

## 단위 테스트 (mock 기반) — 5 passed, 0.03s

```
tests/test_agent_service.py::test_agent_created_once              PASSED
tests/test_agent_service.py::test_checkpointer_persists           PASSED
tests/test_main.py::test_root_endpoint                            PASSED
tests/test_main.py::test_health_endpoint                          PASSED
tests/test_opensearch_client.py::test_get_opensearch_client_returns_singleton PASSED
```

## 통합 테스트 (실제 OpenSearch + OpenAI API) — 4 passed, 43s

```
tests/test_v8_scenarios.py::test_case1_price_search               PASSED   # 쌀 가격 조회 → search_price 호출
tests/test_v8_scenarios.py::test_case2_price_comparison_table     PASSED   # 감자 가격 비교 → compare_prices 호출
tests/test_v8_scenarios.py::test_case3_price_chart                PASSED   # 고구마 차트 → create_price_chart 호출
tests/test_v8_scenarios.py::test_case4_multiturn_conversation     PASSED   # 멀티턴 대화 연속성 확인
```

> 통합 테스트는 외부 API(OpenAI, OpenSearch) 의존으로 네트워크 상태에 따라 간헐적 실패 가능.
> 실행 방법: `uv run pytest tests/test_v8_scenarios.py -v -m integration`
