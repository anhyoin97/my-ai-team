"""엔드투엔드 파이프라인 실행 스크립트.

수집(HackerNews, GoogleNews) → 정규화 → 중복 제거 → 점수화 → 다이제스트 생성 → 이력 저장.
소스/키워드 등 설정은 config.yaml에서 읽는다.
단계별 진행 상황은 ~/.my-ai-team-office/status.json에 agent_id "pipeline"으로 기록한다.

실행: python scripts/run_pipeline.py [config 경로]
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from collector import dedupe, digest, scoring, storage, thumbnail
from collector.adapters.base import SourceAdapter
from collector.adapters.google_news import GoogleNewsAdapter
from collector.adapters.hackernews import HackerNewsAdapter
from collector.config import AppConfig, load_config
from collector.models import NormalizedItem, RawItem

_HOOKS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from status_store import write_status  # noqa: E402

DEFAULT_CONFIG_PATH = "config.yaml"
STATUS_FILE = os.path.expanduser("~/.my-ai-team-office/status.json")
AGENT_ID = "pipeline"


def _report(status: str, detail: str) -> None:
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    write_status(STATUS_FILE, AGENT_ID, status, detail)


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
    try:
        _report("working", "파이프라인 시작")

        db_path = config.storage.db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        storage.init_db(db_path)

        raw_items: list[RawItem] = []
        _report("working", "수집 중")
        for adapter in build_adapters(config):
            fetched = adapter.fetch()
            print(f"수집 ({adapter.name}): {len(fetched)}건")
            raw_items.extend(fetched)
        print(f"수집 합계: {len(raw_items)}건")
        _report("working", f"수집 완료: {len(raw_items)}건")

        normalized_items = [NormalizedItem.from_raw(raw) for raw in raw_items]
        print(f"정규화: {len(normalized_items)}건")
        _report("working", f"정규화 완료: {len(normalized_items)}건")

        seen_ids = storage.get_seen_ids(db_path)
        deduped_items = dedupe.deduplicate(normalized_items, seen_ids)
        print(f"중복 제거 후: {len(deduped_items)}건")
        _report("working", f"중복 제거 완료: {len(deduped_items)}건")

        scored_items = scoring.score_items(
            deduped_items, config.scoring.keywords, config.scoring.threshold
        )
        print(f"점수화 통과: {len(scored_items)}건")
        _report("working", f"점수화 완료: {len(scored_items)}건")

        _report("working", "썸네일 조회 중")
        scored_items = [
            item.model_copy(update={"thumbnail_url": thumbnail.fetch_thumbnail_url(item.url)})
            for item in scored_items
        ]
        _report("working", "썸네일 조회 완료")

        generated_at = datetime.now(timezone.utc)
        markdown = digest.render_digest_markdown(scored_items, generated_at, config.digest.title)
        output_path = digest.write_digest_file(markdown, config.digest.output_dir, generated_at)
        print(f"다이제스트 파일: {output_path}")

        storage.save_items(db_path, normalized_items)
        storage.record_digest(db_path, scored_items, output_path, generated_at)

        _report("idle", f"수집 {len(raw_items)}건 → 다이제스트 {output_path} 생성 완료")
        return output_path
    except Exception as e:
        _report("error", f"실패: {e}")
        raise


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    run(load_config(config_path))
