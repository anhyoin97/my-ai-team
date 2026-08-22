# my-ai-team — 관심분야 정보 수집기

## 프로젝트 목적

여러 소스(RSS, 공개 API)에서 항목을 수집 → 공통 스키마로 정규화 → 중복 제거 →
키워드로 필터·점수화 → 주간 다이제스트(Markdown) 생성 → SQLite에 이력 축적.

이 저장소는 실제로 쓸 파이프라인인 동시에, Claude Code 멀티에이전트 워크플로
(Git Worktree 병렬 개발, Hooks 품질 게이트, Skills, Remote Control)를 연습하는
학습 프로젝트이기도 하다.

## 파이프라인 단계

1. **수집 (adapters)** — 소스별 어댑터가 원본 데이터를 가져와 `RawItem` 리스트로 반환
2. **정규화** — `RawItem` → `NormalizedItem` 공통 스키마로 변환
3. **중복 제거** — URL 정규화 + 제목 유사도 기반
4. **필터·점수화** — 키워드 매칭 기반 점수 부여, 임계값 미만 제외
5. **다이제스트 생성** — 주간 단위로 상위 항목을 Markdown 파일로 출력
6. **이력 축적** — SQLite에 모든 수집 항목과 다이제스트 발행 이력 저장 (중복 제거의 기준)

## 디렉터리 구조

src/collector/
models.py # 공통 스키마 (RawItem, NormalizedItem) — 이 파일은 함부로 변경 금지
adapters/
base.py # SourceAdapter 프로토콜 — 모든 어댑터가 구현해야 하는 계약
hackernews.py # 예: AI/개발 뉴스 소스 어댑터
google_news.py # 예: 키워드 뉴스 소스 어댑터
dedupe.py
scoring.py
digest.py
storage.py # SQLite 접근 계층
tests/
test_<모듈명>.py # 모듈당 1개 테스트 파일, 미러링 구조


## 어댑터 작성 규칙 (중요 — 병렬 개발의 기준)

- 새 어댑터는 `src/collector/adapters/<source_name>.py` 파일 하나로 완결
- 반드시 `base.py`의 `SourceAdapter` 프로토콜을 구현: `fetch() -> list[RawItem]`
- 다른 어댑터 파일을 import하지 않는다 (완전히 독립적 — 병렬 worktree 작업 전제조건)
- 외부 호출(HTTP)은 함수/메서드로 분리해 테스트에서 mock 가능하게 만든다
- 각 어댑터는 `tests/test_adapters_<source_name>.py`에 대응하는 테스트를 가져야 함
- 네트워크 요청은 테스트에서 절대 실제로 하지 않는다 (mock 필수 — 테스트 Skill 참고)

## 공통 스키마 변경 정책

`models.py`의 `RawItem`/`NormalizedItem`은 모든 어댑터가 공유하는 계약이다.
필드를 추가/변경해야 하면 어댑터 작업과 별도 PR로 분리하고, 모든 어댑터에
영향이 없는지 확인 후에만 병합한다.

## 개발 명령어

```bash
source .venv/bin/activate
pip install -e ".[dev]"

ruff check .          # 린트
ruff format .         # 포맷
mypy src              # 타입 체크
pytest                # 테스트
pytest --cov=collector  # 커버리지 포함 테스트
```

커밋 전에는 위 4개(ruff check, mypy, pytest)가 모두 통과해야 한다.
이는 `.claude/settings.json`의 Hooks로 강제된다 — 실패하면 커밋이 차단된다.

## 브랜치 / Worktree 규칙

- 어댑터별 병렬 개발 시 브랜치명: `adapter/<source_name>`
- Worktree 경로 관례: `../my-ai-team-worktrees/<source_name>`
- 각 어댑터 작업은 독립된 worktree + 서브에이전트에서 진행하고,
  완료 후 `main`으로 PR을 통해 병합한다 (직접 push 금지)

## 커밋 메시지 규칙

Conventional Commits 스타일 사용: `feat:`, `fix:`, `test:`, `refactor:`, `chore:`

## 테스트 작성 시 참고

테스트 작성 패턴(fixture, mock, parametrize 컨벤션)은
`.claude/skills/adapter-testing/SKILL.md`를 따른다.
