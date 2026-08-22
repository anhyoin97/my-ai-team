---
name: adapter-testing
description: 새 소스 어댑터(RSS/API)의 pytest 테스트를 작성하거나 리뷰할 때 사용하는 표준 패턴. 어댑터 코드를 만들거나 수정할 때 이 스킬을 따른다.
---

# 어댑터 테스트 작성 패턴

## 원칙

1. **네트워크 호출은 절대 실제로 하지 않는다.** 모든 외부 호출은 mock 처리.
2. **고정된 샘플 응답(fixture)으로 테스트한다.** 실제 API/RSS 응답을 저장해두고 재사용.
3. **최소 3가지 케이스를 다룬다**: 정상 응답, 빈 응답, 일부 항목이 깨진/불완전한 응답.
4. **파일명 규칙**: `tests/test_adapters_<source_name>.py`
5. **fixture 위치**: `tests/fixtures/<source_name>/` 아래에 원본 샘플 저장 (예: `sample_feed.xml`, `sample_response.json`)

## 어댑터 구조 전제

어댑터는 네트워크 호출 부분을 별도 메서드로 분리해야 mock이 쉬워진다:

```python
# src/collector/adapters/example_source.py
import httpx

from collector.adapters.base import SourceAdapter
from collector.models import RawItem


class ExampleSourceAdapter:
    name = "example_source"

    def __init__(self, url: str = "https://example.com/feed") -> None:
        self.url = url

    def _fetch_raw_response(self) -> str:
        """실제 네트워크 호출. 테스트에서는 이 메서드만 mock한다."""
        response = httpx.get(self.url, timeout=10)
        response.raise_for_status()
        return response.text

    def fetch(self) -> list[RawItem]:
        text = self._fetch_raw_response()
        return self._parse(text)

    def _parse(self, text: str) -> list[RawItem]:
        # 파싱 로직 (순수 함수에 가깝게 — 이 부분이 테스트의 핵심 대상)
        ...
```

`_fetch_raw_response`만 mock하면 `_parse` 로직은 그대로 실제 파싱 코드가 실행되어
"파싱 로직이 진짜로 맞는지"를 검증할 수 있다.

## 테스트 템플릿

```python
# tests/test_adapters_example_source.py
from pathlib import Path
from unittest.mock import patch

import pytest

from collector.adapters.example_source import ExampleSourceAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "example_source"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestExampleSourceAdapter:
    def test_fetch_returns_expected_items_from_sample_response(self) -> None:
        adapter = ExampleSourceAdapter()
        with patch.object(
            adapter, "_fetch_raw_response", return_value=load_fixture("sample_response.json")
        ):
            items = adapter.fetch()

        assert len(items) == 2
        assert items[0].source == "example_source"
        assert items[0].title  # 빈 문자열이 아님
        assert items[0].url.startswith("http")

    def test_fetch_returns_empty_list_for_empty_response(self) -> None:
        adapter = ExampleSourceAdapter()
        with patch.object(adapter, "_fetch_raw_response", return_value="[]"):
            items = adapter.fetch()

        assert items == []

    def test_fetch_skips_malformed_entries_without_crashing(self) -> None:
        adapter = ExampleSourceAdapter()
        with patch.object(
            adapter, "_fetch_raw_response", return_value=load_fixture("sample_response_partial_broken.json")
        ):
            items = adapter.fetch()

        # 깨진 항목 하나는 건너뛰고, 나머지는 정상 반환되어야 한다
        assert len(items) >= 1

    @pytest.mark.parametrize("status_code", [404, 500, 503])
    def test_fetch_propagates_http_errors(self, status_code: int) -> None:
        # 실제 httpx 예외 전파는 _fetch_raw_response 자체 테스트에서 별도로 다룬다.
        pass
```

## 체크리스트 (PR 만들기 전 확인)

- [ ] `_fetch_raw_response`(또는 동등한 네트워크 호출부)를 mock했다 (실제 HTTP 요청 없음)
- [ ] 정상/빈/일부깨짐 3가지 케이스를 테스트했다
- [ ] fixture 파일을 `tests/fixtures/<source_name>/`에 저장했다
- [ ] `pytest`, `ruff check .`, `mypy src` 모두 통과했다
- [ ] 반환된 `RawItem`의 `source` 필드가 어댑터의 `name`과 일치하는지 확인했다
