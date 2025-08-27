# tests/test_tools/test_search.py
import pytest

# Import the module to patch its TavilyClient symbol
import Hakken.integrations.search as search_mod
from Hakken.integrations.search import internet_search, TavilyIntegration


class FakeTavilyClient:
    """Fake Tavily client for unit tests."""
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.calls = []

    def search(self, *, query, max_results=5, topic="general",
               include_raw_content=False, include_domains=None, exclude_domains=None):
        self.calls.append({
            "query": query,
            "max_results": max_results,
            "topic": topic,
            "include_raw_content": include_raw_content,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
        })
        # Minimal realistic payload
        return {
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example.com/1",
                    "content": "Content 1",
                    "score": 0.9,
                    "published_date": "2024-01-01",
                },
                {
                    "title": "Result 2",
                    "url": "https://example.com/2",
                    "content": "Content 2",
                    "score": 0.8,
                },
            ]
        }


@pytest.fixture(autouse=True)
def patch_tavily_and_env(monkeypatch):
    # Ensure API key exists for tests that expect successful init
    monkeypatch.setenv("TAVILY_API_KEY", "test_api_key")
    # Patch the TavilyClient symbol used by the module
    monkeypatch.setattr(search_mod, "TavilyClient", FakeTavilyClient)
    yield
    # teardown handled by monkeypatch


def test_init_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "abc123")
    monkeypatch.setattr(search_mod, "TavilyClient", FakeTavilyClient)

    integ = TavilyIntegration()
    assert isinstance(integ.client, FakeTavilyClient)
    assert integ.api_key == "abc123"
    assert integ.client.api_key == "abc123"


def test_init_raises_without_api_key(monkeypatch):
    # Remove key to trigger error path
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ValueError) as exc:
        TavilyIntegration()
    assert "Tavily API key required" in str(exc.value)


def test_search_happy_path_builds_params(monkeypatch):
    fake = FakeTavilyClient(api_key="k")
    monkeypatch.setattr(search_mod, "TavilyClient", lambda api_key=None: fake)
    integ = TavilyIntegration()

    out = integ.search(
        query="Python programming",
        max_results=3,
        topic="news",
        include_raw_content=True,
        include_domains=["docs.python.org"],
        exclude_domains=["example.com"],
    )

    assert "results" in out and len(out["results"]) == 2
    # Verify call parameters captured by fake
    assert fake.calls and fake.calls[-1]["query"] == "Python programming"
    assert fake.calls[-1]["max_results"] == 3
    assert fake.calls[-1]["topic"] == "news"
    assert fake.calls[-1]["include_raw_content"] is True
    assert fake.calls[-1]["include_domains"] == ["docs.python.org"]
    assert fake.calls[-1]["exclude_domains"] == ["example.com"]


@pytest.mark.parametrize("bad_query", ["", "   ", None])
def test_search_rejects_empty_query(bad_query):
    integ = TavilyIntegration()
    with pytest.raises(ValueError):
        integ.search(bad_query)


@pytest.mark.parametrize("bad_n", [0, 21, -1, 100])
def test_search_rejects_bad_max_results(bad_n):
    integ = TavilyIntegration()
    with pytest.raises(ValueError):
        integ.search("ok", max_results=bad_n)


def test_helpers_extract_and_format():
    integ = TavilyIntegration()
    # Build a canned results dict
    results = {
        "results": [
            {
                "title": "A",
                "url": "https://a.com",
                "content": "AAA",
                "score": 0.9,
                "published_date": "2024-01-01",
                "raw_content": "<html>AAA</html>",
            },
            {
                "title": "B",
                "url": "https://b.com",
                "content": "BBB",
                "score": 0.8,
            },
        ]
    }

    # URLs
    urls = integ.extract_urls_from_results(results)
    assert urls == ["https://a.com", "https://b.com"]

    # Structured content
    extracted = integ.extract_content_from_results(results)
    assert extracted[0]["title"] == "A"
    assert extracted[0]["raw_content"] == "<html>AAA</html>"
    assert extracted[1]["title"] == "B"

    # Key information
    key_info = integ.extract_key_information(results)
    assert key_info == ["AAA", "BBB"]

    # Markdown formatting
    md = integ.format_search_results(results, "markdown")
    assert "# Search Results (2 found)" in md
    assert "## 1. A" in md
    assert "**URL:** https://a.com" in md

    # JSON formatting
    js = integ.format_search_results(results, "json")
    assert js.strip().startswith("{") and "\"results\"" in js


def test_search_and_extract_wraps_to_dataclass(monkeypatch):
    fake = FakeTavilyClient(api_key="k")
    monkeypatch.setattr(search_mod, "TavilyClient", lambda api_key=None: fake)
    integ = TavilyIntegration()
    out = integ.search_and_extract("query", max_results=2, topic="general")
    assert len(out) == 2
    assert out[0].title == "Result 1"
    assert out[0].url == "https://example.com/1"
    assert out[0].score == 0.9


def test_top_level_internet_search_function(monkeypatch):
    # Ensure the top-level convenience function works with the fake
    fake = FakeTavilyClient(api_key="k")
    monkeypatch.setattr(search_mod, "TavilyClient", lambda api_key=None: fake)
    monkeypatch.setenv("TAVILY_API_KEY", "zzz")

    out = internet_search("Python programming", max_results=2, topic="general", include_raw_content=False)
    assert "results" in out and len(out["results"]) == 2
