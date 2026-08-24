"""엔드투엔드 파이프라인 실행 스크립트.

수집(HackerNews, GoogleNews) → 정규화 → 중복 제거 → 점수화 → 다이제스트 생성 → 이력 저장.
소스/키워드 등 설정은 config.yaml에서 읽는다.

실행: python scripts/run_pipeline.py [config 경로]
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from collector import dedupe, digest, scoring, storage
from collector.adapters.base import SourceAdapter
from collector.adapters.google_news import GoogleNewsAdapter
from collector.adapters.hackernews import HackerNewsAdapter
from collector.config import AppConfig, load_config
from collector.models import NormalizedItem, RawItem

DEFAULT_CONFIG_PATH = "config.yaml"


def build_adapters(config: AppConfig) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = []
    if config.sources.hackernews.enabled:
        adapters.append(HackerNewsAdapter(config.sources.hackernews.feed_url))
    if config.sources.google_news.enabled:
        adapters.extend(
            GoogleNewsAdapter(keyword) for keyword in config.sources.google_news.keywords
        )
    return adapters


def run(config: AppConfig) -> str:
    db_path = config.storage.db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    storage.init_db(db_path)

    raw_items: list[RawItem] = []
    for adapter in build_adapters(config):
        fetched = adapter.fetch()
        print(f"수집 ({adapter.name}): {len(fetched)}건")
        raw_items.extend(fetched)
    print(f"수집 합계: {len(raw_items)}건")

    normalized_items = [NormalizedItem.from_raw(raw) for raw in raw_items]
    print(f"정규화: {len(normalized_items)}건")

    seen_ids = storage.get_seen_ids(db_path)
    deduped_items = dedupe.deduplicate(normalized_items, seen_ids)
    print(f"중복 제거 후: {len(deduped_items)}건")

    scored_items = scoring.score_items(
        deduped_items, config.scoring.keywords, config.scoring.threshold
    )
    print(f"점수화 통과: {len(scored_items)}건")

    generated_at = datetime.now(timezone.utc)
    markdown = digest.render_digest_markdown(scored_items, generated_at, config.digest.title)
    output_path = digest.write_digest_file(markdown, config.digest.output_dir, generated_at)
    print(f"다이제스트 파일: {output_path}")

    storage.save_items(db_path, normalized_items)
    storage.record_digest(db_path, scored_items, output_path, generated_at)

    return output_path


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    run(load_config(config_path))
