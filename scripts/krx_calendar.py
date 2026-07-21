"""KR 거래일/휴장일 + 밤사이 창(window) 계산. KST=UTC+9.

전 영업일 NXT 종료(20:00 KST) ~ 당일 07:00 KST 구간을 UTC로 변환해 반환.
⚠ KRX 휴장일은 아래 하드코딩. 매년 갱신 필요(README 참고).
"""
from datetime import datetime, date, timedelta, timezone

KST = timezone(timedelta(hours=9))
UTC = timezone.utc

# KRX 휴장일(주말 외). best-effort — 매년 검증/갱신 필요.
KRX_HOLIDAYS = {
    # 2026
    "2026-01-01",
    "2026-02-16", "2026-02-17", "2026-02-18",  # 설날
    "2026-03-02",                               # 3·1절 대체(3/1 일)
    "2026-05-01",                               # 근로자의 날(증시 휴장)
    "2026-05-05",                               # 어린이날
    "2026-05-25",                               # 석가탄신일 대체(5/24 일)
    "2026-08-17",                               # 광복절 대체(8/15 토) — 검증 요
    "2026-09-24", "2026-09-25",                 # 추석(9/26 토)
    "2026-10-05",                               # 개천절 대체(10/3 토) — 검증 요
    "2026-10-09",                               # 한글날
    "2026-12-25",                               # 성탄절
    "2026-12-31",                               # 연말 폐장
    # 2027 (일부) — 갱신 필요
    "2027-01-01",
}

def is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:  # 토(5)/일(6)
        return False
    return d.isoformat() not in KRX_HOLIDAYS

def prev_trading_day(d: date) -> date:
    p = d - timedelta(days=1)
    while not is_trading_day(p):
        p -= timedelta(days=1)
    return p

def window_for(run_date: date):
    """run_date(KST 당일)의 밤사이 창을 반환.
    returns dict: start_kst, end_kst, start_utc, end_utc, prev_trading_day, is_trading_day
    """
    prev = prev_trading_day(run_date)
    start_kst = datetime(prev.year, prev.month, prev.day, 20, 0, tzinfo=KST)   # 전 영업일 20:00 (NXT 종료)
    end_kst = datetime(run_date.year, run_date.month, run_date.day, 7, 0, tzinfo=KST)  # 당일 07:00
    return {
        "start_kst": start_kst,
        "end_kst": end_kst,
        "start_utc": start_kst.astimezone(UTC),
        "end_utc": end_kst.astimezone(UTC),
        "prev_trading_day": prev.isoformat(),
        "is_trading_day": is_trading_day(run_date),
    }

def to_kst_iso(utc_iso: str) -> str:
    """아카이브의 UTC ISO(예 2026-07-21T12:55:44+00:00)를 KST ISO로."""
    try:
        dt = datetime.fromisoformat(utc_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(KST).isoformat()
    except Exception:
        return utc_iso
