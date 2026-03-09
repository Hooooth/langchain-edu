# SSE 스트리밍 프로토콜

## 개요

백엔드와 프론트엔드 간 실시간 데이터 통신을 위해 SSE(Server-Sent Events) 스트리밍 프로토콜을 사용합니다.
이를 통해 모델의 사고 과정, 도구 실행 결과, 최종 응답을 단계별로 수신할 수 있습니다.

### 기본 정보

- **엔드포인트**: `POST /api/v1/chat`
- **응답 타입**: `Content-Type: text/event-stream`
- **데이터 형식**: `data: {JSON}\n\n`

---

## 요청 형식

클라이언트가 채팅 엔드포인트로 전송하는 요청:

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "지난 3개월 매출 현황을 분석해줘"
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `thread_id` | string | 대화 세션의 고유 UUID |
| `message` | string | 사용자 질문 |

---

## 스트리밍 응답 단계

서버는 처리 과정을 `step` 필드를 통해 알립니다. 각 단계에서 전송되는 이벤트를 수신하면서 UI를 동적으로 업데이트합니다.

### 1단계: Model (모델 추론)

모델이 사용자 메시지를 분석하여 도구 호출을 결정하는 단계입니다.

**응답 예시**:

```json
{
  "step": "model",
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "analyze_data",
        "arguments": "{\"metrics\": [\"revenue\", \"profit\"]}"
      }
    }
  ]
}
```

**필드 설명**

| 필드 | 설명 |
|------|------|
| `step` | 항상 "model" |
| `tool_calls` | 호출할 도구 배열 |
| `tool_calls[].id` | 도구 호출 고유 ID |
| `tool_calls[].function.name` | 도구 함수명 |
| `tool_calls[].function.arguments` | 도구에 전달할 JSON 문자열 |

### 2단계: Tools (도구 실행)

각 도구가 순차적으로 실행되고, 결과가 스트리밍됩니다.

**응답 예시**:

```json
{
  "step": "tools",
  "name": "fetch_data",
  "content": "{\"rows\": 45, \"columns\": [\"date\", \"revenue\", \"profit\"]}"
}
```

또는 에러 발생 시:

```json
{
  "step": "tools",
  "name": "fetch_data",
  "content": "Database connection timeout"
}
```

**필드 설명**

| 필드 | 설명 |
|------|------|
| `step` | 항상 "tools" |
| `name` | 실행된 도구명 |
| `content` | 도구 실행 결과 (성공/실패 메시지) |

### 3단계: Done (최종 응답)

모든 처리가 완료되고 최종 응답을 전송하는 단계입니다.

**응답 예시**:

```json
{
  "step": "done",
  "message_id": "msg_xyz789",
  "role": "assistant",
  "content": "지난 3개월 매출이 20% 증가했습니다. 상세 분석 결과는 아래 차트를 참고하세요.",
  "metadata": {
    "code_snippet": "SELECT date, revenue, profit FROM sales WHERE date >= DATE_SUB(NOW(), INTERVAL 3 MONTH)",
    "data": {
      "dataTable": {
        "columns": {
          "date": { "type": "string" },
          "revenue": { "type": "number" },
          "profit": { "type": "number" }
        },
        "rows": [
          { "date": "2026-01-01", "revenue": 50000, "profit": 12000 },
          { "date": "2026-02-01", "revenue": 55000, "profit": 13200 },
          { "date": "2026-03-01", "revenue": 60000, "profit": 15000 }
        ]
      }
    },
    "chart": {
      "chart": { "type": "column" },
      "title": { "text": "월별 매출 추이" },
      "xAxis": { "categories": ["1월", "2월", "3월"] },
      "series": [
        {
          "name": "매출",
          "data": [50000, 55000, 60000]
        },
        {
          "name": "순이익",
          "data": [12000, 13200, 15000]
        }
      ]
    }
  },
  "created_at": "2026-03-09T15:30:45Z"
}
```

**필드 설명**

| 필드 | 설명 |
|------|------|
| `step` | 항상 "done" |
| `message_id` | 메시지 고유 ID |
| `role` | 역할 ("assistant") |
| `content` | 최종 응답 텍스트 |
| `metadata` | 렌더링 데이터 (선택사항) |
| `created_at` | ISO 8601 타임스탬프 |

---

## Metadata 구조

`metadata` 필드는 프론트엔드에서 특정 컴포넌트로 렌더링할 데이터를 담습니다.

### code_snippet

SQL 쿼리 등의 코드를 CodeEditor 컴포넌트로 렌더링합니다.

```json
{
  "metadata": {
    "code_snippet": "SELECT * FROM users WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 MONTH)"
  }
}
```

### data (GridViewer)

테이블 형식의 데이터를 GridViewer 컴포넌트로 렌더링합니다.

```json
{
  "metadata": {
    "data": {
      "dataTable": {
        "columns": {
          "id": { "type": "number" },
          "name": { "type": "string" },
          "email": { "type": "string" },
          "status": { "type": "string" }
        },
        "rows": [
          { "id": 1, "name": "김철수", "email": "kim@example.com", "status": "active" },
          { "id": 2, "name": "이영희", "email": "lee@example.com", "status": "active" },
          { "id": 3, "name": "박민준", "email": "park@example.com", "status": "inactive" }
        ]
      }
    }
  }
}
```

### chart (ChartViewer)

Highcharts 옵션 객체를 ChartViewer 컴포넌트로 렌더링합니다.

```json
{
  "metadata": {
    "chart": {
      "chart": {
        "type": "line"
      },
      "title": {
        "text": "월별 사용자 수"
      },
      "xAxis": {
        "categories": ["1월", "2월", "3월", "4월", "5월"]
      },
      "yAxis": {
        "title": {
          "text": "사용자 수"
        }
      },
      "series": [
        {
          "name": "신규 사용자",
          "data": [100, 150, 200, 250, 300]
        },
        {
          "name": "활성 사용자",
          "data": [800, 950, 1100, 1250, 1400]
        }
      ]
    }
  }
}
```

---

## 실제 스트리밍 시나리오

### 시나리오 1: 단순 응답 (도구 호출 없음)

사용자: "안녕하세요"

**스트림 1** (model 단계 - 도구 호출 없음):
```json
{
  "step": "model",
  "tool_calls": []
}
```

**스트림 2** (done 단계):
```json
{
  "step": "done",
  "message_id": "msg_001",
  "role": "assistant",
  "content": "안녕하세요! 무엇을 도와드릴까요?",
  "created_at": "2026-03-09T15:30:45Z"
}
```

### 시나리오 2: 복합 도구 호출

사용자: "지난달 매출을 차트로 보여줘"

**스트림 1** (model 단계):
```json
{
  "step": "model",
  "tool_calls": [
    {
      "id": "call_001",
      "type": "function",
      "function": {
        "name": "analyze_data",
        "arguments": "{\"type\": \"sales\", \"period\": \"1month\"}"
      }
    }
  ]
}
```

**스트림 2** (tools 단계 - 첫 번째 도구):
```json
{
  "step": "tools",
  "name": "analyze_data",
  "content": "{\"status\": \"success\", \"data_count\": 30}"
}
```

**스트림 3** (model 단계 - 다음 도구 결정):
```json
{
  "step": "model",
  "tool_calls": [
    {
      "id": "call_002",
      "type": "function",
      "function": {
        "name": "fetch_data",
        "arguments": "{\"query\": \"SELECT date, revenue FROM sales WHERE date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)\"}"
      }
    }
  ]
}
```

**스트림 4** (tools 단계 - 두 번째 도구):
```json
{
  "step": "tools",
  "name": "fetch_data",
  "content": "{\"rows\": 30, \"columns\": [\"date\", \"revenue\"]}"
}
```

**스트림 5** (model 단계 - 최종 도구 결정):
```json
{
  "step": "model",
  "tool_calls": [
    {
      "id": "call_003",
      "type": "function",
      "function": {
        "name": "create_chart",
        "arguments": "{\"type\": \"column\", \"title\": \"지난달 일일 매출\"}"
      }
    }
  ]
}
```

**스트림 6** (tools 단계 - 세 번째 도구):
```json
{
  "step": "tools",
  "name": "create_chart",
  "content": "{\"status\": \"success\"}"
}
```

**스트림 7** (done 단계):
```json
{
  "step": "done",
  "message_id": "msg_002",
  "role": "assistant",
  "content": "지난달 매출 데이터를 정리했습니다. 일일 매출은 꾸준히 증가 추세를 보이고 있습니다.",
  "metadata": {
    "data": {
      "dataTable": {
        "columns": {
          "date": { "type": "string" },
          "revenue": { "type": "number" }
        },
        "rows": [
          { "date": "2026-02-01", "revenue": 45000 },
          { "date": "2026-02-02", "revenue": 48000 },
          { "date": "2026-02-03", "revenue": 51000 }
        ]
      }
    },
    "chart": {
      "chart": { "type": "column" },
      "title": { "text": "지난달 일일 매출" },
      "series": [
        {
          "name": "매출",
          "data": [45000, 48000, 51000]
        }
      ]
    }
  },
  "created_at": "2026-03-09T15:35:22Z"
}
```

---

## 에러 처리

### 스트리밍 중 에러

도구 실행 중 에러가 발생하면 `step="tools"`로 에러 메시지를 전송합니다.

```json
{
  "step": "tools",
  "name": "fetch_data",
  "content": "데이터베이스 연결 시간 초과"
}
```

### 최종 에러 응답

심각한 에러가 발생했을 때는 `step="done"`으로 에러 메시지를 전송합니다.

```json
{
  "step": "done",
  "message_id": "msg_err_001",
  "role": "assistant",
  "content": "죄송합니다. 요청 처리 중 오류가 발생했습니다.",
  "metadata": {
    "error": "GraphRecursionError: Maximum recursion depth exceeded"
  },
  "created_at": "2026-03-09T15:40:00Z"
}
```

### GraphRecursionError

모델이 도구를 무한 호출하는 경우 발생합니다.

```json
{
  "step": "done",
  "role": "assistant",
  "content": "죄송합니다. 요청을 처리하는 과정에서 무한 루프가 감지되어 중단했습니다. 다른 방식으로 질문해주세요.",
  "metadata": {
    "error": "GraphRecursionError"
  }
}
```

---

## 프론트엔드 처리 방식

### fetchEventSource 사용

클라이언트는 `@microsoft/fetch-event-source` 라이브러리를 사용하여 SSE를 수신합니다.

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source';

const response = await fetchEventSource('/api/v1/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    thread_id: 'uuid',
    message: 'user message',
  }),
  onmessage(event) {
    const data = JSON.parse(event.data);
    // step별 처리 로직
  },
  onerror(err) {
    console.error('Streaming error:', err);
  },
});
```

### useChat Hook의 handleChunk 메서드

프론트엔드의 `useChat` hook은 `handleChunk` 메서드에서 `step` 필드를 확인하여 분기 처리합니다.

```typescript
const handleChunk = (chunk: StreamChunk) => {
  switch (chunk.step) {
    case 'model':
      // 도구 호출 UI 표시
      setToolCalls(chunk.toolCalls);
      break;

    case 'tools':
      // 도구 실행 결과 처리
      appendToolResult(chunk.name, chunk.content);
      break;

    case 'done':
      // 최종 응답 및 메타데이터 처리
      setCurrentMessage({
        id: chunk.messageId,
        role: chunk.role,
        content: chunk.content,
        metadata: chunk.metadata,
      });
      break;
  }
};
```

### 자동 snake_case → camelCase 변환

서버에서 전송하는 JSON의 `snake_case` 필드는 프론트엔드에서 자동으로 `camelCase`로 변환됩니다.

예시:
- `message_id` → `messageId`
- `tool_calls` → `toolCalls`
- `created_at` → `createdAt`

---

## 참고 자료

- [MDN - Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Highcharts 공식 문서](https://www.highcharts.com/docs)
