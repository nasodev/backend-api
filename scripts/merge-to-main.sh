#!/bin/bash

# 현재 브런치를 main에 머지하고 remote에 push하는 스크립트
# Usage: ./scripts/merge-to-main.sh

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 현재 브런치 저장
CURRENT_BRANCH=$(git branch --show-current)
STASHED=false

# main 브런치에서 실행 방지
if [ "$CURRENT_BRANCH" = "main" ]; then
    echo -e "${RED}Error: 이미 main 브런치입니다. 다른 브런치에서 실행하세요.${NC}"
    exit 1
fi

echo -e "${YELLOW}현재 브런치: ${CURRENT_BRANCH}${NC}"

# cleanup 함수 - 스크립트 종료시 원래 브런치로 복귀
cleanup() {
    local exit_code=$?

    # 원래 브런치로 복귀
    if [ "$(git branch --show-current)" != "$CURRENT_BRANCH" ]; then
        echo -e "${YELLOW}원래 브런치로 복귀: ${CURRENT_BRANCH}${NC}"
        git checkout "$CURRENT_BRANCH" 2>/dev/null || true
    fi

    # stash 복원
    if [ "$STASHED" = true ]; then
        echo -e "${YELLOW}stash 복원 중...${NC}"
        git stash pop
    fi

    exit $exit_code
}

trap cleanup EXIT

# 커밋되지 않은 변경사항 확인 및 stash
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo -e "${YELLOW}커밋되지 않은 변경사항 발견. stash 중...${NC}"
    git stash push -u -m "merge-to-main: auto-stash from $CURRENT_BRANCH"
    STASHED=true
fi

# main 브런치로 전환
echo -e "${GREEN}main 브런치로 전환...${NC}"
git checkout main

# remote에서 최신 main pull
echo -e "${GREEN}remote에서 main pull...${NC}"
git pull origin main

# 현재 브런치를 main에 머지
echo -e "${GREEN}${CURRENT_BRANCH} 브런치를 main에 머지...${NC}"
git merge "$CURRENT_BRANCH" -m "Merge branch '$CURRENT_BRANCH' into main"

# remote에 push
echo -e "${GREEN}main을 remote에 push...${NC}"
git push origin main

echo -e "${GREEN}완료! ${CURRENT_BRANCH} 브런치가 main에 머지되고 push되었습니다.${NC}"
