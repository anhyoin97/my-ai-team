"""공통 스키마: 모든 어댑터가 반환/생산하는 데이터 형태.

이 파일은 모든 어댑터가 공유하는 계약이므로 CLAUDE.md의 변경 정책을 따를 것.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RawItem(BaseModel):
    """어댑터가 소스에서 가져온 원본 항목. 정규화 이전 상태."""

    source: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    raw: dict[str, object] = Field(default_factory=dict)


class NormalizedItem(BaseModel):
    """정규화된 항목. 중복 제거·점수화·다이제스트는 이 타입만 다룬다."""

    id: str
    source: str
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    keywords_matched: list[str] = Field(default_factory=list)
    score: float = 0.0

    @classmethod
    def from_raw(cls, raw: RawItem) -> NormalizedItem:
        published = raw.published_at or datetime.now(timezone.utc)
        return cls(
            id=compute_item_id(raw.url),
            source=raw.source,
            title=raw.title.strip(),
            url=raw.url,
            published_at=published,
            summary=(raw.summary or "").strip(),
        )


def compute_item_id(url: str) -> str:
    """URL을 정규화해 중복 제거용 안정적인 id를 생성한다."""
    normalized = url.strip().rstrip("/").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
