# Firebase Auth E2E Test

Firebase 인증 → Backend API 연동 테스트

## Preconditions

- kid-chat 서버: `http://localhost:3001` (실행 중)
- backend-api 서버: `http://localhost:8001` (실행 중)
- 테스트 계정: e2e-test / e2e-test

## Test Steps

### 1. kid-chat 로그인

1. Navigate to `http://localhost:3001`
2. Fill 이름 input: `e2e-test`
3. Fill 비밀번호 input: `e2e-test`
4. Click "로그인" button
5. Wait for chat interface to load

### 2. Firebase Token 획득

1. Execute in console: `getToken()`
2. Get token from console log (msgid with "Token:" prefix)
3. Save token for API tests

### 3. Backend API 인증 테스트

#### 3.1 /auth/me 엔드포인트
```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8001/auth/me
```

**Expected Response:**
```json
{
  "uid": "z6SvYTUhVtQUE3mczn3nJ0tLZNv1",
  "email": "e2e-test@kidchat.local",
  "name": null
}
```

#### 3.2 /auth/verify 엔드포인트
```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8001/auth/verify
```

**Expected Response:**
```json
{
  "valid": true,
  "uid": "z6SvYTUhVtQUE3mczn3nJ0tLZNv1"
}
```

#### 3.3 토큰 없이 요청 (실패 케이스)
```bash
curl http://localhost:8001/auth/me
```

**Expected Response:**
```json
{"detail": "Not authenticated"}
```

## Expected Results

- [ ] kid-chat 로그인 성공
- [ ] Firebase ID Token 획득 성공
- [ ] /auth/me 정상 응답 (uid, email 포함)
- [ ] /auth/verify 정상 응답 (valid: true)
- [ ] 토큰 없는 요청 시 403 반환

## Cleanup

1. 브라우저에서 로그아웃 (optional)
2. 서버 종료 (optional)
