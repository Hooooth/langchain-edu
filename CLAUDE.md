# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 참고하는 가이드 문서입니다.

## 기본 규칙

- 모든 대화, 커밋 메시지, 코드 주석은 **한글**로 작성한다.

## 프로젝트 개요

LangChain 에이전트 교육용 템플릿 — 두 개의 독립적인 서브 프로젝트로 구성된 모노레포:

- **`agent/`** — FastAPI + LangChain v1.0 백엔드 (Python, `uv`로 관리)
- **`ui/`** — React 19 + Vite 프론트엔드 (TypeScript/JSX, `pnpm`으로 관리)

백엔드는 SSE 스트리밍 기반 채팅 API를 제공하고, 프론트엔드가 이를 소비한다.

### 교육 목적

이 프로젝트의 핵심 실습 목표는 **`agent/app/agents/dummy.py`를 실제 LangChain 에이전트로 교체**하는 것이다. `dummy.py`는 입력을 그대로 돌려주는 목(mock) 에이전트이며, 이것은 버그가 아니라 의도된 설계이다. 프론트엔드는 이미 완성되어 있으므로 백엔드 에이전트 개발에 집중한다.

## 명령어

### 백엔드 (agent/ 디렉토리에서 실행)

```bash
uv sync                          # 의존성 설치 (.venv 생성)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload  # 개발 서버
uv run pytest                    # 전체 테스트
uv run pytest tests/test_main.py # 단일 테스트 파일 실행
uv run ruff check app/           # 린트
uv run black app/                # 포맷팅
```

### 프론트엔드 (ui/ 디렉토리에서 실행)

```bash
pnpm install                     # 의존성 설치
pnpm dev                         # 개발 서버 (localhost:5173)
pnpm build                       # 프로덕션 빌드 (tsc + vite build)
```

## 아키텍처

### 백엔드

- **진입점**: `app/main.py` — FastAPI 앱, CORS, 로깅 미들웨어, `/health` 엔드포인트
- **설정**: `app/core/config.py` — Pydantic Settings, `.env`에서 로드 (OPENAI_API_KEY, OPENAI_MODEL, DEEPAGENT_RECURSION_LIMIT)
- **라우트**: `app/api/routes/` — `chat.py` (POST `/api/v1/chat`, SSE 스트리밍), `threads.py` (GET `/api/v1/threads`)
- **서비스**: `app/services/` — `agent_service.py` (LangChain 에이전트 오케스트레이션), `conversation_service.py`, `threads_service.py`
- **에이전트**: `app/agents/` — LangChain 에이전트 정의 및 프롬프트 (현재 dummy.py는 mock)
- **데이터**: `app/data/` — JSON 기반 스레드/대화 저장소 (파일 기반, DB 없음)

### 프론트엔드

- **상태 관리**: Jotai (`src/store/`)
- **데이터 페칭**: TanStack React Query (`src/services/`, `src/hooks/`)
- **라우팅**: React Router v7 (`src/routes/`)
- **스타일링**: SCSS modules + MUI + styled-components + Emotion
- **i18n**: react-i18next, 한국어/영어 번역 (`src/constants/i18n/`)
- **차트**: Highcharts (`src/components/ChartViewer/`)
- **코드 표시**: CodeMirror (`src/components/CodeEditor/`)
- **데이터 테이블**: Highcharts Grid Lite (`src/components/GridViewer/`)
- **경로 별칭**: `@` → `src/` (vite.config.ts, tsconfig.json에서 설정)
- **SVG 임포트**: `*.svg?react` 접미사로 컴포넌트 임포트 (vite-plugin-svgr)

### 채팅 스트리밍 프로토콜

POST `/api/v1/chat` 엔드포인트는 `step` 필드를 가진 JSON 객체를 스트리밍한다:
- `step: "model"` — 모델 호출, `tool_calls` 배열 포함
- `step: "tools"` — 도구 실행 결과, `name`과 `content` 포함
- `step: "done"` — 최종 응답, `content`와 `metadata` (code_snippet, data, chart) 포함

## 환경 변수

각 서브 프로젝트에 `env.sample`이 있다. `.env`로 복사 후 값을 채운다:
- **agent/.env**: `OPENAI_API_KEY`, `OPENAI_MODEL`, `DEEPAGENT_RECURSION_LIMIT`, `API_V1_PREFIX`, `CORS_ORIGINS`
- **ui/.env**: `VITE_API_BASE_URL` (기본값: `http://localhost:8000`)

## 주의사항

- Python >=3.11, <=3.13
- **Vite 프록시 동작**: `vite.config.ts`에서 `/api` 경로를 백엔드로 프록시하면서 `/api` 접두사를 **제거**한다. 예: 프론트엔드의 `/api/v1/chat` → 백엔드의 `/v1/chat`. 그런데 백엔드의 `API_V1_PREFIX`는 `/api/v1`이므로, 실제 백엔드 라우트는 `/api/v1/chat`이다. 즉 프록시가 `/api`를 제거하고 백엔드가 다시 `/api/v1`을 붙이는 구조.
- **snake_case ↔ camelCase 자동 변환**: 프론트엔드의 Axios 응답 인터셉터(`services/common.ts`)가 백엔드 응답의 snake_case 키를 camelCase로 자동 변환한다. API 연동 시 필드명 불일치에 주의.
- 에이전트 재귀 제한은 `DEEPAGENT_RECURSION_LIMIT`으로 설정 (기본값 20)
