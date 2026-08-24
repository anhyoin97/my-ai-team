"""엔드투엔드 파이프라인 실행 스크립트.

수집(HackerNews, GoogleNews) → 정규화 → 중복 제거 → 점수화 → 다이제스트 생성 → 이력 저장.

실행: python scripts/run_pipeline.py [키워드]
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from collector import dedupe, digest, scoring, storage
from collector.adapters.base import SourceAdapter
from collector.adapters.google_news import GoogleNewsAdapter
from collector.adapters.hackernews import HackerNewsAdapter
from collector.models import NormalizedItem, RawItem

DB_PATH = "data/history.db"
OUTPUT_DIR = "output/digests"
SCORING_KEYWORDS = ["AI", "LLM", "인공지능"]
SCORING_THRESHOLD = 1.0


def run(keyword: str) -> str:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    storage.init_db(DB_PATH)

    adapters: list[SourceAdapter] = [HackerNewsAdapter(), GoogleNewsAdapter(keyword)]
    raw_items: list[RawItem] = []
    for adapter in adapters:
        fetched = adapter.fetch()
        print(f"수집 ({adapter.name}): {len(fetched)}건")
        raw_items.extend(fetched)
    print(f"수집 합계: {len(raw_items)}건")

    normalized_items = [NormalizedItem.from_raw(raw) for raw in raw_items]
    print(f"정규화: {len(normalized_items)}건")

    seen_ids = storage.get_seen_ids(DB_PATH)
    deduped_items = dedupe.deduplicate(normalized_items, seen_ids)
    print(f"중복 제거 후: {len(deduped_items)}건")

    scored_items = scoring.score_items(deduped_items, SCORING_KEYWORDS, SCORING_THRESHOLD)
    print(f"점수화 통과: {len(scored_items)}건")

    generated_at = datetime.now(timezone.utc)
    markdown = digest.render_digest_markdown(scored_items, generated_at)
    output_path = digest.write_digest_file(markdown, OUTPUT_DIR, generated_at)
    print(f"다이제스트 파일: {output_path}")

    storage.save_items(DB_PATH, normalized_items)
    storage.record_digest(DB_PATH, scored_items, output_path, generated_at)

    return output_path


if __name__ == "__main__":
    keyword_arg = sys.argv[1] if len(sys.argv) > 1 else "AI"
    run(keyword_arg)
