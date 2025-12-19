#!/bin/bash
# Backend API 서버 설정 스크립트
# 서버에서 sudo 권한으로 실행

set -e

echo "=== 1. PostgreSQL 시작 및 활성화 ==="
sudo systemctl start postgresql
sudo systemctl enable postgresql

echo "=== 2. PostgreSQL DB 및 사용자 생성 ==="
# postgres 사용자로 전환하여 실행
sudo -u postgres psql <<EOF
-- backend_api 사용자 생성 (비밀번호 변경 필요!)
CREATE USER backend_api WITH PASSWORD 'your_secure_password_here';

-- backend_api 데이터베이스 생성
CREATE DATABASE backend_api OWNER backend_api;

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE backend_api TO backend_api;
EOF

echo "=== 3. .env 파일 생성 ==="
cat > /home/funq/dev/backend-api/.env <<EOF
DEBUG=false
DATABASE_URL=postgresql://backend_api:your_secure_password_here@localhost:5432/backend_api
CORS_ORIGINS=["http://localhost:3000","https://blog.funq.kr","https://api.funq.kr"]
EOF

echo "=== 4. Nginx 설정 ==="
sudo cp /home/funq/dev/backend-api/deploy/nginx-api.conf /etc/nginx/sites-available/backend-api.conf
sudo ln -sf /etc/nginx/sites-available/backend-api.conf /etc/nginx/sites-enabled/backend-api.conf
sudo nginx -t
sudo systemctl reload nginx

echo "=== 5. SSL 인증서 발급 (Let's Encrypt) ==="
echo "먼저 DNS에 api.funq.kr A 레코드를 추가한 후 실행하세요"
echo "sudo certbot --nginx -d api.funq.kr"

echo "=== 6. systemd 서비스 등록 ==="
sudo cp /home/funq/dev/backend-api/deploy/backend-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend-api
sudo systemctl start backend-api

echo "=== 7. 상태 확인 ==="
sudo systemctl status backend-api --no-pager

echo ""
echo "=== 설정 완료! ==="
echo "API 확인: curl http://localhost:8000/health"
