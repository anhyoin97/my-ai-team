"""config.yaml 로딩 및 검증."""
from __future__ import annotations

import yaml
from pydantic import BaseModel


class HackerNewsSourceConfig(BaseModel):
    enabled: bool
    feed_url: str


class GoogleNewsSourceConfig(BaseModel):
    enabled: bool
    keywords: list[str]


class SourcesConfig(BaseModel):
    hackernews: HackerNewsSourceConfig
    google_news: GoogleNewsSourceConfig


class ScoringConfig(BaseModel):
    keywords: list[str]
    threshold: float


class DigestConfig(BaseModel):
    output_dir: str
    title: str


class StorageConfig(BaseModel):
    db_path: str


class AppConfig(BaseModel):
    sources: SourcesConfig
    scoring: ScoringConfig
    digest: DigestConfig
    storage: StorageConfig


def load_config(path: str) -> AppConfig:
    """path의 YAML 파일을 읽어 검증된 AppConfig를 반환한다."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)
