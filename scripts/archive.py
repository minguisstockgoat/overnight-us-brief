"""Mac mini 텔레그램 아카이브 HTTP MCP 클라이언트.

search_telegram_messages(query, chat, since, until, limit) 를 호출.
- 결과는 최신순 UTC, 한 응답 최대 200건 → 창을 시간분할 재귀로 전량 수집 후 dedup.
"""
import json
from datetime import datetime, timezone
import httpx
import config

CAP = 200            # 서버 응답 상한(관측값)
MIN_SLICE_SEC = 120  # 이보다 짧은 창은 더 쪼개지 않음

def _call(args, timeout=60):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "search_telegram_messages", "arguments": args}}
    headers = {
        "Authorization": f"Bearer {config.ARCHIVE_TOKEN()}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    r = httpx.post(config.ARCHIVE_URL(), json=body, headers=headers,
                   timeout=httpx.Timeout(timeout, connect=10.0))
    r.raise_for_status()
    obj = r.json()
    if "error" in obj:
        raise RuntimeError(f"archive MCP error: {obj['error']}")
    text = obj["result"]["content"][0]["text"]
    return json.loads(text)

def _query(since_iso, until_iso, limit=CAP):
    d = _call({"query": "", "since": since_iso, "until": until_iso, "limit": limit})
    return d.get("results", [])

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def fetch_window(start_utc: datetime, end_utc: datetime):
    """[start, end) 창의 전체 메시지를 시간분할로 빠짐없이 수집(dedup)."""
    seen = {}

    def recurse(a: datetime, b: datetime):
        res = _query(_iso(a), _iso(b))
        # 클라이언트측 경계 필터([a, b)) + dedup
        for m in res:
            try:
                dt = datetime.fromisoformat(m["date"])
            except Exception:
                continue
            if a <= dt < b:
                seen[(m["chat_id"], m["message_id"])] = m
        # 상한에 걸렸고 더 쪼갤 수 있으면 분할
        if len(res) >= CAP and (b - a).total_seconds() > MIN_SLICE_SEC:
            mid = a + (b - a) / 2
            recurse(a, mid)
            recurse(mid, b)

    recurse(start_utc, end_utc)
    msgs = list(seen.values())
    msgs.sort(key=lambda m: m["date"])  # 오래된→최신 (시계열)
    return msgs
