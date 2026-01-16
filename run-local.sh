#!/bin/bash
# 로컬 개발 서버 실행 스크립트

set -e

cd "$(dirname "$0")"

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
