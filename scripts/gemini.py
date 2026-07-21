"""Gemini 1차 요약 — httpx REST 직접 호출(라이브러리 hang 회피, 메모리 교훈).

밤사이 텔레그램 메시지를 청크로 나눠 각 메시지를 정규화 항목으로 요약/1차선별.
"""
import json
import httpx
import config
from krx_calendar import to_kst_iso

CHAR_BUDGET = 12000   # 청크당 대략 문자 예산
MSG_TRUNC = 1600      # 메시지 본문 절단

SYS = (
    "너는 한국 증권사 리서치 데스크의 애널리스트다. 아래는 밤사이(전일 미국장 전후) 텔레그램 "
    "채널들에 올라온 증시 관련 메시지다. 각 메시지를 검토해 '미국 증시·글로벌 매크로'와 관련된 것만 "
    "정규화해 JSON 배열로 반환하라.\n"
    "- 미국 개별종목/지수/실적/가이던스, 연준·금리·물가·환율·유가 등 글로벌 매크로, 주요 해외 헤드라인 → 포함.\n"
    "- 한국 개별종목 급등/공시/신고가/차트매매 등 국장 노이즈, 광고/잡담/중복 → 제외(빈 배열이면 []).\n"
    "각 항목 필드: {\"i\": 원본인덱스(int), \"one_line\": 한 줄 핵심(한국어), "
    "\"detail\": 2~4문장 요약(한국어, 숫자·고유명사 보존), "
    "\"region\": \"US\"|\"글로벌\"|\"아시아\"|\"기타\", "
    "\"topic\": 짧은 주제 태그(예 '연준·금리','엔비디아·AI반도체','유가·에너지'), "
    "\"tickers\": [관련 티커/종목명...] }\n"
    "반드시 유효한 JSON 배열만 출력."
)

def _endpoint():
    return (f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{config.GEMINI_MODEL()}:generateContent")

def _chunk(messages):
    cur, size = [], 0
    for m in messages:
        blob = m["_line"]
        if cur and size + len(blob) > CHAR_BUDGET:
            yield cur
            cur, size = [], 0
        cur.append(m)
        size += len(blob)
    if cur:
        yield cur

def _call_gemini(prompt):
    payload = {
        "system_instruction": {"parts": [{"text": SYS}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    headers = {"x-goog-api-key": config.GEMINI_API_KEY(), "Content-Type": "application/json"}
    r = httpx.post(_endpoint(), json=payload, headers=headers,
                   timeout=httpx.Timeout(120.0, read=100.0, connect=10.0))
    r.raise_for_status()
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return []
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("["):]  # 코드펜스 방어
    try:
        arr = json.loads(text)
        return arr if isinstance(arr, list) else []
    except json.JSONDecodeError:
        return []

def summarize(messages):
    """messages: archive 원본 리스트. returns 정규화 항목 리스트(시계열 순)."""
    # 인덱스 부여 + 프롬프트용 라인 구성
    enriched = []
    for idx, m in enumerate(messages):
        kst = to_kst_iso(m.get("date", ""))
        chat = m.get("chat_name", "")
        text = (m.get("text") or "").replace("\r", " ").strip()[:MSG_TRUNC]
        m["_kst"] = kst
        m["_line"] = f"[{idx}] ({kst} · {chat})\n{text}\n"
        enriched.append(m)

    items = []
    for chunk in _chunk(enriched):
        prompt = "다음 메시지들을 처리하라:\n\n" + "".join(c["_line"] for c in chunk)
        for it in _call_gemini(prompt):
            if not isinstance(it, dict):
                continue
            i = it.get("i")
            if not isinstance(i, int) or i < 0 or i >= len(messages):
                # 인덱스 소실 시 메타 없이 통과
                src = None
            else:
                src = messages[i]
            it["time_kst"] = (src or {}).get("_kst", "")
            it["chat"] = (src or {}).get("chat_name", "")
            it["link"] = _extract_link((src or {}).get("text", ""))
            items.append(it)

    items.sort(key=lambda x: x.get("time_kst", ""))
    return items

def _extract_link(text):
    if not text:
        return None
    import re
    m = re.search(r"https?://[^\s)]+", text)
    return m.group(0) if m else None
