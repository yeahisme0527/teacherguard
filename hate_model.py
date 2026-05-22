"""
티쳐가드 — kor_unsmile 혐오표현 탐지 모듈
=================================================
smilegate-ai/kor_unsmile (한국어 혐오표현 멀티라벨 분류)을
HuggingFace Inference API로 호출한다.
"""
from __future__ import annotations

import streamlit as st

try:
    import requests
except Exception:
    requests = None  # type: ignore

MODEL_ID = "smilegate-ai/kor_unsmile"

# 새 엔드포인트 (우선) / 구 엔드포인트 (폴백)
API_URLS = [
    f"https://router.huggingface.co/hf-inference/models/{MODEL_ID}",
    f"https://api-inference.huggingface.co/models/{MODEL_ID}",
]

HATE_CATEGORIES = {
    "여성/가족", "남성", "성소수자", "인종/국적",
    "연령", "지역", "종교", "기타 혐오",
}


def _token() -> str | None:
    try:
        tok = st.secrets["huggingface"]["token"]
    except Exception:
        return None
    if not tok or str(tok).startswith("YOUR_"):
        return None
    return str(tok)


def is_enabled() -> bool:
    return requests is not None and _token() is not None


def _parse_response(data) -> list[tuple[str, float]] | None:
    """API 응답에서 (label, score) 리스트 추출 — 여러 형식 처리."""
    # [[{label,score},...]] 형식
    if isinstance(data, list) and data and isinstance(data[0], list):
        data = data[0]
    # [{label,score},...] 형식
    if isinstance(data, list):
        labels = [
            (d["label"], float(d["score"]))
            for d in data
            if isinstance(d, dict) and "label" in d and "score" in d
        ]
        return labels if labels else None
    return None


def classify(text: str, threshold: float = 0.25) -> dict | None:
    """text 를 kor_unsmile 로 분류.

    반환: {
        "profanity": bool,
        "hate": bool,
        "hate_categories": [str],
        "labels": [(label, score)],
        "api_error": str | None,   # 디버그용
    }
    실패/미설정 시 None.
    """
    token = _token()
    if requests is None or token is None or not text or not text.strip():
        return None

    last_error = None
    for url in API_URLS:
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"inputs": text, "options": {"wait_for_model": True}},
                timeout=25,
            )
            if resp.status_code == 200:
                labels = _parse_response(resp.json())
                if labels:
                    profanity = any(
                        l == "악플/욕설" and s >= threshold for l, s in labels
                    )
                    hate_hits = [
                        l for l, s in labels
                        if l in HATE_CATEGORIES and s >= threshold
                    ]
                    return {
                        "profanity": profanity,
                        "hate": len(hate_hits) > 0,
                        "hate_categories": hate_hits,
                        "labels": sorted(labels, key=lambda x: -x[1]),
                        "api_error": None,
                    }
            last_error = f"HTTP {resp.status_code}"
        except Exception as e:
            last_error = str(e)
            continue   # 다음 URL 시도

    # 두 엔드포인트 모두 실패 — 에러를 session_state에 기록
    try:
        st.session_state["_hf_last_error"] = last_error
    except Exception:
        pass
    return None
