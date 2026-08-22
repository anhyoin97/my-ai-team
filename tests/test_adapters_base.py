from collector.adapters.base import SourceAdapter
from collector.models import RawItem


class DummyAdapter:
    name = "dummy"

    def fetch(self) -> list[RawItem]:
        return [RawItem(source=self.name, title="t", url="https://example.com")]


def test_dummy_adapter_satisfies_protocol():
    adapter = DummyAdapter()
    assert isinstance(adapter, SourceAdapter)


def test_fetch_returns_raw_items():
    items = DummyAdapter().fetch()
    assert len(items) == 1
    assert items[0].source == "dummy"
