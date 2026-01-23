#!/bin/bash
# 로컬 개발 서버 실행 스크립트
# 사용법:
#   ./run-local.sh          # Docker로 실행 (기본)
#   ./run-local.sh docker   # Docker로 실행
#   ./run-local.sh venv     # venv로 실행 (기존 방식)

set -e

cd "$(dirname "$0")"

MODE="${1:-docker}"

case "$MODE" in
    docker)
        echo "=== Docker 모드로 실행 ==="

        # Docker 네트워크 생성 (없으면)
        if ! docker network ls | grep -q "funq-network"; then
            echo "Creating funq-network..."
            docker network create funq-network
        fi

        # 기존 컨테이너 정리
        docker compose down 2>/dev/null || true

        echo "Starting backend-api with Docker on port 28000..."
        docker compose up --build
        ;;

    venv)
        echo "=== venv 모드로 실행 ==="

        # venv 생성 (없으면)
        if [ ! -d "venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
            source venv/bin/activate
            echo "Installing dependencies..."
            pip install -r requirements.txt
        else
            source venv/bin/activate
        fi

        echo "Starting backend-api on port 28000..."
        uvicorn app.main:app --reload --host 0.0.0.0 --port 28000
        ;;

    *)
        echo "사용법: ./run-local.sh [docker|venv]"
        echo "  docker - Docker Compose로 실행 (기본)"
        echo "  venv   - Python venv로 실행 (기존 방식)"
        exit 1
        ;;
esac
