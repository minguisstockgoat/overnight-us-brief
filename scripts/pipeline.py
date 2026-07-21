"""전날 미장 시황 브리핑 파이프라인.

창 계산 → 아카이브 수집 → 채널 1차필터 → Gemini 요약 → Opus 큐레이션 → data.json.

사용:
  py scripts/pipeline.py                 # 오늘(KST) 기준
  py scripts/pipeline.py --date 2026-07-22
  py scripts/pipeline.py --env-file ../../와이즈리포트봇/.env   # 개발용 키 로드
"""
import argparse
import json
import os
import sys
from datetime import datetime, date, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import config
import krx_calendar as cal
import archive
import gemini
import opus

KST = timezone(timedelta(hours=9))


def run(run_date: date, out_path: str):
    win = cal.window_for(run_date)
    generated = datetime.now(timezone.utc).astimezone(KST).isoformat()

    base = {
        "generatedAt": generated,
        "window": {
            "startKst": win["start_kst"].isoformat(),
            "endKst": win["end_kst"].isoformat(),
            "prevTradingDay": win["prev_trading_day"],
        },
    }

    if not win["is_trading_day"]:
        out = {**base, "status": "휴장", "headline": [], "topics": []}
        _write(out, out_path)
        print(f"[skip] {run_date} 는 거래일 아님(휴장) — status만 기록")
        return out

    print(f"[1/4] 수집: {win['start_utc']} ~ {win['end_utc']} (UTC)")
    msgs = archive.fetch_window(win["start_utc"], win["end_utc"])
    print(f"      수집 {len(msgs)}건")

    kept = [m for m in msgs if not config.is_denied_channel(m.get("chat_name", ""))]
    print(f"[2/4] 채널 1차필터 후 {len(kept)}건 → Gemini 요약")
    items = gemini.summarize(kept)
    print(f"      Gemini 관련 항목 {len(items)}건")

    if not items:
        out = {**base, "status": "ok", "headline": ["밤사이 주요 미장·매크로 뉴스가 확인되지 않았습니다."], "topics": []}
        _write(out, out_path)
        return out

    print(f"[3/4] Opus 큐레이션({config.OPUS_MODEL()})")
    curated = opus.curate(items, win)

    out = {
        **base,
        "status": "ok",
        "headline": curated.get("headline", []),
        "topics": curated.get("topics", []),
        "stats": {"collected": len(msgs), "afterFilter": len(kept), "geminiItems": len(items)},
    }
    print(f"[4/4] 기록: 주제 {len(out['topics'])}개, 헤드라인 {len(out['headline'])}개")
    _write(out, out_path)
    return out


def _write(out, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"      → {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (KST 실행일). 미지정 시 오늘.")
    ap.add_argument("--out", default=os.path.join(ROOT, "data.json"))
    ap.add_argument("--env-file", action="append", default=[], help="추가 .env 경로(개발용)")
    args = ap.parse_args()

    # .env 로드: repo/.env + 추가 지정
    config.load_env(os.path.join(ROOT, ".env"), *args.env_file)

    if args.date:
        rd = date.fromisoformat(args.date)
    else:
        rd = datetime.now(KST).date()

    # 필수 키 확인
    missing = [k for k, v in {
        "ARCHIVE_TOKEN": config.ARCHIVE_TOKEN(),
        "GEMINI_API_KEY": config.GEMINI_API_KEY(),
        "ANTHROPIC_API_KEY": config.ANTHROPIC_API_KEY(),
    }.items() if not v]
    if missing:
        print(f"[에러] 누락된 키: {', '.join(missing)} (.env 확인)", file=sys.stderr)
        sys.exit(2)

    run(rd, args.out)


if __name__ == "__main__":
    main()
