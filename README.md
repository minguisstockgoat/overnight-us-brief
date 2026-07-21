# 전날 미장 시황 브리핑 (Overnight US Market Brief)

매 국장 영업일 아침, **전 영업일 NXT 종료(20:00 KST) ~ 당일 07:00 KST** 사이 텔레그램
아카이브의 **미국 증시·글로벌 매크로** 뉴스를 수집·요약·큐레이션해 시계열·주제별로 보여주는
정적 대시보드. 통합 허브(https://minguisstockgoat.github.io/)에 연결.

**라이브:** https://minguisstockgoat.github.io/overnight-us-brief/

## 파이프라인

```
창 계산(krx_calendar) → 아카이브 수집(archive) → 채널 1차필터
   → Gemini 1차 요약(gemini) → Opus 4.8 큐레이션(opus) → data.json → 프런트(index.html)
```

- **데이터 소스**: Mac mini SQLite 아카이브를 감싸는 HTTP MCP 서버(`search_telegram_messages`).
- **Gemini**(`gemini-2.5-flash`): 밤사이 메시지를 정규화 항목으로 요약·1차 선별(httpx REST 직접 호출).
- **Opus 4.8**(`claude-opus-4-8`): 미장/매크로만 남기고 주제 클러스터·시계열·중요도(핵심/주요/참고)·headline 생성.
- 발송 없음 — 대시보드만 갱신.

## 로컬 실행 (Windows 개발, `py` 런처)

```bash
py -m pip install -r requirements.txt
# .env 준비 후:
py scripts/pipeline.py --date 2026-07-22
# 키를 다른 .env에서 끌어오려면:
py scripts/pipeline.py --env-file "..\\..\\와이즈리포트봇\\.env"
```

`data.json` 이 생성되면 `py -m http.server` 로 `index.html` 을 열어 확인.

## 운영 배포 (Mac mini, launchd)

아카이브가 있는 Mac mini에서 실행하므로 네트워크 이슈가 없습니다.

1. **clone & 의존성**
   ```bash
   git clone https://github.com/minguisstockgoat/overnight-us-brief.git
   cd overnight-us-brief
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **키 배치**: `.env.example` → `.env` 복사 후 `ARCHIVE_TOKEN` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` 입력.
   (`.env` 는 커밋되지 않음.)
3. **git push 인증**: `gh auth login` 또는 SSH deploy key 설정(토큰 하드코딩 금지).
   `scripts/run.sh` 가 `git push` 로 Pages 를 갱신합니다.
4. **수동 1회 테스트**: `bash scripts/run.sh` → `data.json` 갱신·커밋·푸시 확인, `brief.log` 점검.
5. **스케줄 등록**:
   ```bash
   # plist 안의 REPO_PATH 3곳을 실제 경로로 치환
   sed -i '' "s#REPO_PATH#$(pwd)#g" com.minguis.overnightbrief.plist
   cp com.minguis.overnightbrief.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.minguis.overnightbrief.plist
   ```
   평일 07:10(Mac 시간대 기준)에 실행됩니다. Mac 시간대가 KST 여야 합니다.
   슬립 상태였다면 wake 직후 실행됩니다.

## GitHub Pages

- Source = `main` / `root`. 빌드 없는 정적 사이트 → `data.json` push 시 ~1분 내 반영.
- 프런트는 로드 시 `data.json` 을 fetch(캐시 무력화 쿼리 포함).

## 유지보수 메모

- **KRX 휴장일은 `scripts/krx_calendar.py` 에 하드코딩** → 매년 갱신 필요. 휴장일엔 `status:"휴장"` 만 기록.
- **일본 뉴스 등 아시아**는 참고로 포함될 수 있으나 초점은 미장·글로벌 매크로.
- 국장 전용 채널(급등/신고가/공시)은 `config.CHANNEL_DENY_KEYWORDS` 로 1차 제외 + Opus 최종 필터.
- 모델은 `.env` 의 `GEMINI_MODEL` / `OPUS_MODEL` 로 교체 가능.
- 아카이브 응답 상한(200건)은 `archive.py` 가 시간분할로 자동 전량 수집.
