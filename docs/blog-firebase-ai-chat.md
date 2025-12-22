# FastAPI 백엔드에 Firebase 인증과 Claude AI 채팅 구현하기

가족 채팅 앱 "Kid Chat"에 AI 친구 기능을 추가한 과정을 공유합니다. Firebase 인증으로 사용자를 확인하고, Claude Code CLI를 활용하여 AI 채팅 기능을 구현했습니다.

## 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [Firebase 인증 구현](#firebase-인증-구현)
3. [AI 채팅 API 설계](#ai-채팅-api-설계)
4. [Claude Code CLI 통합](#claude-code-cli-통합)
5. [E2E 테스트와 CORS 문제 해결](#e2e-테스트와-cors-문제-해결)
6. [결론](#결론)

---

## 프로젝트 개요

### 배경

"Kid Chat"은 가족 간 소통을 위한 간단한 채팅 앱입니다. 아이들이 "에이아이야"로 시작하는 메시지를 보내면 AI가 친구처럼 대답해주는 기능을 추가하고 싶었습니다.

### 기술 스택

- **Backend**: FastAPI + Python 3.12
- **Frontend**: React + Vite + TypeScript
- **Database**: PostgreSQL + SQLAlchemy
- **인증**: Firebase Authentication
- **AI**: Claude Code CLI (subprocess)

### 아키텍처

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Kid Chat  │────▶│ Backend API │────▶│ Claude CLI  │
│  (React)    │◀────│  (FastAPI)  │◀────│ (subprocess)│
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Firebase   │     │ PostgreSQL  │
│    Auth     │     │             │
└─────────────┘     └─────────────┘
```

---

## Firebase 인증 구현

### 1. Firebase Admin SDK 설정

먼저 Firebase Admin SDK를 초기화합니다. 서비스 계정 키 파일을 사용하여 인증합니다.

```python
# app/firebase.py
import firebase_admin
from firebase_admin import auth, credentials
from app.config import get_settings

settings = get_settings()
_firebase_app = None

def get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app

def verify_firebase_token(id_token: str) -> dict:
    """Firebase ID 토큰을 검증하고 사용자 정보를 반환합니다."""
    get_firebase_app()
    decoded_token = auth.verify_id_token(id_token)
    return decoded_token
```

### 2. 인증 의존성 (Dependency)

FastAPI의 Depends를 활용하여 재사용 가능한 인증 의존성을 만들었습니다.

```python
# app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.firebase import verify_firebase_token

security = HTTPBearer()

class FirebaseUser(BaseModel):
    uid: str
    email: str | None = None
    name: str | None = None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> FirebaseUser:
    """Firebase 토큰을 검증하고 현재 사용자를 반환합니다."""
    token = credentials.credentials

    try:
        decoded_token = verify_firebase_token(token)
        return FirebaseUser(
            uid=decoded_token["uid"],
            email=decoded_token.get("email"),
            name=decoded_token.get("name")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### 3. 인증 엔드포인트

토큰 검증용 엔드포인트를 제공합니다.

```python
# app/routers/auth.py
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user, FirebaseUser

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me")
async def get_me(user: FirebaseUser = Depends(get_current_user)):
    """현재 로그인한 사용자 정보를 반환합니다."""
    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name
    }
```

---

## AI 채팅 API 설계

### 요구사항

1. "에이아이야"로 시작하는 메시지에만 응답
2. 친구처럼 간결하게 대답 (100단어 이내)
3. 파일 수정 금지 (안전성)
4. 최신 정보 필요시 웹검색 활용

### Pydantic 스키마

```python
# app/schemas/ai.py
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="AI에게 보낼 메시지"
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=10,
        le=300,
        description="응답 대기 시간 (초)"
    )

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI 응답")
    elapsed_time_ms: int = Field(..., description="처리 시간 (밀리초)")
    truncated: bool = Field(default=False, description="응답 잘림 여부")
```

### API 엔드포인트

```python
# app/routers/ai.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user, FirebaseUser
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.claude_service import ClaudeService, get_claude_service

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: FirebaseUser = Depends(get_current_user),
    claude_service: ClaudeService = Depends(get_claude_service),
):
    """AI와 대화합니다. Firebase 인증이 필요합니다."""
    try:
        result = await claude_service.chat(
            prompt=request.prompt,
            timeout_seconds=request.timeout_seconds
        )
        return ChatResponse(
            response=result.output,
            elapsed_time_ms=result.elapsed_ms,
            truncated=result.truncated
        )
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="AI response timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}"
        )
```

---

## Claude Code CLI 통합

### 핵심 아이디어

Claude Code CLI를 subprocess로 호출하여 AI 응답을 생성합니다. `--dangerously-skip-permissions` 플래그로 자동 실행하고, 시스템 지시사항을 프롬프트에 추가합니다.

### 시스템 지시사항

```python
SYSTEM_INSTRUCTIONS = """
당신은 아이들의 친구입니다. 다음 규칙을 따르세요:
- 간결하게 친구처럼 대답합니다
- 파일을 절대 수정하지 않습니다
- 100단어 이내로 대답합니다
- 최신 정보가 필요하면 웹검색을 활용합니다
"""
```

### ClaudeService 구현

```python
# app/services/claude_service.py
import asyncio
import time
from dataclasses import dataclass
from app.config import get_settings

settings = get_settings()

@dataclass
class ClaudeResponse:
    output: str
    elapsed_ms: int
    truncated: bool = False

class ClaudeService:
    def __init__(self):
        self.cli_path = settings.claude_cli_path
        self.default_timeout = settings.claude_timeout_seconds
        self.max_timeout = settings.claude_max_timeout_seconds

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None
    ) -> ClaudeResponse:
        timeout = min(
            timeout_seconds or self.default_timeout,
            self.max_timeout
        )

        full_prompt = f"{prompt}\n\n{SYSTEM_INSTRUCTIONS}"

        cmd = [
            self.cli_path,
            "--dangerously-skip-permissions",
            "-p",
            full_prompt
        ]

        start_time = time.time()

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Claude CLI timed out after {timeout}s")

        elapsed_ms = int((time.time() - start_time) * 1000)

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Claude CLI failed: {error_msg}")

        output = stdout.decode().strip()

        # 응답 길이 제한 (안전장치)
        MAX_LENGTH = 5000
        truncated = len(output) > MAX_LENGTH
        if truncated:
            output = output[:MAX_LENGTH] + "..."

        return ClaudeResponse(
            output=output,
            elapsed_ms=elapsed_ms,
            truncated=truncated
        )

# 의존성 주입용
def get_claude_service() -> ClaudeService:
    return ClaudeService()
```

### 설정 추가

```python
# app/config.py
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # Claude CLI
    claude_cli_path: str = "claude"
    claude_timeout_seconds: int = 120
    claude_max_timeout_seconds: int = 300
```

---

## E2E 테스트와 CORS 문제 해결

### Chrome DevTools MCP를 활용한 E2E 테스트

Claude Code의 Chrome DevTools MCP를 사용하여 실제 브라우저에서 E2E 테스트를 수행했습니다.

```yaml
# 테스트 시나리오
1. kid-chat 앱 접속 (localhost:3004)
2. Firebase 로그인 (환규/hwankyu)
3. "에이아이야 안녕하세요!" 메시지 전송
4. AI 응답 확인
```

### 첫 번째 문제: Connection Refused

**증상:**
```
POST http://localhost:18000/ai/chat [failed - net::ERR_CONNECTION_REFUSED]
```

**원인:** 프론트엔드의 `.env.local`에 잘못된 포트가 설정되어 있었습니다.

**해결:**
```bash
# kid-chat/.env.local
VITE_AI_SERVER_URL=http://localhost:8001  # 18000 → 8001
```

### 두 번째 문제: CORS Preflight 400 Error

**증상:**
```
Access to fetch at 'http://localhost:8001/ai/chat' from origin
'http://localhost:3004' has been blocked by CORS policy
```

**원인:** `.env` 파일의 `CORS_ORIGINS`가 `config.py`의 기본값을 오버라이드하고 있었고, 포트 3004가 포함되어 있지 않았습니다.

**분석 과정:**
```python
# config.py 기본값 (OK)
cors_origins: list[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",  # 추가됨
    ...
]

# .env 파일 (문제!)
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001",...]
# → config.py 기본값을 오버라이드하여 3004 포트가 빠짐
```

**해결:**
```bash
# backend-api/.env
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","http://localhost:3002","http://localhost:3003","http://localhost:3004","https://blog.funq.kr","https://chat.funq.kr"]
```

### 교훈: pydantic-settings의 환경 변수 우선순위

pydantic-settings는 환경 변수 > .env 파일 > 기본값 순서로 설정을 읽습니다. `.env` 파일에 값이 있으면 코드의 기본값이 무시되므로, 두 곳의 설정을 동기화해야 합니다.

```python
class Settings(BaseSettings):
    # 이 기본값은 .env 파일에 CORS_ORIGINS가 있으면 무시됨!
    cors_origins: list[str] = ["http://localhost:3000", ...]

    model_config = SettingsConfigDict(env_file=".env")
```

---

## 결론

### 완성된 기능

1. **Firebase 인증**: JWT 토큰 기반 사용자 인증
2. **AI 채팅 API**: Claude Code CLI를 활용한 AI 응답 생성
3. **보안**: 인증 필수, 프롬프트 길이 제한, 타임아웃 설정

### 프로젝트 구조

```
backend-api/
├── app/
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   ├── config.py            # 설정 (pydantic-settings)
│   ├── firebase.py          # Firebase Admin SDK 초기화
│   ├── dependencies.py      # 인증 의존성
│   ├── routers/
│   │   ├── auth.py          # /auth 엔드포인트
│   │   └── ai.py            # /ai 엔드포인트
│   ├── schemas/
│   │   └── ai.py            # Pydantic 스키마
│   └── services/
│       └── claude_service.py # Claude CLI 서비스
├── tests/
│   ├── test_auth.py         # 인증 테스트
│   └── test_ai.py           # AI 채팅 테스트
└── requirements.txt
```

### API 사용 예시

```bash
# 1. Firebase에서 ID 토큰 획득 (프론트엔드에서)
TOKEN=$(firebase auth token)

# 2. AI 채팅 요청
curl -X POST http://localhost:8001/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "에이아이야 오늘 날씨 어때?"}'

# 응답
{
  "response": "안녕! 오늘 서울은 맑고 영하 2도야. 따뜻하게 입고 나가~",
  "elapsed_time_ms": 3500,
  "truncated": false
}
```

### 향후 개선 사항

1. **응답 스트리밍**: 긴 응답을 실시간으로 전송
2. **대화 컨텍스트**: 이전 대화 기억하기
3. **Rate Limiting**: 사용량 제한
4. **캐싱**: 동일 질문에 대한 응답 캐싱

---

*이 글은 Claude Code와 함께 작성되었습니다.*
