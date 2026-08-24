import pytest
from pydantic import ValidationError

from collector.config import AppConfig, load_config

VALID_CONFIG_YAML = """
sources:
  hackernews:
    enabled: true
    feed_url: "https://hnrss.org/frontpage"
  google_news:
    enabled: true
    keywords:
      - "Claude"
      - "AI"

scoring:
  keywords:
    - "Claude"
    - "AI"
  threshold: 1.0

digest:
  output_dir: "output/digests"
  title: "주간 다이제스트"

storage:
  db_path: "data/history.db"
"""


def write_config(tmp_path, content: str) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_load_config_parses_valid_yaml(tmp_path):
    path = write_config(tmp_path, VALID_CONFIG_YAML)

    config = load_config(path)

    assert config.sources.hackernews.enabled is True
    assert config.sources.hackernews.feed_url == "https://hnrss.org/frontpage"
    assert config.sources.google_news.keywords == ["Claude", "AI"]
    assert config.scoring.keywords == ["Claude", "AI"]
    assert config.scoring.threshold == 1.0
    assert config.digest.output_dir == "output/digests"
    assert config.digest.title == "주간 다이제스트"
    assert config.storage.db_path == "data/history.db"


def test_load_config_raises_on_missing_required_field(tmp_path):
    missing_feed_url = """
sources:
  hackernews:
    enabled: true
  google_news:
    enabled: true
    keywords: ["AI"]
scoring:
  keywords: ["AI"]
  threshold: 1.0
digest:
  output_dir: "output/digests"
  title: "주간 다이제스트"
storage:
  db_path: "data/history.db"
"""
    path = write_config(tmp_path, missing_feed_url)

    with pytest.raises(ValidationError):
        load_config(path)


def test_load_config_raises_on_missing_top_level_section(tmp_path):
    missing_storage_section = """
sources:
  hackernews:
    enabled: true
    feed_url: "https://hnrss.org/frontpage"
  google_news:
    enabled: false
    keywords: []
scoring:
  keywords: []
  threshold: 1.0
digest:
  output_dir: "output/digests"
  title: "주간 다이제스트"
"""
    path = write_config(tmp_path, missing_storage_section)

    with pytest.raises(ValidationError):
        load_config(path)


def test_load_config_rejects_wrong_type_for_threshold(tmp_path):
    wrong_type_threshold = """
sources:
  hackernews:
    enabled: true
    feed_url: "https://hnrss.org/frontpage"
  google_news:
    enabled: true
    keywords: ["AI"]
scoring:
  keywords: ["AI"]
  threshold: "not-a-number"
digest:
  output_dir: "output/digests"
  title: "주간 다이제스트"
storage:
  db_path: "data/history.db"
"""
    path = write_config(tmp_path, wrong_type_threshold)

    with pytest.raises(ValidationError):
        load_config(path)


def test_app_config_can_be_constructed_directly_with_google_news_disabled():
    config = AppConfig.model_validate(
        {
            "sources": {
                "hackernews": {"enabled": False, "feed_url": "https://example.com/feed"},
                "google_news": {"enabled": False, "keywords": []},
            },
            "scoring": {"keywords": [], "threshold": 1.0},
            "digest": {"output_dir": "output/digests", "title": "제목"},
            "storage": {"db_path": "data/history.db"},
        }
    )

    assert config.sources.hackernews.enabled is False
    assert config.sources.google_news.keywords == []
