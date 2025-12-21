# Git Sync (main → 현재 브런치)

main 브런치의 최신 변경사항을 현재 브런치로 가져와라.

## 실행

```bash
./scripts/sync-main.sh
```

## 예상 결과

- remote/main pull
- 현재 브런치에 main 머지
- 커밋되지 않은 변경사항은 자동 stash/복원
