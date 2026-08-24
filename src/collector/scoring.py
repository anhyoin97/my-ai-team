"""키워드 기반 점수화: 제목/요약에서 매칭된 키워드 수를 점수로 부여한다."""
from __future__ import annotations

from collector.models import NormalizedItem


def score_items(
    items: list[NormalizedItem],
    keywords: list[str],
    threshold: float = 1.0,
) -> list[NormalizedItem]:
    """각 항목의 title+summary에서 keywords를 매칭해 점수를 매기고,
    threshold 미만인 항목은 제외한 새 NormalizedItem 리스트를 반환한다.
    """
    scored: list[NormalizedItem] = []
    for item in items:
        haystack = f"{item.title} {item.summary}".lower()
        matched = [kw for kw in keywords if kw.lower() in haystack]
        score = float(len(matched))
        if score < threshold:
            continue
        scored.append(item.model_copy(update={"keywords_matched": matched, "score": score}))
    return scored
