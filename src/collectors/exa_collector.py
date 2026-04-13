"""
Exa collector for semantic search, competitor discovery, and AI visibility.

Uses Exa API for:
- Brand mention search (percepción)
- Competitor discovery (diferenciación)
- AI visibility probe (presencia)
- Content freshness (vitalidad)
"""

from dataclasses import dataclass, field


@dataclass
class ExaResult:
    """Single Exa search result."""
    url: str
    title: str
    text: str = ""
    highlights: list = field(default_factory=list)
    summary: str = ""
    score: float = 0.0
    published_date: str = ""


@dataclass
class ExaData:
    """Aggregated Exa data for a brand."""
    brand_name: str
    mentions: list[ExaResult] = field(default_factory=list)
    competitors: list[ExaResult] = field(default_factory=list)
    ai_visibility_results: list[ExaResult] = field(default_factory=list)
    news: list[ExaResult] = field(default_factory=list)
    raw_responses: dict = field(default_factory=dict)


class ExaCollector:
    """Collects data via Exa API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from exa_py import Exa
            if not self.api_key:
                raise ValueError("EXA_API_KEY not set")
            self._client = Exa(api_key=self.api_key)
        return self._client

    def search(self, query: str, num_results: int = 10, **kwargs) -> list[ExaResult]:
        """Run a search query via Exa."""
        try:
            response = self.client.search(
                query,
                type="auto",
                num_results=num_results,
                contents={
                    "highlights": {"max_characters": 4000},
                    "text": {"max_characters": 5000},
                },
                **kwargs,
            )
        except Exception as e:
            print(f"Exa search error: {e}")
            return []

        results = []
        for r in response.results:
            results.append(ExaResult(
                url=r.url,
                title=getattr(r, "title", ""),
                text=getattr(r, "text", ""),
                highlights=getattr(r, "highlights", []) or [],
                summary=getattr(r, "summary", ""),
                score=getattr(r, "score", 0.0),
                published_date=str(getattr(r, "published_date", "")),
            ))
        return results

    def collect_brand_data(self, brand_name: str, brand_url: str = None) -> ExaData:
        """Collect all Exa data for a brand."""
        data = ExaData(brand_name=brand_name)

        # 1. Brand mentions — how is the brand talked about?
        data.mentions = self.search(
            f'"{brand_name}" brand company',
            num_results=15,
        )

        # 2. Competitors — who else is in this space?
        if brand_url:
            data.competitors = self.search(
                f"competitors similar to {brand_name}",
                num_results=10,
                category="company",
            )

        # 3. News — recent coverage
        data.news = self.search(
            f'"{brand_name}" news',
            num_results=10,
            category="news",
        )

        # 4. AI visibility — does the brand appear in AI-related recommendations/content?
        data.ai_visibility_results = self.probe_ai_visibility(brand_name)

        return data

    def probe_ai_visibility(self, brand_name: str) -> list[ExaResult]:
        """
        Check if the brand appears in AI-related content.
        Proxies 'AI visibility' — do LLMs know this brand?
        """
        return self.search(
            f'"{brand_name}" AI artificial intelligence recommendation',
            num_results=5,
        )
