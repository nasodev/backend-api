# Git Merge (현재 브런치 → main)

현재 브런치를 main에 머지하고 remote에 push해라.

## 실행

```bash
./scripts/merge-to-main.sh
```

## 예상 결과

- main 브런치로 전환
- remote main pull (최신화)
- 현재 브런치를 main에 머지
- remote에 push
- 원래 브런치로 복귀
