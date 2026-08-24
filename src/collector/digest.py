"""주간 다이제스트 Markdown 생성기."""
from __future__ import annotations

import os
from datetime import datetime

from collector.models import NormalizedItem

_SUMMARY_MAX_LENGTH = 120
_EMPTY_NOTICE = "이번 주는 새로운 항목이 없습니다."


def render_digest_markdown(
    items: list[NormalizedItem],
    generated_at: datetime,
    title: str = "주간 다이제스트",
) -> str:
    """items를 점수 내림차순(동점이면 최신순)으로 정렬해 Markdown으로 렌더링한다."""
    lines = [f"# {title}", "", f"생성일: {generated_at:%Y-%m-%d}", ""]

    if not items:
        lines.append(_EMPTY_NOTICE)
        return "\n".join(lines) + "\n"

    sorted_items = sorted(items, key=lambda item: (item.score, item.published_at), reverse=True)

    for index, item in enumerate(sorted_items, start=1):
        summary = item.summary[:_SUMMARY_MAX_LENGTH]
        lines.append(f"{index}. [{item.title}]({item.url}) — {item.source}")
        if summary:
            lines.append(f"   {summary}")

    return "\n".join(lines) + "\n"


def write_digest_file(markdown: str, output_dir: str, generated_at: datetime) -> str:
    """markdown을 generated_at 날짜 기반 파일명으로 output_dir에 저장하고 경로를 반환한다."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{generated_at:%Y-%m-%d}-digest.md"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return output_path
