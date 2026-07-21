"""공통 설정 + .env 로더 (외부 의존성 최소화)."""
import os

def load_env(*paths):
    """단순 KEY=VALUE .env 파서. 이미 os.environ에 있으면 덮어쓰지 않음."""
    for p in paths:
        if not p or not os.path.isfile(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)

# 아카이브(Mac mini HTTP MCP)
ARCHIVE_URL = lambda: os.environ.get("ARCHIVE_URL", "https://macmini.taila0cca3.ts.net/")
ARCHIVE_TOKEN = lambda: os.environ.get("ARCHIVE_TOKEN", "")

# 모델
GEMINI_MODEL = lambda: os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = lambda: os.environ.get("GEMINI_API_KEY", "")
OPUS_MODEL = lambda: os.environ.get("OPUS_MODEL", "claude-opus-4-8")
ANTHROPIC_API_KEY = lambda: os.environ.get("ANTHROPIC_API_KEY", "")

# 국장 개별종목/공시 위주 채널 — 1차 제외(부분일치). 미장·매크로 최종 판단은 Opus가 함.
CHANNEL_DENY_KEYWORDS = ["급등", "신고가", "AWAKE", "해피엔딩"]

def is_denied_channel(name: str) -> bool:
    name = name or ""
    return any(kw in name for kw in CHANNEL_DENY_KEYWORDS)
