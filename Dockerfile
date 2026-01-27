# ============================================
# Stage 1: Builder - 의존성 설치 단계
# ============================================
# 목적: Python 패키지를 설치하고 컴파일하는 단계
# 이 단계의 결과물(설치된 패키지)만 다음 단계로 복사됨
# 빌드 도구(gcc 등)는 최종 이미지에 포함되지 않아 이미지 크기 감소

FROM python:3.12-slim AS builder

# 작업 디렉토리 설정
WORKDIR /app

# 빌드에 필요한 시스템 패키지 설치
# - gcc: C 컴파일러 (일부 Python 패키지 컴파일에 필요)
# - libpq-dev: PostgreSQL 클라이언트 라이브러리 (psycopg2 빌드에 필요)
# --no-install-recommends: 최소한의 패키지만 설치 (이미지 크기 감소)
# rm -rf /var/lib/apt/lists/*: apt 캐시 삭제 (이미지 크기 감소)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 후 패키지 설치
# --no-cache-dir: pip 캐시 사용 안 함 (이미지 크기 감소)
# --user: 사용자 디렉토리에 설치 (~/.local) - 나중에 복사하기 쉬움
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Production - 프로덕션 실행 단계
# ============================================
# 목적: 실제 서비스 운영에 필요한 최소한의 구성만 포함
# builder 단계에서 설치된 패키지만 복사하여 이미지 크기 최소화

FROM python:3.12-slim AS production

WORKDIR /app

# 런타임에 필요한 시스템 패키지만 설치
# - libpq5: PostgreSQL 클라이언트 런타임 라이브러리
# - curl: 헬스체크 및 Claude CLI 설치에 사용
# useradd: 보안을 위해 non-root 사용자 생성
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Claude CLI 설치 (AI 일정 파싱 기능에 필요)
# 심볼릭 링크를 따라가서 실제 바이너리를 /usr/local/bin에 복사
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && cp -L /root/.local/bin/claude /usr/local/bin/claude \
    && chmod +x /usr/local/bin/claude

# builder 단계에서 설치한 Python 패키지 복사
# /root/.local (builder) → /home/appuser/.local (production)
COPY --from=builder /root/.local /home/appuser/.local

# 환경 변수 설정
# PATH: 설치된 패키지의 실행 파일을 찾을 수 있도록 경로 추가
# PYTHONUNBUFFERED=1: Python 출력을 버퍼링하지 않음 (로그 즉시 출력)
# PYTHONDONTWRITEBYTECODE=1: .pyc 파일 생성 안 함 (컨테이너에선 불필요)
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 애플리케이션 코드 복사
# --chown: 파일 소유자를 appuser로 설정 (보안)
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./

# non-root 사용자로 전환 (보안 강화)
# root로 실행하면 컨테이너 탈출 시 호스트에 영향 줄 수 있음
USER appuser

# 헬스체크 설정
# Docker가 컨테이너 상태를 주기적으로 확인
# --interval: 체크 간격 (30초마다)
# --timeout: 응답 대기 시간 (10초)
# --start-period: 시작 후 대기 시간 (5초, 앱 초기화 시간)
# --retries: 실패 허용 횟수 (3번 실패하면 unhealthy)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 컨테이너가 사용하는 포트 문서화 (실제 포트 오픈은 docker-compose에서)
EXPOSE 8000

# 컨테이너 시작 시 실행할 명령어
# uvicorn: ASGI 서버
# app.main:app: FastAPI 앱 위치
# --host 0.0.0.0: 모든 네트워크 인터페이스에서 접속 허용
# --port 8000: 8000번 포트에서 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 3: Development - 개발 환경 단계
# ============================================
# 목적: 테스트 도구 포함, 핫 리로드 지원
# production 단계를 기반으로 개발에 필요한 것들 추가

FROM production AS development

# 개발 도구 설치를 위해 임시로 root 전환
USER root

# 테스트 관련 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio httpx

# Claude CLI 설치 및 PATH 설정
# claude는 심볼릭 링크이므로 실제 파일을 복사 (-L 옵션으로 링크 따라감)
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && cp -L /root/.local/bin/claude /usr/local/bin/claude \
    && chmod +x /usr/local/bin/claude

# 테스트 파일은 docker-compose.yml에서 볼륨 마운트로 연결
# (빌드 시점이 아닌 실행 시점에 연결됨)

# 다시 non-root 사용자로 전환
USER appuser

# 개발 모드 명령어 (--reload: 코드 변경 시 자동 재시작)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
