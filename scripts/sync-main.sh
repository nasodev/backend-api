#!/bin/bash
#
# sync-main.sh
# main 브랜치에서 최신 변경사항을 가져와 현재 브랜치에 머지
# 변경사항이 있으면 자동으로 stash 후 복원
#
# 사용법:
#   ./scripts/sync-main.sh           # 기본 (main 브랜치)
#   ./scripts/sync-main.sh develop   # 다른 소스 브랜치 지정
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 소스 브랜치 (기본값: main)
SOURCE_BRANCH="${1:-main}"

# 현재 브랜치 확인
CURRENT_BRANCH=$(git branch --show-current)

# stash 사용 여부 플래그
STASHED=false

# 종료 시 stash 복원 (에러 발생 시에도)
cleanup() {
    if [ "$STASHED" = true ]; then
        echo -e "\n${BLUE}[복원] Stash된 변경사항 복원 중...${NC}"
        if git stash pop; then
            echo -e "${GREEN}✓ 변경사항이 복원되었습니다.${NC}"
        else
            echo -e "${RED}✗ Stash 복원 중 충돌이 발생했습니다.${NC}"
            echo -e "${YELLOW}수동으로 해결하세요: git stash show -p | git apply${NC}"
        fi
    fi
}

trap cleanup EXIT

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Git Sync: ${SOURCE_BRANCH} → ${CURRENT_BRANCH}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 현재 브랜치가 소스 브랜치와 같으면 pull만 수행
if [ "$CURRENT_BRANCH" == "$SOURCE_BRANCH" ]; then
    echo -e "${YELLOW}현재 ${SOURCE_BRANCH} 브랜치입니다. pull만 수행합니다.${NC}"
    git pull origin "$SOURCE_BRANCH"
    echo -e "${GREEN}✓ 완료${NC}"
    exit 0
fi

# 작업 디렉토리에 변경사항이 있는지 확인
HAS_STAGED=$(git diff --cached --quiet; echo $?)
HAS_UNSTAGED=$(git diff --quiet; echo $?)
HAS_UNTRACKED=$(git ls-files --others --exclude-standard | head -1)

if [ "$HAS_STAGED" -ne 0 ] || [ "$HAS_UNSTAGED" -ne 0 ] || [ -n "$HAS_UNTRACKED" ]; then
    echo -e "\n${YELLOW}[Stash] 커밋되지 않은 변경사항 감지${NC}"
    git status --short

    echo -e "\n${BLUE}[Stash] 변경사항을 임시 저장합니다...${NC}"

    # untracked 파일 포함하여 stash
    STASH_MSG="sync-main: auto-stash on $(date '+%Y-%m-%d %H:%M:%S')"
    git stash push -u -m "$STASH_MSG"
    STASHED=true

    echo -e "${GREEN}✓ Stash 완료 (머지 후 자동 복원됩니다)${NC}"
fi

# remote 업데이트
echo -e "\n${BLUE}[1/4] Remote 정보 업데이트...${NC}"
git fetch origin

# main 브랜치의 새로운 커밋 확인
LOCAL_HASH=$(git rev-parse "origin/${SOURCE_BRANCH}" 2>/dev/null || echo "none")
REMOTE_HASH=$(git ls-remote origin "$SOURCE_BRANCH" | cut -f1)

if [ "$LOCAL_HASH" == "$REMOTE_HASH" ]; then
    echo -e "${YELLOW}${SOURCE_BRANCH}에 새로운 변경사항이 없습니다.${NC}"

    # 현재 브랜치가 main과 차이가 있는지 확인
    BEHIND=$(git rev-list --count "${CURRENT_BRANCH}..origin/${SOURCE_BRANCH}" 2>/dev/null || echo "0")

    if [ "$BEHIND" -gt 0 ]; then
        echo -e "${BLUE}하지만 현재 브랜치가 ${SOURCE_BRANCH}보다 ${BEHIND}개 커밋 뒤처져 있습니다.${NC}"
    else
        echo -e "${GREEN}✓ 이미 최신 상태입니다.${NC}"
        exit 0
    fi
fi

# 새로운 커밋 개수 확인
NEW_COMMITS=$(git rev-list --count "${CURRENT_BRANCH}..origin/${SOURCE_BRANCH}" 2>/dev/null || echo "0")

if [ "$NEW_COMMITS" -eq 0 ]; then
    echo -e "${GREEN}✓ 머지할 새로운 커밋이 없습니다.${NC}"
    exit 0
fi

echo -e "\n${BLUE}[2/4] ${SOURCE_BRANCH}에서 ${NEW_COMMITS}개의 새로운 커밋 발견${NC}"

# 새로운 커밋 목록 표시
echo -e "${YELLOW}새로운 커밋:${NC}"
git log --oneline "${CURRENT_BRANCH}..origin/${SOURCE_BRANCH}" | head -10

if [ "$NEW_COMMITS" -gt 10 ]; then
    echo -e "${YELLOW}... 외 $((NEW_COMMITS - 10))개${NC}"
fi

# 머지 수행
echo -e "\n${BLUE}[3/4] origin/${SOURCE_BRANCH}를 ${CURRENT_BRANCH}에 머지 중...${NC}"

if git merge "origin/${SOURCE_BRANCH}" --no-edit; then
    echo -e "\n${BLUE}[4/4] 머지 완료${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ${NEW_COMMITS}개 커밋이 성공적으로 머지되었습니다.${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    echo -e "\n${RED}✗ 머지 충돌이 발생했습니다.${NC}"
    echo -e "${YELLOW}충돌을 해결한 후 다음 명령을 실행하세요:${NC}"
    echo -e "  git add ."
    echo -e "  git commit"
    # cleanup 함수에서 stash pop 시도됨
    exit 1
fi
