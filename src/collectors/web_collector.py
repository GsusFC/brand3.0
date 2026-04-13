"""
Web collector using Firecrawl.

Scrapes the brand's website and extracts:
- HTML structure, meta tags, content
- Visual assets (logo, colors — via screenshots)
- Tech stack detection
- Page speed signals
"""

import subprocess
import json
from dataclasses import dataclass


@dataclass
class WebData:
    """Raw web data from scraping."""
    url: str
    title: str = ""
    meta_description: str = ""
    markdown_content: str = ""
    html: str = ""
    links: list = None
    images: list = None
    screenshot_path: str = ""
    tech_stack: list[str] = None
    load_time_ms: int = 0
    error: str = ""

    def __post_init__(self):
        self.links = self.links or []
        self.images = self.images or []
        self.tech_stack = self.tech_stack or []


class WebCollector:
    """Collects web data via Firecrawl CLI."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _run_firecrawl(self, url: str, options: list[str] = None) -> dict:
        """Run firecrawl CLI and return parsed output."""
        cmd = ["firecrawl", "scrape", url, "--format", "markdown"]
        if options:
            cmd.extend(options)

        env = None
        if self.api_key:
            import os
            env = {**os.environ, "FIRECRAWL_API_KEY": self.api_key}

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        # Parse output — skip first line (Scrape ID)
        lines = result.stdout.strip().split("\n")
        content = "\n".join(lines[1:]) if lines else ""
        return {"content": content, "raw": result.stdout}

    def scrape(self, url: str) -> WebData:
        """Scrape a website and return structured data."""
        data = WebData(url=url)

        # Basic scrape
        result = self._run_firecrawl(url)
        if "error" in result:
            data.error = result["error"]
            return data

        data.markdown_content = result.get("content", "")

        # Extract title from markdown (usually first heading)
        for line in data.markdown_content.split("\n"):
            if line.startswith("# "):
                data.title = line[2:].strip()
                break

        return data

    def scrape_multiple(self, urls: list[str]) -> list[WebData]:
        """Scrape multiple URLs."""
        return [self.scrape(url) for url in urls]
