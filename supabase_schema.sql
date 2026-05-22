-- ============================================================
-- 티쳐가드(TeacherGuard) Supabase 스키마
-- ------------------------------------------------------------
-- Supabase 대시보드 → SQL Editor 에 전체를 복붙해서 한 번 실행하세요.
-- ============================================================

-- ------------------------------------------------------------
-- 1. profiles : auth.users 에 1:1로 붙는 프로필 테이블
-- ------------------------------------------------------------
create table if not exists public.profiles (
    id            uuid primary key references auth.users(id) on delete cascade,
    email         text not null,
    display_name  text,
    school_region text,   -- 시도 (예: 서울, 경기)
    school_type   text,   -- 학교급 (예: 초등학교, 중학교, 고등학교)
    school_name   text,   -- 학교명 (예: 서울고등학교)
    created_at    timestamptz not null default now()
);

-- 기존 DB에 컬럼이 없는 경우 추가 (이미 있으면 무시)
alter table public.profiles add column if not exists school_region text;
alter table public.profiles add column if not exists school_type   text;
alter table public.profiles add column if not exists school_name   text;
alter table public.profiles add column if not exists invite_code   text unique; -- 교사 초대코드 (6자리)

alter table public.messages  add column if not exists room_id uuid; -- 교사의 user_id (방 식별자)
create index if not exists messages_room_id_idx on public.messages (room_id);

-- ------------------------------------------------------------
-- 2. messages : 채팅 메시지 (학부모 발송 + AI 응답)
-- ------------------------------------------------------------
create table if not exists public.messages (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references auth.users(id) on delete cascade,
    sender_role       text not null check (sender_role in ('parent', 'ai', 'teacher')),
    text              text not null,
    blurred_text      text,
    blocked           boolean not null default false,
    is_profanity      boolean not null default false,
    emotion_level     int    not null default 1,
    severity          int    not null default 1,
    types_detected    jsonb  not null default '[]'::jsonb,
    detected_keywords jsonb  not null default '[]'::jsonb,
    display_time      text,                      -- "HH:MM" 표시용
    created_at        timestamptz not null default now()
);

create index if not exists messages_created_at_idx
    on public.messages (created_at desc);

create index if not exists messages_is_profanity_idx
    on public.messages (is_profanity)
    where is_profanity = true;

-- ------------------------------------------------------------
-- 3. blocked_users : 교사가 차단한 학부모 ID
-- ------------------------------------------------------------
create table if not exists public.blocked_users (
    id              uuid primary key default gen_random_uuid(),
    teacher_id      uuid not null references auth.users(id) on delete cascade,
    blocked_user_id text not null,
    created_at      timestamptz not null default now(),
    unique (teacher_id, blocked_user_id)
);

-- ------------------------------------------------------------
-- 4. 신규 가입 시 profiles 자동 생성 트리거
-- ------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
    insert into public.profiles (id, email, display_name)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1))
    );
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();

-- ------------------------------------------------------------
-- 5. RLS (Row Level Security)
-- ------------------------------------------------------------
alter table public.profiles      enable row level security;
alter table public.messages      enable row level security;
alter table public.blocked_users enable row level security;

-- profiles : 인증된 사용자는 모두 조회, 본인 것만 수정/생성
drop policy if exists "profiles_select" on public.profiles;
create policy "profiles_select" on public.profiles
    for select using (auth.role() = 'authenticated');

drop policy if exists "profiles_insert" on public.profiles;
create policy "profiles_insert" on public.profiles
    for insert with check (auth.uid() = id);

drop policy if exists "profiles_update" on public.profiles;
create policy "profiles_update" on public.profiles
    for update using (auth.uid() = id);

-- messages : 인증된 사용자는 모두 조회 가능(교사 대시보드용),
--           본인 user_id 로만 insert 가능
drop policy if exists "messages_select" on public.messages;
create policy "messages_select" on public.messages
    for select using (auth.role() = 'authenticated');

drop policy if exists "messages_insert" on public.messages;
create policy "messages_insert" on public.messages
    for insert with check (auth.uid() = user_id);

-- blocked_users : 본인이 만든 차단 목록만 관리
drop policy if exists "blocked_select" on public.blocked_users;
create policy "blocked_select" on public.blocked_users
    for select using (auth.uid() = teacher_id);

drop policy if exists "blocked_insert" on public.blocked_users;
create policy "blocked_insert" on public.blocked_users
    for insert with check (auth.uid() = teacher_id);

drop policy if exists "blocked_delete" on public.blocked_users;
create policy "blocked_delete" on public.blocked_users
    for delete using (auth.uid() = teacher_id);
