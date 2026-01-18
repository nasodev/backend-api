# CLAUDE.md 파일 최신화 프롬프트

## 목적
프로젝트의 CLAUDE.md 파일을 현재 코드베이스 상태에 맞게 최신화합니다.

## 실행 방법
```
프로젝트 루트의 CLAUDE.md 파일을 최신화해줘
```

## 분석 항목

### 1. 프로젝트 구조 분석
- `app/**/*.py` 파일 목록 확인
- `tests/**/*.py` 파일 목록 확인
- 디렉토리 구조 파악

### 2. 기술 스택 확인
- `requirements.txt` 또는 `pyproject.toml` 파싱
- 주요 라이브러리 버전 확인

### 3. API 엔드포인트 파악
- `app/routers/` 내 라우터 파일 분석
- `app/main.py`에서 include된 라우터 확인

### 4. 데이터베이스 모델 분석
- `app/models/` 내 모델 파일 분석
- 테이블명, 컬럼, 관계 파악

### 5. 서비스 레이어 분석
- `app/services/` 내 서비스 파일 분석
- Protocol 및 구현체 파악

### 6. 테스트 구조 분석
- `tests/unit/`, `tests/integration/`, `tests/e2e/` 파악
- `tests/fakes/` Fake 구현체 파악

## CLAUDE.md 필수 섹션

```markdown
# Project Name - Claude Code Instructions

## Project Overview
- 프로젝트 설명
- 주요 기능 목록

## Tech Stack
- 언어, 프레임워크, 라이브러리 버전

## Project Structure
- 디렉토리 트리 (주요 파일 설명 포함)

## Commands
- 개발 서버 실행
- 테스트 실행
- 마이그레이션 명령어

## API Endpoints
- 엔드포인트 목록 (HTTP method, path, 설명)

## Database Models
- 모델별 필드 설명

## Conventions
- API Routes 규칙
- Database Models 규칙
- Pydantic Schemas 규칙
- Dependencies/DI 패턴
- Testing 규칙

## Environment Variables
- 필수 환경변수 목록

## Deployment
- 배포 환경 정보

## Testing Guidelines
- 테스트 작성 규칙
```

## 주의사항

1. **기존 내용 보존**: 수동으로 작성된 설명이나 컨벤션은 유지
2. **자동 감지**: 코드베이스에서 자동으로 감지 가능한 내용만 업데이트
3. **일관성**: 기존 CLAUDE.md 스타일과 일관되게 작성
4. **검증**: 업데이트 후 실제 파일/디렉토리 존재 여부 확인
