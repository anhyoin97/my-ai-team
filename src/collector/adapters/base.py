"""모든 소스 어댑터가 구현해야 하는 인터페이스."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from collector.models import RawItem


@runtime_checkable
class SourceAdapter(Protocol):
    """소스 하나에서 원본 항목을 가져오는 어댑터의 계약.

    구현 규칙 (CLAUDE.md 참고):
    - 다른 어댑터 모듈을 import하지 않는다.
    - 네트워크 호출은 별도 메서드로 분리해 테스트에서 mock 가능하게 한다.
    - 실패 시 예외를 삼키지 말고 그대로 전파한다.
    """

    name: str

    def fetch(self) -> list[RawItem]:
        """소스에서 원본 항목 리스트를 가져온다."""
        ...
