# 캘린더 AI 일정 등록 기능 구현 계획

## 개요

가족달력(calendar.funq.kr)에 AI 기반 일정 등록 기능 추가. 텍스트/이미지 입력 → AI 파싱 → **PendingEvent DB 저장** → 미리보기 → 확인 후 등록.

## 핵심 제약사항

- **AI 채팅은 stateless 일회성** - 세션/컨텍스트 유지 없음
- 미리보기 → 확인 플로우를 위해 **PendingEvent 테이블**로 임시 저장 필요

## 요구사항 요약

| 항목 | 결정 |
|------|------|
| 등록 방식 | 미리보기 → 확인 → 등록 |
| 구현 방식 | AI 채팅 + 전용 API 둘 다 |
| 이미지 입력 | Base64 |
| 페르소나 | 캘린더 전용 "달력이" (호출어: "달력아") |
| 반복 일정 | 자동 인식 지원 |
| 클라이언트 | 캘린더 앱 + 채팅 앱 모두 |
| **임시 저장** | **PendingEvent 테이블 (DB)** |

## 구현 단계

### Phase 0: PendingEvent 모델 및 마이그레이션

**파일**: `app/models/calendar.py`, `alembic/versions/xxx_add_pending_event.py`

**작업**:
- [ ] `PendingEvent` 모델 정의
- [ ] Alembic 마이그레이션 생성 및 적용
- [ ] `PendingEventService` 서비스 클래스 작성

**모델 설계**:
```python
class PendingEventStatus(str, Enum):
    PENDING = "pending"      # 대기 중
    CONFIRMED = "confirmed"  # 승인됨 → Event 생성됨
    EXPIRED = "expired"      # 만료됨
    CANCELLED = "cancelled"  # 취소됨

class PendingEvent(Base):
    __tablename__ = "pending_events"

    id = Column(UUID, primary_key=True, default=uuid4)

    # 파싱된 일정 데이터 (JSON)
    event_data = Column(JSONB, nullable=False)

    # 원본 입력
    source_text = Column(Text, nullable=True)
    source_image_hash = Column(String(64), nullable=True)  # 이미지 해시 (중복 방지)

    # 메타데이터
    created_by = Column(UUID, ForeignKey("family_members.id"), nullable=False)
    status = Column(String(20), default="pending")
    confidence = Column(Float, default=1.0)
    ai_message = Column(Text, nullable=True)  # AI 응답 메시지

    # TTL 관리
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # 기본 30분

    # 관계
    created_by_member = relationship("FamilyMember")
```

**서비스 메서드**:
```python
class PendingEventService:
    def create(self, event_data: dict, user_uid: str, expires_minutes: int = 30) -> PendingEvent
    def get_by_id(self, pending_id: UUID) -> PendingEvent | None
    def confirm(self, pending_id: UUID) -> Event  # PendingEvent → Event 변환
    def cancel(self, pending_id: UUID) -> None
    def cleanup_expired(self) -> int  # 만료된 항목 정리
    def get_pending_by_user(self, user_uid: str) -> list[PendingEvent]
```

---

### Phase 1: 캘린더 AI 페르소나 추가

**파일**: `app/services/claude/personas.py`

**작업**:
- [ ] `PersonaType.CALENDAR` enum 추가
- [ ] "달력아" 호출어 패턴 추가 (`detect_persona` 함수)
- [ ] "달력이" 페르소나 정의 추가
- [ ] 일정 파싱 특화 시스템 프롬프트 작성

**페르소나 설정**:
```python
PersonaType.CALENDAR: Persona(
    name="calendar",
    display_name="달력이",
    triggers=["달력아", "달력이"],
    system_prompt="""..."""
)
```

**시스템 프롬프트 핵심 내용**:
- 날짜/시간 파싱 규칙 (오늘, 내일, 다음주 등)
- 반복 일정 패턴 인식 (매일, 매주, 매월 등)
- JSON 형식 출력 지시
- 모호한 정보 처리 방법

---

### Phase 2: AI 채팅 스키마 확장

**파일**: `app/schemas/ai.py`

**작업**:
- [ ] `ChatRequest`에 `image_base64: Optional[str]` 필드 추가
- [ ] `ChatResponse`에 `pending_events: Optional[list]` 필드 추가
- [ ] `ChatResponse`에 `action_type: Optional[str]` 필드 추가
- [ ] `ParsedEvent` 스키마 정의 (파싱된 일정 구조)

**스키마 구조**:
```python
class ParsedEvent(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    description: Optional[str] = None
    recurrence_pattern: Optional[RecurrencePattern] = None
    confidence: float = 1.0
    source_text: Optional[str] = None

class ChatRequest(BaseModel):
    prompt: str
    timeout_seconds: Optional[int] = None
    image_base64: Optional[str] = None  # 추가

class ChatResponse(BaseModel):
    response: str
    elapsed_time_ms: int
    truncated: bool = False
    persona: Optional[str] = None
    action_type: Optional[str] = None  # 추가: "confirm_event", "info" 등
    pending_events: Optional[list[ParsedEvent]] = None  # 추가
```

---

### Phase 3: Claude 서비스 이미지 지원

**파일**: `app/services/claude/service.py`

**작업**:
- [ ] `chat()` 메서드에 `image_base64` 파라미터 추가
- [ ] 이미지를 임시 파일로 저장하는 로직 추가
- [ ] 프롬프트에 이미지 경로 포함
- [ ] 임시 파일 정리 로직 추가

**구현 방식**:
```python
async def chat(
    self,
    prompt: str,
    timeout_seconds: int | None = None,
    image_base64: str | None = None,
) -> ChatResponse:
    # 이미지가 있으면 임시 파일로 저장
    if image_base64:
        temp_path = self._save_temp_image(image_base64)
        prompt = f"{prompt} {temp_path}"

    # Claude CLI 호출
    ...

    # 임시 파일 정리
    if temp_path:
        os.unlink(temp_path)
```

---

### Phase 4: 전용 Calendar AI API

**파일**: `app/routers/calendar/ai.py` (신규)

**작업**:
- [ ] `POST /calendar/ai/parse` - 텍스트/이미지 파싱 → PendingEvent 생성
- [ ] `POST /calendar/ai/confirm/{pending_id}` - PendingEvent → Event 확정
- [ ] `DELETE /calendar/ai/pending/{pending_id}` - PendingEvent 취소
- [ ] `GET /calendar/ai/pending` - 내 대기 중인 일정 목록
- [ ] 스키마 정의 (`app/schemas/calendar_ai.py`)

**API 설계**:

#### `POST /calendar/ai/parse`
```python
class AIParseRequest(BaseModel):
    text: Optional[str] = None
    image_base64: Optional[str] = None

class AIParseResponse(BaseModel):
    pending_id: UUID  # 확인용 ID
    parsed_events: list[ParsedEvent]
    ai_message: str  # AI 응답 메시지
    expires_at: datetime  # 만료 시간
    confidence: float
```

#### `POST /calendar/ai/confirm/{pending_id}`
```python
class AIConfirmRequest(BaseModel):
    # 선택적 수정 (미리보기에서 사용자가 수정한 경우)
    modifications: Optional[list[EventCreate]] = None

class AIConfirmResponse(BaseModel):
    created_events: list[EventResponse]
    count: int
```

#### `GET /calendar/ai/pending`
```python
class PendingEventResponse(BaseModel):
    id: UUID
    event_data: dict
    ai_message: str
    created_at: datetime
    expires_at: datetime
    status: str

class PendingListResponse(BaseModel):
    pending_events: list[PendingEventResponse]
```

#### `DELETE /calendar/ai/pending/{pending_id}`
- 204 No Content 반환

---

### Phase 5: AI 라우터 확장

**파일**: `app/routers/ai.py`

**작업**:
- [ ] `/ai/chat` 엔드포인트에 `image_base64` 지원 추가
- [ ] 캘린더 페르소나 응답 시 `pending_events` 파싱 추가
- [ ] `action_type` 응답 처리

---

### Phase 6: 프로토콜 업데이트

**파일**: `app/services/claude/protocol.py`

**작업**:
- [ ] `AIServiceProtocol.chat()` 시그니처에 `image_base64` 추가
- [ ] `ChatResponse`에 `pending_events` 필드 추가

---

### Phase 7: 테스트 작성

**파일들**:
- `tests/unit/services/test_calendar_persona.py` (신규)
- `tests/integration/test_calendar_ai.py` (신규)
- `tests/fakes/fake_claude.py` (수정)

**테스트 케이스**:
- [ ] 달력이 페르소나 감지 테스트
- [ ] 텍스트 → 일정 파싱 테스트
- [ ] 이미지 base64 처리 테스트
- [ ] 반복 일정 패턴 인식 테스트
- [ ] `/calendar/ai/parse` 엔드포인트 테스트
- [ ] `/calendar/ai/register` 엔드포인트 테스트
- [ ] 에러 케이스 (파싱 실패, 모호한 입력)

---

## 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `app/models/calendar.py` | 수정 | PendingEvent 모델 추가 |
| `alembic/versions/xxx_add_pending_event.py` | **신규** | 마이그레이션 |
| `app/services/calendar/pending.py` | **신규** | PendingEventService |
| `app/services/calendar/dependencies.py` | 수정 | get_pending_service 추가 |
| `app/services/claude/personas.py` | 수정 | 달력이 페르소나 추가 |
| `app/services/claude/service.py` | 수정 | 이미지 지원 추가 |
| `app/services/claude/protocol.py` | 수정 | 시그니처 업데이트 |
| `app/schemas/ai.py` | 수정 | image_base64, pending_id 추가 |
| `app/schemas/calendar_ai.py` | **신규** | AI 파싱 관련 스키마 |
| `app/routers/ai.py` | 수정 | 이미지/캘린더 응답 처리 |
| `app/routers/calendar/ai.py` | **신규** | 전용 AI 엔드포인트 |
| `app/routers/calendar/__init__.py` | 수정 | ai 라우터 포함 |
| `tests/fakes/fake_claude.py` | 수정 | 이미지 파라미터 추가 |
| `tests/fakes/fake_pending.py` | **신규** | PendingEventService Fake |
| `tests/unit/services/test_calendar_persona.py` | **신규** | 페르소나 테스트 |
| `tests/integration/test_calendar_ai.py` | **신규** | AI 엔드포인트 테스트 |

---

## 시스템 프롬프트 초안 (달력이)

```
너는 "달력이"야. 가족달력 일정 등록을 도와주는 AI 어시스턴트야.
사용자가 텍스트나 이미지로 일정 정보를 주면 파싱해서 JSON으로 응답해.

## 날짜/시간 파싱 규칙
- 오늘: {today}
- 내일: {tomorrow}
- 모레: {day_after_tomorrow}
- 다음주 월요일: 가장 가까운 다음 월요일
- 시간이 없으면 기본값 09:00-10:00 (1시간)
- 종일 일정: "하루종일", "종일" 키워드 감지

## 반복 일정 인식
- "매일" → FREQ=DAILY
- "매주 월요일" → FREQ=WEEKLY;BYDAY=MO
- "매주 월수금" → FREQ=WEEKLY;BYDAY=MO,WE,FR
- "매월 1일" → FREQ=MONTHLY
- "매년" → FREQ=YEARLY

## 응답 형식
반드시 다음 JSON 형식으로 응답해:

```json
{
  "events": [
    {
      "title": "일정 제목",
      "start_time": "2026-01-23T15:00:00",
      "end_time": "2026-01-23T16:00:00",
      "all_day": false,
      "description": null,
      "recurrence": null,
      "confidence": 0.95
    }
  ],
  "message": "사용자에게 보여줄 친근한 메시지"
}
```

## 모호한 정보 처리
- 연도 없음 → 현재 연도 또는 가장 가까운 미래
- 시간 없음 → all_day: true 또는 기본 시간
- confidence < 0.7 이면 사용자에게 확인 요청
```

---

## 구현 순서

1. **Phase 0**: PendingEvent 모델 및 마이그레이션 (DB 먼저)
2. **Phase 1**: 페르소나 추가 (의존성 없음)
3. **Phase 6**: 프로토콜 업데이트 (Phase 3 전에 필요)
4. **Phase 2**: 스키마 확장 (API 변경 전에 필요)
5. **Phase 3**: Claude 서비스 이미지 지원
6. **Phase 4**: 전용 Calendar AI API (PendingEvent 사용)
7. **Phase 5**: AI 라우터 확장
8. **Phase 7**: 테스트 작성 (각 Phase 후 점진적으로)

---

## 예상 API 사용 흐름

### 시나리오 1: 채팅 앱에서 사용

```
1. 사용자: "달력아 내일 3시 치과 등록해줘"

2. 백엔드:
   - Claude AI가 텍스트 파싱
   - PendingEvent 테이블에 저장 (expires_at = now + 30분)

3. AI 응답:
   {
     "response": "내일(1/23) 오후 3시 치과 일정이에요! 등록할까요?",
     "action_type": "confirm_event",
     "pending_id": "uuid-xxx",
     "pending_events": [{...}],
     "expires_at": "2026-01-22T22:30:00"
   }

4. 사용자: "응" 또는 UI에서 확인 버튼 클릭

5. 프론트엔드: POST /calendar/ai/confirm/{pending_id}

6. 백엔드:
   - PendingEvent 조회 (만료/취소 체크)
   - Event 테이블에 실제 일정 생성
   - PendingEvent 상태 → "confirmed"

7. 응답: 생성된 Event 정보
```

### 시나리오 2: 캘린더 앱에서 사용

```
1. 사용자: 이미지 업로드 + "일정 추출해줘"

2. 프론트엔드: POST /calendar/ai/parse
   {
     "text": "일정 추출해줘",
     "image_base64": "iVBORw0KGgo..."
   }

3. 백엔드:
   - Claude AI가 이미지 분석 + 텍스트 파싱
   - PendingEvent 테이블에 저장

4. 응답:
   {
     "pending_id": "uuid-xxx",
     "parsed_events": [{title, start_time, end_time, ...}],
     "ai_message": "학교 알림장에서 3개 일정을 찾았어요!",
     "expires_at": "2026-01-22T22:30:00"
   }

5. 사용자: 미리보기 확인 (수정 가능)

6. 프론트엔드: POST /calendar/ai/confirm/{pending_id}
   {
     "modifications": [{...}]  // 사용자가 수정한 경우 (선택)
   }

7. 완료: Event 생성됨
```

### 시나리오 3: 만료/취소

```
1. 30분 후 또는 사용자가 취소 클릭
2. DELETE /calendar/ai/pending/{pending_id}
3. PendingEvent 상태 → "cancelled" 또는 자동 "expired"
```

---

## 리스크 및 고려사항

1. **Claude CLI 응답 파싱**: JSON 추출 실패 시 fallback 처리 필요
2. **이미지 용량**: Base64 크기 제한 필요 (예: 5MB)
3. **임시 파일 관리**: 정리 실패 시 디스크 사용량 증가
4. **모호한 입력**: "다음주" 같은 상대적 날짜 처리 일관성
5. **시간대**: 서버/클라이언트 시간대 불일치 가능성
6. **PendingEvent 정리**: 만료된 레코드 주기적 정리 필요 (cron job 또는 lazy cleanup)
7. **동시성**: 같은 PendingEvent를 여러 번 confirm 시 중복 방지 필요
8. **사용자 경험**: 30분 만료 시간이 적절한지 모니터링 필요

---

## 완료 기준

- [ ] PendingEvent 모델 및 마이그레이션 완료
- [ ] "달력아" 호출 시 달력이 페르소나 활성화
- [ ] 텍스트 입력 → 일정 파싱 → PendingEvent 저장
- [ ] 이미지(Base64) 입력 → 일정 파싱
- [ ] 반복 일정 패턴 인식 (매일/매주/매월/매년)
- [ ] `/calendar/ai/parse` → PendingEvent 생성
- [ ] `/calendar/ai/confirm/{id}` → Event 생성
- [ ] `/calendar/ai/pending` → 대기 목록 조회
- [ ] 만료 시간(30분) 후 자동 만료 처리
- [ ] 미리보기 → 확인 → 등록 플로우 완성
- [ ] 기존 테스트 통과 + 신규 테스트 통과
