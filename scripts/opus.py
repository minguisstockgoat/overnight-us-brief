"""Opus 4.8 큐레이션 — Anthropic Messages API(httpx REST, 구조화 출력).

Gemini 정규화 항목 → 미장/매크로만 남기고 주제 클러스터·시계열·중요도·headline 생성.
"""
import json
import httpx
import config

ENDPOINT = "https://api.anthropic.com/v1/messages"

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "array", "items": {"type": "string"}},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "importance": {"type": "string", "enum": ["핵심", "주요", "참고"]},
                    "region": {"type": "string", "enum": ["US", "글로벌", "아시아", "기타"]},
                    "summary": {"type": "string"},
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "timeKst": {"type": "string"},
                                "summary": {"type": "string"},
                                "chat": {"type": "string"},
                                "link": {"type": ["string", "null"]},
                                "tickers": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["timeKst", "summary", "chat", "link", "tickers"],
                        },
                    },
                },
                "required": ["title", "importance", "region", "summary", "events"],
            },
        },
    },
    "required": ["headline", "topics"],
}

SYS = (
    "너는 프랍 트레이딩 데스크의 시니어 애널리스트다. 아래는 밤사이(전 영업일 미국장 전후) "
    "텔레그램에서 수집·1차요약된 증시 뉴스 항목들이다. 국장 개장 전 트레이더가 5분 안에 밤사이 "
    "미장 시황을 파악하도록 '전날 미장 시황 브리핑'을 만든다.\n"
    "규칙:\n"
    "1) 미국 증시·글로벌 매크로만 남긴다. 한국 개별종목/공시/급등주 등 국장 노이즈는 제외.\n"
    "2) 같은 사건을 다룬 항목은 하나의 주제(topic)로 묶고, 주제 내 events는 시각(timeKst) 오름차순 정렬.\n"
    "3) 각 주제에 중요도(importance)를 부여: 핵심(장 방향/시장 전체 영향) > 주요 > 참고.\n"
    "4) topics는 중요도 높은 순으로 정렬.\n"
    "5) headline: 밤사이 가장 중요한 3~5개를 한 줄씩(한국어). 지수·금리·빅테크·매크로 우선.\n"
    "6) 근거 없는 추측 금지. 각 event.summary는 원문 사실만 간결히. link/chat/tickers는 소스에서 보존.\n"
    "반드시 제공된 JSON 스키마로만 응답."
)

def curate(items, window):
    compact = [
        {
            "t": it.get("time_kst", ""),
            "chat": it.get("chat", ""),
            "one": it.get("one_line", ""),
            "detail": it.get("detail", ""),
            "region": it.get("region", ""),
            "topic": it.get("topic", ""),
            "tickers": it.get("tickers", []),
            "link": it.get("link"),
        }
        for it in items
    ]
    user = (
        f"창(KST): {window['start_kst'].isoformat()} ~ {window['end_kst'].isoformat()} "
        f"(전 영업일 {window['prev_trading_day']} 20:00 → 당일 07:00)\n"
        f"항목 수: {len(compact)}\n\n"
        f"항목(JSON):\n{json.dumps(compact, ensure_ascii=False)}"
    )
    payload = {
        "model": config.OPUS_MODEL(),
        "max_tokens": 16000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        "system": SYS,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    r = httpx.post(ENDPOINT, json=payload, headers=headers,
                   timeout=httpx.Timeout(600.0, read=590.0, connect=10.0))
    if r.status_code >= 400:
        raise RuntimeError(f"Anthropic {r.status_code}: {r.text[:800]}")
    data = r.json()
    if data.get("stop_reason") == "refusal":
        raise RuntimeError(f"Opus refusal: {data.get('stop_details')}")
    text = next((b["text"] for b in data.get("content", []) if b.get("type") == "text"), None)
    if not text:
        raise RuntimeError("Opus: no text block in response")
    return json.loads(text)
