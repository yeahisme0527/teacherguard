"""
티쳐가드 — kor_unsmile 혐오표현 탐지 모듈
=================================================
smilegate-ai/kor_unsmile (한국어 혐오표현 멀티라벨 분류)을
HuggingFace Inference API로 호출한다.

- HF 토큰이 없거나 호출이 실패하면 None 을 반환 → 호출 측에서
  기존 키워드 탐지 결과를 그대로 사용 (graceful fallback).
- Streamlit Cloud 무료 플랜 메모리를 아끼려고 모델을 직접
  띄우지 않고 가벼운 HTTP 호출만 한다.
"""
from __future__ import annotations

import streamlit as st

try:
    import requests
except Exception:
    requests = None  # type: ignore

MODEL_ID = "smilegate-ai/kor_unsmile"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

# 악플/욕설을 제외한 혐오 카테고리
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


def classify(text: str, threshold: float = 0.4) -> dict | None:
    """text 를 kor_unsmile 로 분류.

    반환: {
        "profanity": bool,            # 악플/욕설 탐지 여부
        "hate": bool,                 # 혐오 카테고리 탐지 여부
        "hate_categories": [str],     # 탐지된 혐오 카테고리
        "labels": [(label, score)],   # 점수 내림차순 전체 라벨
    }
    실패/미설정 시 None.
    """
    token = _token()
    if requests is None or token is None or not text or not text.strip():
        return None
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": text, "options": {"wait_for_model": True}},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # 응답 형식: [[{label,score}, ...]] 또는 [{label,score}, ...]
        if isinstance(data, list) and data and isinstance(data[0], list):
            data = data[0]
        if not isinstance(data, list):
            return None
        labels = [
            (d["label"], float(d["score"]))
            for d in data
            if isinstance(d, dict) and "label" in d and "score" in d
        ]
        if not labels:
            return None
        profanity = any(l == "악플/욕설" and s >= threshold for l, s in labels)
        hate_hits = [l for l, s in labels if l in HATE_CATEGORIES and s >= threshold]
        return {
            "profanity": profanity,
            "hate": len(hate_hits) > 0,
            "hate_categories": hate_hits,
            "labels": sorted(labels, key=lambda x: -x[1]),
        }
    except Exception:
        return None
