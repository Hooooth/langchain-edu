# LangChain Agent 템플릿 - 아키텍처 문서

## 1. 프로젝트 개요

교육용 LangChain 에이전트 템플릿 프로젝트입니다. FastAPI 백엔드와 React 프론트엔드로 구성되며, 학생들이 기본 구조를 이해한 후 실제 LangChain 에이전트로 교체하여 학습할 수 있도록 설계되었습니다.

**목적**: LangChain + LangGraph 기반의 멀티턴 에이전트 아키텍처 학습

**버전**: 0.1.0

---

## 2. 전체 시스템 구조

```
┌─────────────────────────────────────────────────────┐
│           React + Vite (Frontend)                   │
│  InitPage (/) → ChatPage (/chat)                    │
│  - State: Jotai atoms (sessionStorage 기반)         │
│  - Services: SSE 스트리밍, Axios                    │
└─────────────────────────────────────────────────────┘
                        ↕
                   HTTP/SSE
                        ↕
┌─────────────────────────────────────────────────────┐
│       FastAPI Backend (Uvicorn 8000)                │
│  /api/v1/chat (POST) → SSE 스트리밍                │
│  /api/v1/threads (GET) → JSON 파일 읽기            │
└─────────────────────────────────────────────────────┘
                        ↕
                  LangChain/LangGraph
                        ↕
┌─────────────────────────────────────────────────────┐
│      LLM (OpenAI) + Agent + Tools                   │
└─────────────────────────────────────────────────────┘
```

---

## 3. 백엔드 아키텍처

### 3.1 계층 구조: Routes → Services → Agents

```
HTTP Request
     ↓
Routes (API 진입점)
     ↓
Services (비즈니스 로직)
     ↓
Agents (LangChain/LangGraph)
     ↓
LLM + Tools
```

### 3.2 Routes 계층 (`app/api/routes/`)

#### **chat.py** - 채팅 엔드포인트
- **POST `/api/v1/chat`**: 사용자 메시지 처리 및 SSE 스트리밍 응답
  - Request: `ChatRequest(thread_id: UUID, message: str)`
  - Response: `StreamingResponse` (text/event-stream)
  - 각 이벤트는 JSON 형식: `{"step": "...", "content": "...", ...}`

#### **threads.py** - 대화 이력 조회
- **GET `/api/v1/threads`**: 최근 대화 목록
- **GET `/api/v1/threads/{thread_id}`**: 특정 대화 세션 상세 조회
- **GET `/api/v1/favorites/questions`**: 즐겨찾기 질문 목록
- 모두 JSON 파일에서 데이터 읽기

### 3.3 Services 계층 (`app/services/`)

#### **agent_service.py** - 에이전트 실행 및 스트리밍
```python
AgentService:
  - _create_agent(thread_id)         # 에이전트 생성
  - process_query(user_messages, thread_id)  # 비동기 제너레이터
    ├─ 에이전트의 astream() 호출
    ├─ 청크 파싱 및 변환
    └─ SSE 형식으로 yield
```

**핵심 기능**:
- LangGraph 에이전트의 `astream()` 호출
- `asyncio.wait(FIRST_COMPLETED)`로 agent_task와 progress_queue 병렬 처리
- 각 청크를 JSON으로 변환하여 스트리밍

**주요 이벤트 타입**:
- `step: "model"` - 에이전트가 도구 호출 계획 중
- `step: "tools"` - 도구 실행 중
- `step: "done"` - 최종 응답 완료

#### **conversation_service.py** - 메모리 기반 대화 관리
```python
ConversationService:
  - create_conversation(id, title, initial_message)
  - add_message(conversation_id, message)
  - get_conversations(limit, offset)
  - get_conversation(conversation_id, include_data)
```

**특징**:
- 메모리 기반 저장소 (향후 DB로 확장 가능)
- LangChainMessage 포맷 사용
- 메타데이터(chart, data) 필터링 지원

#### **threads_service.py** - JSON 파일 읽기
```python
get_threads_json()              # 스레드 목록
get_thread_by_id_json(thread_id) # 스레드 상세
get_favorite_questions_json()    # 즐겨찾기 질문
```

- `data/threads/` 디렉토리의 JSON 파일 읽기
- 동기 함수를 async로 래핑

### 3.4 Agents 계층 (`app/agents/`)

#### **dummy.py** - 교육용 목 에이전트
```python
class Agent:
  async def astream(input_data, config, stream_mode):
    # agent_service.py가 기대하는 형태로 에코 응답 반환
    # ChatResponse 도구 호출 에뮬레이션
```

**⚠️ IMP(Important)**: 학생들이 LangGraph 기반의 실제 에이전트로 교체해야 하는 부분입니다.

**교체 예상 코드**:
```python
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

class Agent:
  def __init__(self):
    self.graph = self._build_graph()

  def _build_graph(self):
    # StateGraph 정의
    # 노드: model, tools, ...
    # 엣지 정의
    return graph.compile(checkpointer=...)

  async def astream(self, input_data, config, stream_mode):
    return self.graph.astream(input_data, config, stream_mode)
```

#### **prompts.py** - 시스템 프롬프트
- 에이전트의 동작을 정의하는 프롬프트 텍스트
- 필요시 여러 프롬프트 템플릿 정의

### 3.5 Models 계층 (`app/models/`)

#### **chat.py**
```python
ChatRequest(thread_id: UUID, message: str)
ChatResponse(message_id: str, content: str, metadata: dict)
ResponseMetadata()  # 향후 확장용
```

#### **threads.py**
```python
ThreadDataResponse        # 스레드 상세 응답
RootBaseModel[T]         # 제네릭 래퍼
# ... 기타 데이터 모델
```

**주요 타입**:
- `LangChainMessage` - 역할별 메시지 (user/assistant)
- `GridData` - 표 형식 데이터
- `ChartDefinition` - 차트 설정

### 3.6 Core 설정 (`app/core/`)

#### **config.py** - Pydantic Settings
```python
class Settings(BaseSettings):
  API_V1_PREFIX: str           # API 접두사 (예: /api/v1)
  CORS_ORIGINS: List[str]      # CORS 허용 도메인
  OPENAI_API_KEY: str          # LLM API 키
  OPENAI_MODEL: str            # 모델명 (예: gpt-4)
  DEEPAGENT_RECURSION_LIMIT: int  # 재귀 호출 제한
```

`.env` 파일에서 자동 로드

### 3.7 Utils 계층 (`app/utils/`)

#### **logger.py** - 로깅 데코레이터
```python
@log_execution  # 모든 함수 타입 지원
async def process_query(...)
```

**지원 함수 타입**:
- 비동기 제너레이터 (async generator)
- 비동기 함수 (async function)
- 동기 제너레이터 (sync generator)
- 동기 함수 (sync function)

**로그 포맷**:
```
▶️ 시작: function_name
✅ 종료: function_name (실행 시간: X.XXX초)
❌ 오류: function_name - error message
```

#### **read_json.py** - JSON 파일 읽기 유틸
- `data/` 디렉토리 JSON 파일 파싱

---

## 4. 프론트엔드 아키텍처

### 4.1 페이지 구조 (`src/pages/`)

#### **InitPage** (`/`)
- 첫 방문 화면
- 프롬프트 제시 및 채팅 시작

#### **ChatPage** (`/chat`)
- 메시지 표시 및 입력
- SSE 스트리밍 응답 실시간 표시
- 메타데이터 렌더링 (차트, 표)

### 4.2 상태 관리 (`src/store/`)

**Jotai atoms** (sessionStorage 기반 영속성):

| Atom | 타입 | 용도 |
|------|------|------|
| `questionAtom` | `IMessage[]` | 사용자 질문 목록 |
| `answerAtom` | `IMessage[]` | 에이전트 응답 목록 |
| `messageAtom` | `string` | 현재 입력 텍스트 |
| `threadById` | `string` | 현재 스레드 ID |
| `promptAtom` | `string[]` | 제안 프롬프트 목록 |
| `isPromptModalAtom` | `boolean` | 프롬프트 모달 상태 |

**Persistence**: `atomWithSessionStorage` 유틸로 자동 동기화

### 4.3 Custom Hooks (`src/hooks/`)

#### **useChat**
```typescript
const {
  // State
  answers,           // 에이전트 응답
  question,          // 사용자 질문
  message,           // 입력 텍스트
  isTyping,          // 처리 중 여부

  // Handlers
  handleSendMessage(inputValue),     // 메시지 전송
  handleChunk(step, content, metadata, toolCalls, name),
  handleMsgChange(event),

  // Utils
  scrollToBottom()
} = useChat();
```

**주요 기능**:
- SSE 스트리밍 청크 처리
- 중복 방지 (`isTyping` 체크)
- 자동 라우팅 (`/chat`으로 이동)

#### **useHistory**
- 대화 이력 조회 (threads, favorites)

### 4.4 Services 계층 (`src/services/`)

#### **chatService.ts** - 채팅 API
```typescript
ChatService = () => ({
  sendMessage(threadId, message, onChunk),
  getFavoriteList(),
  getThreads(),
  getThreadById({ threadId })
})
```

#### **common.ts** - HTTP & SSE
```typescript
const api = {
  get(url, config),
  post(url, data, config),
  stream(url, data, onChunk)  // SSE 스트리밍
}
```

**스트리밍 구현**:
- `@microsoft/fetch-event-source` 라이브러리
- `AbortController` 지원
- JSON 파싱 및 `snake_case` → `camelCase` 변환

### 4.5 Components (`src/components/`)

#### **Layout**
```
Layout
├─ Sidebar
├─ Menu (네비게이션)
│  └─ SubMenu (중첩 메뉴)
└─ Outlet (페이지 렌더링)
```

#### **MessageInput**
- 텍스트 입력 (Shift+Enter 줄바꿈 지원)
- Enter로 전송

#### **CodeEditor**
- CodeMirror 기반
- 구문 강조

#### **GridViewer**
- Highcharts Grid로 표 렌더링
- `GridData` 메타데이터 처리

#### **ChartViewer**
- Highcharts로 차트 렌더링
- `ChartDefinition` 메타데이터 처리

#### **MyPromptModal**
- 프롬프트 저장/불러오기

### 4.6 라우팅 (`src/routes/`)

#### **route.config.tsx**
```
Layout (/)
├─ InitPage (/)
├─ ChatPage (/chat)
├─ Dashboard (/dashboard)  [예정]
└─ Setting (/setting)      [예정]
```

**라우터**: React Router v7 (중첩 라우트 지원)

---

## 5. 핵심 데이터 흐름

### 5.1 채팅 요청 → 스트리밍 응답

```
┌─────────────────────────────────────────────────────────┐
│  프론트엔드: MessageInput                               │
│  1. 사용자 입력: "안녕하세요"                           │
│  2. handleSendMessage() 호출                            │
│  3. isTyping = true, 에이전트 응답 UI 생성             │
└─────────────────────────────────────────────────────────┘
                        ↓
        chatService.sendMessage(threadId, message)
                        ↓
┌─────────────────────────────────────────────────────────┐
│  백엔드: POST /api/v1/chat                              │
│  1. ChatRequest 파싱                                    │
│  2. AgentService.process_query() 호출                   │
│  3. 각 청크를 SSE로 스트리밍                           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  LangGraph Agent                                         │
│  1. _create_agent() → Agent 인스턴스 생성               │
│  2. agent.astream() → 비동기 스트림 반환               │
│  3. asyncio.wait()로 청크 수집                         │
│  4. 각 청크:                                            │
│     - step=model: 도구 호출 (tool_calls)               │
│     - step=tools: 도구 실행 (tool output)              │
│     - step=done: 최종 응답 (ChatResponse)              │
└─────────────────────────────────────────────────────────┘
                        ↓
        yield JSON: {"step": "model", "tool_calls": [...]}
        yield JSON: {"step": "tools", "name": "..."}
        yield JSON: {"step": "done", "content": "..."}
                        ↓
┌─────────────────────────────────────────────────────────┐
│  프론트엔드: fetchEventSource onmessage                 │
│  1. 이벤트 파싱: JSON.parse(event.data)                │
│  2. handleChunk() 호출                                  │
│  3. UI 업데이트:                                        │
│     - step=model/tools: "도구명 처리 중..."            │
│     - step=done: 최종 답변 표시                        │
│  4. isTyping = false                                    │
└─────────────────────────────────────────────────────────┘
```

### 5.2 SSE 이벤트 형식

**Planning 단계**:
```json
{"step": "model", "tool_calls": ["SearchTool", "CalculateTool"]}
```

**Tool 실행 단계**:
```json
{"step": "tools", "name": "SearchTool", "content": "검색 결과..."}
```

**응답 완료 단계**:
```json
{
  "step": "done",
  "message_id": "uuid",
  "role": "assistant",
  "content": "최종 답변",
  "metadata": {
    "chart": {...},
    "data": {...}
  },
  "created_at": "2026-03-09T..."
}
```

### 5.3 메타데이터 렌더링

`metadata` 객체에 포함된 구조화된 데이터:

```python
metadata = {
    "chart": ChartDefinition {
        type: "line" | "bar" | "pie" | ...,
        title: "차트 제목",
        series: [...],
        xAxis: {...},
        ...
    },
    "data": GridData {
        columns: ["col1", "col2", ...],
        rows: [[...], [...], ...],
        ...
    }
}
```

UI에서는 `ChartViewer`와 `GridViewer`로 렌더링

---

## 6. 파일 구조 요약

### 백엔드
```
agent/
├── app/
│   ├── main.py                          # FastAPI 앱 진입점
│   ├── api/
│   │   └── routes/
│   │       ├── chat.py                  # POST /api/v1/chat
│   │       └── threads.py               # GET /api/v1/threads*
│   ├── services/
│   │   ├── agent_service.py             # 에이전트 실행 & 스트리밍
│   │   ├── conversation_service.py      # 메모리 기반 대화 관리
│   │   └── threads_service.py           # JSON 파일 읽기
│   ├── agents/
│   │   ├── dummy.py                     # 목 에이전트 (교체 대상)
│   │   └── prompts.py                   # 시스템 프롬프트
│   ├── models/
│   │   ├── chat.py                      # ChatRequest, ChatResponse
│   │   └── threads.py                   # 스레드 관련 모델
│   ├── core/
│   │   └── config.py                    # 환경변수 설정
│   └── utils/
│       ├── logger.py                    # @log_execution 데코레이터
│       └── read_json.py                 # JSON 파일 읽기
├── tests/
│   ├── conftest.py
│   ├── test_main.py
│   └── test_v8_scenarios.py
└── .env                                 # 환경변수 (gitignore)
```

### 프론트엔드
```
ui/
├── src/
│   ├── main.tsx                         # 앱 진입점
│   ├── App.tsx                          # 라우트 설정
│   ├── pages/
│   │   ├── InitPage.tsx                 # 첫 화면
│   │   └── ChatPage.tsx                 # 채팅 화면
│   ├── components/
│   │   ├── Layout/                      # 레이아웃 (Sidebar + Menu)
│   │   ├── MessageInput/                # 메시지 입력
│   │   ├── CodeEditor/                  # CodeMirror 에디터
│   │   ├── GridViewer/                  # 표 렌더링
│   │   ├── ChartViewer/                 # 차트 렌더링
│   │   └── MyPromptModal/               # 프롬프트 모달
│   ├── hooks/
│   │   ├── useChat.ts                   # 채팅 로직
│   │   └── useHistory.ts                # 이력 조회
│   ├── services/
│   │   ├── chatService.ts               # 채팅 API
│   │   ├── common.ts                    # HTTP & SSE 클라이언트
│   │   └── index.ts                     # Axios 인스턴스
│   ├── store/
│   │   ├── question.ts                  # questionAtom
│   │   ├── answer.ts                    # answerAtom
│   │   ├── message.ts                   # messageAtom + threadById
│   │   ├── prompts.ts                   # promptAtom
│   │   └── utils/                       # atomWithSessionStorage
│   ├── routes/
│   │   ├── route.config.tsx             # 라우트 설정
│   │   └── AppRouter.tsx                # React Router 래퍼
│   ├── types/
│   │   ├── chatVM.ts                    # 메시지, 응답 타입
│   │   └── graphVM.ts                   # 차트, 표 타입
│   └── utils/
│       └── utils.ts                     # 헬퍼 함수
└── .env.local                           # 환경변수 (gitignore)
```

---

## 7. 배포 및 설정

### 백엔드 시작
```bash
cd agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# .env 파일 작성 (OPENAI_API_KEY 등)
python app/main.py  # 또는 uvicorn app.main:app --reload
```

### 프론트엔드 시작
```bash
cd ui
pnpm install
# .env.local 파일 작성 (VITE_API_BASE_URL 등)
pnpm dev
```

### 환경변수

**agent/.env**:
```
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:5173"]
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
DEEPAGENT_RECURSION_LIMIT=20
```

**ui/.env.local**:
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## 8. 확장 및 학습 포인트

### 8.1 에이전트 교체 (IMP Priority 1)

**현재**: `dummy.py`의 Echo 에이전트
**목표**: LangGraph 기반 실제 에이전트

```python
# agents/real_agent.py
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from app.agents.prompts import SYSTEM_PROMPT

class Agent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        # 1. State 정의
        class State(TypedDict):
            messages: list
            # ...

        # 2. 노드 정의 (model, tools, ...)
        # 3. 엣지 정의
        # 4. compile() 및 checkpointer 연동
        return graph.compile(checkpointer=...)

    async def astream(self, input_data, config, stream_mode):
        return self.graph.astream(input_data, config, stream_mode)
```

### 8.2 도구(Tools) 추가

```python
# agents/tools.py
from langchain.tools import tool

@tool
def search_web(query: str) -> str:
    """인터넷 검색 도구"""
    # 구현
    pass

@tool
def calculate(expression: str) -> float:
    """계산 도구"""
    # 구현
    pass

TOOLS = [search_web, calculate]
```

에이전트의 `graph` 구성 시 tools 바인딩:
```python
self.llm_with_tools = self.llm.bind_tools(TOOLS)
```

### 8.3 메타데이터 정의 (차트/표)

응답 시 메타데이터 포함:
```python
{
    "message_id": "...",
    "content": "분석 결과입니다.",
    "metadata": {
        "chart": {
            "type": "bar",
            "title": "월별 매출",
            "series": [{"name": "2024", "data": [100, 200, ...]}],
            "xAxis": {"categories": ["1월", "2월", ...]}
        },
        "data": {
            "columns": ["날짜", "매출"],
            "rows": [["2024-01", 100], ["2024-02", 200], ...]
        }
    }
}
```

### 8.4 대화 이력 DB 저장

**현재**: 메모리 + JSON 파일 읽기
**확장**: ConversationService에 DB 백엔드 추가

```python
class DatabaseConversationService(ConversationService):
    def __init__(self):
        self.db = AsyncPgSQL(...)

    async def save_message(self, conversation_id, message):
        await self.db.execute(
            "INSERT INTO messages ..."
        )
```

### 8.5 프롬프트 최적화

`agents/prompts.py`에서 시스템 프롬프트 관리:
```python
SYSTEM_PROMPT = """
너는 전문적인 분석 에이전트입니다.
역할:
1. 사용자 질문 분석
2. 필요한 도구 선택 및 실행
3. 결과를 구조화된 형식으로 제시

Response Format:
- 최종 답변은 메타데이터와 함께 제시
- 차트나 표가 필요하면 metadata에 포함
"""
```

---

## 9. 문제 해결

### "LangChain/LangGraph 모듈 임포트 오류"
```bash
pip install langchain langchain-openai langgraph
```

### "OPENAI_API_KEY 오류"
- `.env` 파일에서 키 확인
- `config.py`에서 로드 확인: `settings.OPENAI_API_KEY`

### "SSE 스트리밍이 작동하지 않음"
- 프론트엔드: `fetchEventSource` 설정 확인
- 백엔드: `event_generator()` 함수가 올바르게 yield 중인지 확인
- 브라우저 DevTools → Network → WS 탭에서 스트림 확인

### "상태 초기화 문제"
- `sessionStorage` 캐시 확인: F12 → Application → Session Storage
- Jotai atom 초기값 확인

---

## 10. 참고 자료

- **LangChain Docs**: https://python.langchain.com
- **LangGraph**: https://langchain-ai.github.io/langgraph
- **FastAPI**: https://fastapi.tiangolo.com
- **React Router v7**: https://reactrouter.com
- **Jotai**: https://jotai.org

---

**마지막 업데이트**: 2026-03-09
