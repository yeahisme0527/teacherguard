# 🗄️ Supabase 연동 설정 가이드

티쳐가드의 채팅·보관함·차단 목록을 클라우드 DB(Supabase)에 영구 저장하기 위한
1회성 셋업 가이드입니다. 무료 플랜으로 충분합니다.

> 설정을 건너뛰어도 앱은 **게스트 모드(로컬 세션)** 로 동작합니다.
> 새로고침하면 데이터가 사라진다는 점만 다르고, 모든 기능은 그대로 체험할 수 있습니다.

---

## 1단계 · Supabase 프로젝트 만들기

1. https://supabase.com 접속 → **Start your project** → GitHub 계정 등으로 가입
2. **New project** 클릭
   - **Name**: `teacherguard` (자유)
   - **Database Password**: 강한 비밀번호 (메모해두기, DB 접속용)
   - **Region**: `Northeast Asia (Seoul)` 권장
   - 무료 플랜 선택
3. 프로비저닝(약 1~2분) 완료까지 대기

## 2단계 · 스키마 SQL 실행

1. 좌측 메뉴에서 **SQL Editor** → **+ New query**
2. 이 폴더의 [`supabase_schema.sql`](supabase_schema.sql) **전체 내용**을 복사해서 붙여넣기
3. 우측 **Run** (또는 `Ctrl+Enter`) 실행
4. 좌측 **Table Editor** 에 `profiles`, `messages`, `blocked_users` 세 테이블이 생겼는지 확인

## 3단계 · 이메일 인증 정책 (선택)

개발 중에는 **이메일 인증 없이** 바로 로그인되게 두는 편이 편합니다.

- **Authentication → Sign In / Up → Email** 패널에서
  `Confirm email` 토글을 **OFF** 로 두면 가입 즉시 로그인 가능
- 운영 단계로 넘어가면 다시 ON 해주세요.

## 4단계 · API 키를 Streamlit 시크릿에 넣기

1. Supabase 대시보드 좌측 **Project Settings → API**
2. 아래 두 값을 복사:
   - **Project URL** (예: `https://abcxyz.supabase.co`)
   - **Project API keys → anon / public** (긴 JWT 문자열)
3. 로컬에서 이 폴더의
   `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` 로 복사
4. 다음과 같이 값을 채워 넣기:

   ```toml
   [supabase]
   url      = "https://abcxyz.supabase.co"
   anon_key = "eyJhbGciOi....."
   ```

5. `.streamlit/secrets.toml` 은 이미 `.gitignore` 처리되어 깃에 올라가지 않습니다.

### Streamlit Cloud 배포할 때

1. Streamlit Cloud 앱 페이지 → **Settings → Secrets**
2. 위의 TOML 내용을 그대로 붙여넣고 저장
3. 앱 재시작

## 5단계 · 실행

```powershell
cd phase6_streamlit
pip install -r requirements.txt
streamlit run streamlit_app.py
```

첫 화면에 **로그인 / 회원가입 탭**이 보이면 성공 🎉
- 회원가입 → 곧바로 로그인
- 로그인하면 사이드바에 `🟢 Supabase 연결됨` 표시
- 학부모로 메시지를 보낸 뒤 **새로고침** 해도 기록이 유지되면 DB 연동 완료

---

## 데이터 구조 한 줄 요약

| 테이블 | 무엇을 저장하나요 |
|---|---|
| `profiles` | 가입 시 자동 생성. 이메일/표시이름 |
| `messages` | 모든 채팅 메시지(학부모 발송 + AI 응답). 분석 결과(감정/유형/키워드) 포함 |
| `blocked_users` | 교사가 차단한 학부모 ID |

## 자주 묻는 질문

**Q. RLS(Row Level Security)는요?**
A. `supabase_schema.sql`에 기본 정책이 들어 있습니다.
- `messages`: 인증된 모든 사용자 조회 가능(교사 대시보드에서 봐야 하므로), 본인 user_id 로만 insert
- `blocked_users`: 본인이 만든 항목만 보고 수정

**Q. 비밀번호를 잊었어요.**
A. Supabase 대시보드 → Authentication → Users 에서 비밀번호 재설정 메일을 보낼 수 있습니다.

**Q. 데이터를 다 지우고 싶어요.**
A. SQL Editor 에서
```sql
truncate table public.messages, public.blocked_users restart identity cascade;
```
