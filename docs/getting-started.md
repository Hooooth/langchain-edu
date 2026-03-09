# 시작 가이드

LangChain 에이전트 템플릿 프로젝트를 로컬에서 실행하기 위한 단계별 설정 가이드입니다.

## 사전 요구사항

다음을 설치하세요:

- **Python 3.11~3.13**
- **Node.js 18+**
- **uv** (Python 패키지 매니저)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **pnpm**
  ```bash
  npm install -g pnpm
  ```

## 백엔드 설정 (agent/)

```bash
cd agent

# 환경 변수 설정
cp env.sample .env
# .env 파일을 열어 OPENAI_API_KEY 입력

# 가상환경 생성 및 의존성 설치
uv sync

# 개발 서버 실행
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 문서 확인: http://localhost:8000/docs

## 프론트엔드 설정 (ui/)

```bash
cd ui

# 환경 변수 설정
cp env.sample .env

# 의존성 설치
pnpm install

# 개발 서버 실행
pnpm dev
```

프론트엔드 확인: http://localhost:5173

## 환경 변수 설명

### agent/.env
- `OPENAI_API_KEY`: OpenAI API 키 (필수)
- `OPENAI_MODEL`: 기본값 `gpt-4o`
- `API_V1_PREFIX`: 기본값 `/api/v1`
- `CORS_ORIGINS`: CORS 허용 도메인
- `DEEPAGENT_RECURSION_LIMIT`: 기본값 `20`

### ui/.env
- `VITE_API_BASE_URL`: 기본값 `http://localhost:8000`

## 개발 명령어

### 백엔드
```bash
cd agent

# 테스트 실행
uv run pytest

# 린트 검사
uv run ruff check app/

# 코드 포맷팅
uv run black app/
```

### 프론트엔드
```bash
cd ui

# 프로덕션 빌드
pnpm build

# 빌드 결과 확인
pnpm preview
```

## 교육 실습 가이드

### 핵심 목표
`agent/app/agents/dummy.py`를 실제 LangChain 에이전트로 교체하기

### 현재 상태
- `dummy.py`: Echo 응답만 반환하는 목(mock) 에이전트
- 프론트엔드: 완성된 상태
- UI는 백엔드의 스트리밍 프로토콜(step: `model`/`tools`/`done`)에 따라 자동으로 코드/테이블/차트를 렌더링

### 참고 문서
- `docs/architecture.md` - 전체 시스템 구조
- `docs/streaming-protocol.md` - 프론트엔드와의 통신 프로토콜
- `agent/docs/spec.md` - 백엔드 스펙

## 트러블슈팅

**`uv: command not found`**
```bash
# uv 설치 확인
curl -LsSf https://astral.sh/uv/install.sh | sh
# 터미널 재시작 후 시도
```

**`pnpm: command not found`**
```bash
npm install -g pnpm
```

**CORS 에러**
- `agent/.env`의 `CORS_ORIGINS` 확인
- 프론트엔드 주소(`http://localhost:5173`) 포함되어 있는지 확인

**API 키 에러**
- `agent/.env`에 유효한 `OPENAI_API_KEY` 설정되어 있는지 확인
