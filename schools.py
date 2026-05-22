"""
티쳐가드 — 전국 학교 검색 모듈 (NEIS Open API)
======================================================
교육부 NEIS(나이스) 학교정보 API를 이용해
지역·학교급별 학교 목록을 조회한다.

API 키 발급(무료, 즉시 발급):
  https://open.neis.go.kr/portal/guide/apiRegisterV2.do

secrets.toml 설정:
  [neis]
  key = "발급받은_키_여기에"

API 키 없이도 앱은 정상 동작합니다 — 학교명 직접 입력 모드로 폴백.
어린이집은 NEIS 미지원(복지부 소관)이므로 항상 직접 입력.
"""
from __future__ import annotations

import streamlit as st

try:
    import requests as _req  # type: ignore
except ImportError:
    _req = None  # type: ignore

NEIS_API_URL = "https://open.neis.go.kr/hub/schoolInfo"

# 시도명 → NEIS 교육청 코드
REGION_CODES: dict[str, str] = {
    "서울": "B10", "부산": "C10", "대구": "D10", "인천": "E10",
    "광주": "F10", "대전": "G10", "울산": "H10", "세종": "I10",
    "경기": "J10", "강원": "K10", "충북": "M10", "충남": "N10",
    "전북": "P10", "전남": "Q10", "경북": "R10", "경남": "S10", "제주": "T10",
}

# 선택 가능한 학교급 목록 (어린이집은 NEIS 미지원 → 수동 입력)
SCHOOL_TYPES: list[str] = [
    "유치원", "초등학교", "중학교", "고등학교", "특수학교", "어린이집",
]

# NEIS API가 지원하는 학교급 (어린이집 제외)
_NEIS_SUPPORTED = {"유치원", "초등학교", "중학교", "고등학교", "특수학교"}


# ============================================================
# API 키 확인
# ============================================================
def _neis_key() -> str | None:
    try:
        k = st.secrets["neis"]["key"]
        return str(k) if k and not str(k).startswith("YOUR_") else None
    except Exception:
        return None


def is_api_enabled() -> bool:
    """NEIS API 키가 설정돼 있으면 True."""
    return _req is not None and _neis_key() is not None


# ============================================================
# 정적 목록
# ============================================================
def get_regions() -> list[str]:
    return list(REGION_CODES.keys())


def get_school_types() -> list[str]:
    return SCHOOL_TYPES


# ============================================================
# 학교 목록 조회 (NEIS API, 1일 캐시)
# ============================================================
@st.cache_data(ttl=86_400, show_spinner=False)
def _fetch_from_neis(region_code: str, school_type: str) -> list[str]:
    """NEIS API → 학교명 리스트. 실패하면 빈 리스트 반환."""
    key = _neis_key()
    if not key or _req is None:
        return []
    names: list[str] = []
    try:
        for page in range(1, 6):          # 페이지당 1000개, 최대 5000개
            r = _req.get(
                NEIS_API_URL,
                params={
                    "KEY": key, "Type": "json",
                    "pIndex": page, "pSize": 1000,
                    "ATPT_OFCDC_SC_CODE": region_code,
                    "SCHUL_KND_SC_NM": school_type,
                },
                timeout=15,
            )
            body = r.json()
            info = body.get("schoolInfo")
            if not info or len(info) < 2:
                break
            rows = info[1].get("row", [])
            if not rows:
                break
            names.extend(row["SCHUL_NM"] for row in rows)
            if len(rows) < 1000:          # 마지막 페이지
                break
    except Exception:
        pass
    return sorted(set(names))


def search_schools(region: str, school_type: str, query: str = "") -> list[str]:
    """지역·학교급으로 학교명 목록 반환.

    Parameters
    ----------
    region      : 시도명 (예: "서울")
    school_type : 학교급 (예: "고등학교")
    query       : 학교명 부분 검색어 (빈 문자열이면 전체)

    Returns
    -------
    list[str]   : 학교명 리스트. API 미설정·어린이집이면 [].
    """
    if school_type not in _NEIS_SUPPORTED or not is_api_enabled():
        return []
    code = REGION_CODES.get(region, "")
    if not code:
        return []
    schools = _fetch_from_neis(code, school_type)
    if query:
        q = query.strip()
        schools = [s for s in schools if q in s]
    return schools
