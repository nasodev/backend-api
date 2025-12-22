# 프로덕션 배포 트러블슈팅: Claude Code CLI + Firebase 인증

로컬에서 완벽하게 작동하던 AI 채팅 기능이 프로덕션 서버에서 실패했습니다. 이 문서는 배포 과정에서 발생한 문제들과 해결 과정을 상세히 기록합니다.

## 목차

1. [문제 개요](#문제-개요)
2. [문제 1: Firebase 인증 실패 (401)](#문제-1-firebase-인증-실패-401)
3. [문제 2: Claude CLI 미발견 (503)](#문제-2-claude-cli-미발견-503)
4. [문제 3: Claude CLI 타임아웃](#문제-3-claude-cli-타임아웃)
5. [최종 해결책](#최종-해결책)
6. [교훈](#교훈)

---

## 문제 개요

### 환경

- **서버**: Ubuntu 22.04 (systemd)
- **백엔드**: FastAPI + Uvicorn
- **인증**: Firebase Admin SDK
- **AI**: Claude Code CLI (subprocess)

### 증상

로컬 개발 환경에서는 AI 채팅이 정상 작동했지만, 프로덕션 배포 후:

```
"인증이 만료되었습니다. 다시 로그인해주세요." (401)
→ "AI 서비스를 이용할 수 없습니다." (503)
→ "Failed to fetch" (타임아웃)
```

에러 메시지가 순차적으로 변경되며 3개의 다른 문제가 있음을 발견했습니다.

---

## 문제 1: Firebase 인증 실패 (401)

### 증상

```
INFO: 192.168.0.1:0 - "POST /ai/chat HTTP/1.1" 401 Unauthorized
```

프론트엔드에서 "인증이 만료되었습니다" 에러 표시.

### 원인 분석

서버에서 Firebase 초기화 테스트:

```bash
cd ~/dev/backend-api && source venv/bin/activate
python -c "from app.firebase import get_firebase_app; app = get_firebase_app(); print('OK:', app.name)"
```

결과:

```
FileNotFoundError: Firebase credentials not found: firebase/kid-chat-2ca0f-firebase-adminsdk-fbsvc-094c9dc406.json
```

**원인**: Firebase 서비스 계정 키 파일이 서버에 없었습니다.

### 해결

로컬에서 서버로 파일 복사:

```bash
scp -r /path/to/backend-api/firebase user@server:~/dev/backend-api/
```

### 교훈

- `.gitignore`에 포함된 민감한 파일은 수동으로 서버에 복사해야 함
- 배포 체크리스트에 "인증 파일 확인" 항목 추가 필요

---

## 문제 2: Claude CLI 미발견 (503)

### 증상

Firebase 문제 해결 후 새로운 에러:

```
Claude CLI not found at: claude
INFO: 192.168.0.1:0 - "POST /ai/chat HTTP/1.1" 503 Service Unavailable
```

### 원인 분석

Claude CLI 설치 확인:

```bash
which claude && claude --version
# /home/funq/.local/bin/claude
# 2.0.75 (Claude Code)
```

CLI는 설치되어 있지만, systemd 서비스가 찾지 못함.

**원인**: systemd 서비스의 PATH에 `~/.local/bin`이 포함되지 않음.

```ini
# /etc/systemd/system/backend-api.service
Environment="PATH=/home/funq/dev/backend-api/venv/bin"
```

### 해결

`.env` 파일에 전체 경로 추가:

```bash
echo 'CLAUDE_CLI_PATH=/home/funq/.local/bin/claude' >> ~/dev/backend-api/.env
sudo systemctl restart backend-api
```

**참고**: `config.py`에서 이 환경 변수를 읽어 사용:

```python
class Settings(BaseSettings):
    claude_cli_path: str = "claude"  # .env의 CLAUDE_CLI_PATH로 오버라이드됨
```

### 교훈

- systemd 서비스는 사용자 셸과 다른 환경에서 실행됨
- 외부 CLI 도구는 항상 절대 경로 사용 권장

---

## 문제 3: Claude CLI 타임아웃

### 증상

CLI 경로 문제 해결 후, 또 다른 에러:

```
Claude CLI timeout after 120060ms
```

120초(기본 타임아웃) 후 실패.

### 원인 분석

#### 1단계: 터미널에서 직접 테스트

```bash
timeout 30 claude -p "안녕" --dangerously-skip-permissions
# 성공! "안녕하세요! FastAPI 백엔드 프로젝트에서 무엇을 도와드릴까요?"
```

터미널에서는 정상 작동.

#### 2단계: systemd 환경 확인

```bash
sudo cat /etc/systemd/system/backend-api.service
```

```ini
[Service]
User=funq
Group=funq
WorkingDirectory=/home/funq/dev/backend-api
Environment="PATH=/home/funq/dev/backend-api/venv/bin"
ExecStart=/home/funq/dev/backend-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**발견**: `HOME` 환경 변수가 없음! Claude CLI는 `~/.claude/` 설정을 찾기 위해 HOME이 필요.

#### 3단계: TTY 없이 테스트

systemd는 TTY(터미널) 없이 실행됩니다:

```bash
timeout 30 setsid claude -p "안녕" --dangerously-skip-permissions </dev/null 2>&1
# 성공!
```

TTY 없이도 작동함. 문제는 다른 곳에...

#### 4단계: Python 코드 분석

```python
# app/services/claude_service.py
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    # stdin이 없음!
)
```

**근본 원인**: `stdin`이 명시적으로 설정되지 않아 subprocess가 부모 프로세스의 stdin을 상속. systemd에서는 stdin이 `/dev/null`이 아닌 특수한 상태일 수 있어 Claude CLI가 대기 상태에 빠짐.

### 해결

#### 1. systemd 서비스 파일 수정

```ini
[Service]
User=funq
Group=funq
WorkingDirectory=/home/funq/dev/backend-api
Environment="PATH=/home/funq/dev/backend-api/venv/bin:/home/funq/.local/bin"
Environment="HOME=/home/funq"
ExecStart=/home/funq/dev/backend-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
```

변경사항:
- `HOME=/home/funq` 추가
- PATH에 `~/.local/bin` 추가

```bash
sudo systemctl daemon-reload
sudo systemctl restart backend-api
```

#### 2. Python 코드 수정

```python
# app/services/claude_service.py
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdin=asyncio.subprocess.DEVNULL,  # 추가!
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

`stdin=asyncio.subprocess.DEVNULL`을 추가하여 subprocess가 stdin을 기다리지 않도록 함.

### 교훈

- systemd 환경은 일반 셸과 크게 다름
  - `HOME` 환경 변수가 자동 설정되지 않음
  - TTY가 없음
  - stdin이 특수한 상태
- subprocess로 외부 CLI 호출 시 항상 `stdin=DEVNULL` 설정 권장
- "터미널에서 되는데 서버에서 안 됨" → systemd 환경 차이 의심

---

## 최종 해결책

### 서버 설정 변경

1. **Firebase 인증 파일 복사**

```bash
scp -r firebase/ user@server:~/dev/backend-api/
```

2. **환경 변수 설정** (`.env`)

```
CLAUDE_CLI_PATH=/home/funq/.local/bin/claude
```

3. **systemd 서비스 파일 수정**

```ini
[Service]
User=funq
Group=funq
WorkingDirectory=/home/funq/dev/backend-api
Environment="PATH=/home/funq/dev/backend-api/venv/bin:/home/funq/.local/bin"
Environment="HOME=/home/funq"
ExecStart=/home/funq/dev/backend-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
```

### 코드 수정

```python
# app/services/claude_service.py
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdin=asyncio.subprocess.DEVNULL,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

### 배포 명령어

```bash
sudo systemctl daemon-reload
sudo systemctl restart backend-api
```

---

## 교훈

### 1. 로컬 ≠ 프로덕션

개발 환경에서 작동한다고 프로덕션에서도 작동하리라 가정하지 마세요. 특히:

- 환경 변수 (PATH, HOME 등)
- 파일 시스템 접근 권한
- 네트워크 설정 (CORS 등)

### 2. systemd 서비스의 특수성

systemd 서비스는 일반 사용자 셸과 완전히 다른 환경:

| 항목 | 사용자 셸 | systemd 서비스 |
|------|----------|----------------|
| HOME | 자동 설정 | 명시적 설정 필요 |
| PATH | ~/.bashrc에서 로드 | Environment로 직접 설정 |
| TTY | 있음 | 없음 |
| stdin | 키보드 입력 | 특수 상태 |

### 3. subprocess 호출 시 stdin 처리

외부 프로세스를 호출할 때는 항상 stdin을 명시적으로 처리:

```python
# 권장
subprocess.run(cmd, stdin=subprocess.DEVNULL)

# asyncio
await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.DEVNULL)
```

### 4. 단계별 디버깅

문제가 복합적일 때는 한 번에 하나씩 해결:

1. 서버 로그 확인 (`journalctl -u service-name -f`)
2. 각 컴포넌트 개별 테스트
3. 환경 차이 비교 (터미널 vs systemd)
4. 코드에서 명시적 설정 추가

### 5. 배포 체크리스트

- [ ] 환경 변수 파일 (.env) 동기화
- [ ] 인증/시크릿 파일 복사 (Firebase, API 키 등)
- [ ] systemd 서비스 파일 환경 변수 확인
- [ ] 외부 CLI 도구 경로 확인
- [ ] 로그 모니터링 설정

---

## 관련 파일

- `app/services/claude_service.py` - Claude CLI 호출 로직
- `app/firebase.py` - Firebase Admin SDK 초기화
- `/etc/systemd/system/backend-api.service` - systemd 서비스 설정
- `.env` - 환경 변수 설정

---

*이 문서는 2024년 12월 21일 프로덕션 배포 트러블슈팅 과정을 기록한 것입니다.*
