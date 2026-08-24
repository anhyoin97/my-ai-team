
# 가상 에이전트 오피스 — 확장 로드맵

## 현재 구조 (2026-08)
`status.json` 스키마:

```json
{
  "<agent_id>": {
    "status": "idle | thinking | working | offline | unknown",
    "detail": "사람이 읽는 현재 작업 설명",
    "updated_at": "ISO8601 타임스탬프"
  }
}
```

**이 스키마는 앞으로도 안정적으로 유지한다.** 프론트엔드(카드 → 픽셀 캔버스)를 바꿔도
백엔드(훅, status.json)는 그대로 재사용 가능해야 하기 때문.

## 다음 단계로 가는 확장 지점

1. **캐릭터 좌표/방 배치**
   agent_id별로 고정된 (x, y) 좌표와 "책상" 스프라이트를 매핑하는 `layout.json`을
   status.json과 별도로 둔다. 에이전트가 늘어나면 여기에 좌표만 추가.

2. **status → 스프라이트 애니메이션 매핑**
   - `idle` → 캐릭터가 의자에 앉아 있는 정지 프레임
   - `thinking` → 머리 위에 "..." 말풍선 + 미세한 흔들림 애니메이션
   - `working` → 키보드 타이핑 스프라이트 루프, `detail`에 도구 이름 표시
   - `offline` → 캐릭터 자리 비움 (반투명 또는 의자만)
   - `unknown`/에러 상황 → 캐릭터 위에 물음표/경고 아이콘

3. **렌더링 방식**
   `dashboard.html`의 카드 grid를 `<canvas>` 또는 `<div>` 절대좌표 배치로 교체.
   폴링 로직(`fetch("status.json")`)은 그대로 두고 렌더링 함수만 교체하면 됨
   (`refresh()` 안의 DOM 조작 부분만 스프라이트 그리기로 바꾸는 구조).

4. **더 세밀한 이벤트**
   지금은 5개 훅 이벤트만 쓰지만, `PostToolUse`(도구 실행 결과: 성공/실패)를 추가하면
   "막힘" 상태(빨간 경고, 테스트 실패 등)를 구분해서 표시할 수 있음.

5. **다중 프로젝트 지원**
   지금은 `~/.my-ai-team-office/status.json` 하나뿐이라 이 프로젝트 전용.
   여러 프로젝트를 한 오피스에 보이게 하려면 status.json에 `project` 필드를 추가하고
   대시보드에서 프로젝트별로 방을 나누면 됨.

## 참고

- 훅 스크립트: `.claude/hooks/report-status.sh`, `.claude/hooks/report_status.py`
- 대시보드: `~/.my-ai-team-office/dashboard.html` (저장소 밖, 로컬 전용 — 여러 프로젝트가
  공유하는 대시보드라서 저장소에 커밋하지 않음)
