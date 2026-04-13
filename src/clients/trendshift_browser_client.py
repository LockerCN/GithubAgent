"""Trendshift 页面抓取客户端实现。"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from typing import Callable

from src.common.exceptions import TrendshiftFetchError
from src.models.repository_models import RepositoryCandidate


PageContentLoader = Callable[[str, int], str]
_TRACKED_TAGS = {"body", "main", "section", "article", "div"}
_REPOSITORY_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[^/\s]+)/(?P<name>[^/\s?#]+?)(?:/)?(?:[?#].*)?$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class _SectionContext:
    """解析时记录容器上下文。"""

    tag: str
    depth: int
    text_parts: list[str] = field(default_factory=list)
    repo_links: list[str] = field(default_factory=list)


class _DailyExploreParser(HTMLParser):
    """解析包含 Daily Explore 的页面片段。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[_SectionContext] = []
        self._matched_sections: list[_SectionContext] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in _TRACKED_TAGS:
            self._stack.append(_SectionContext(tag=normalized_tag, depth=len(self._stack)))

        href = self._extract_href(attrs)
        if href is None:
            return

        if _REPOSITORY_URL_PATTERN.match(href) is None:
            return

        for context in self._stack:
            context.repo_links.append(href)

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return

        for context in self._stack:
            context.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag not in _TRACKED_TAGS or not self._stack:
            return

        current = self._stack.pop()
        combined_text = " ".join(current.text_parts).lower()
        if "daily explore" in combined_text and current.repo_links:
            self._matched_sections.append(current)

    def extract_repository_urls(self) -> list[str]:
        if not self._matched_sections:
            return []

        selected_section = max(
            self._matched_sections,
            key=lambda item: (item.depth, len(item.repo_links)),
        )
        unique_urls: list[str] = []
        seen: set[str] = set()

        for url in selected_section.repo_links:
            if url in seen:
                continue
            seen.add(url)
            unique_urls.append(url)

        return unique_urls

    def _extract_href(self, attrs: list[tuple[str, str | None]]) -> str | None:
        for key, value in attrs:
            if key.lower() == "href" and value:
                return value.strip()
        return None


class TrendshiftBrowserClient:
    """负责抓取 Trendshift Daily Explore 候选仓库。"""

    def __init__(
        self,
        daily_explore_url: str,
        browser_timeout_ms: int,
        page_content_loader: PageContentLoader | None = None,
    ) -> None:
        self._daily_explore_url = daily_explore_url
        self._browser_timeout_ms = browser_timeout_ms
        self._page_content_loader = page_content_loader or self._load_page_content_with_playwright

    def fetch_daily_top_repositories(self, limit: int) -> list[RepositoryCandidate]:
        """抓取前 N 个 Github 仓库候选。"""

        if limit <= 0:
            return []

        try:
            html = self._page_content_loader(self._daily_explore_url, self._browser_timeout_ms)
        except TrendshiftFetchError:
            raise
        except Exception as error:
            raise TrendshiftFetchError("Trendshift 页面抓取失败。") from error

        repository_urls = self._extract_repository_urls(html)
        if not repository_urls:
            raise TrendshiftFetchError("未能从 Daily Explore 区域解析出 Github 仓库。")

        candidates: list[RepositoryCandidate] = []
        for rank, repository_url in enumerate(repository_urls[:limit], start=1):
            match = _REPOSITORY_URL_PATTERN.match(repository_url)
            if match is None:
                continue

            owner = match.group("owner")
            name = match.group("name")
            full_name = f"{owner}/{name}"
            candidates.append(
                RepositoryCandidate(
                    rank=rank,
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    repo_url=f"https://github.com/{full_name}",
                )
            )

        if not candidates:
            raise TrendshiftFetchError("未能从 Trendshift 页面解析出有效仓库。")

        return candidates

    def _extract_repository_urls(self, html: str) -> list[str]:
        parser = _DailyExploreParser()
        parser.feed(html)
        return parser.extract_repository_urls()

    def _load_page_content_with_playwright(self, url: str, timeout_ms: int) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise TrendshiftFetchError("Playwright 未安装，无法抓取 Trendshift 页面。") from error

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    return page.content()
                finally:
                    browser.close()
        except Exception as error:
            raise TrendshiftFetchError(f"Trendshift 页面抓取失败: {error}") from error
