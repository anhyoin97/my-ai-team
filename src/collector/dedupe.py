"""중복 제거: id 기준으로 이미 본 항목과 배치 내 중복을 제외한다."""
from __future__ import annotations

from collector.models import NormalizedItem


def deduplicate(
    items: list[NormalizedItem], seen_ids: set[str] | None = None
) -> list[NormalizedItem]:
    """seen_ids에 없고 배치 내에서 처음 등장한 항목만 순서대로 반환한다."""
    seen = set(seen_ids) if seen_ids else set()
    result: list[NormalizedItem] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        result.append(item)
    return result
