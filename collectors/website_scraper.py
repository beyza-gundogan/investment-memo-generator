"""
Website scraper
Fetches and extracts key content from a company's website.
Uses requests + BeautifulSoup — no API key needed.

Extracts:
- Company description / about text
- Product/service descriptions
- Pricing information (if public)
- Team page content
- Any mission/vision statements
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Pages worth visiting beyond the homepage
USEFUL_PATHS = [
    "/about", "/about-us", "/company", "/our-story",
    "/product", "/products", "/platform", "/solutions",
    "/pricing", "/team", "/careers",
]


def scrape_website(url: str) -> dict:
    """
    Main function. Scrapes a company website and returns
    structured text content for memo generation.

    url: company website e.g. "https://monzo.com"
    """
    if not url.startswith("http"):
        url = "https://" + url

    print(f"  [Website] Scraping {url}...")
    result = {
        "url":         url,
        "homepage":    "",
        "about":       "",
        "product":     "",
        "pricing":     "",
        "team":        "",
        "all_text":    "",
        "page_titles": [],
        "error":       None,
    }

    try:
        # Always scrape homepage first
        homepage_text, homepage_title = _scrape_page(url)
        result["homepage"]    = homepage_text[:2000]
        result["page_titles"].append(homepage_title)

        # Try useful subpages
        base = _base_url(url)
        for path in USEFUL_PATHS:
            page_url = base + path
            text, title = _scrape_page(page_url)
            if not text:
                continue

            result["page_titles"].append(title)
            lower_path = path.lower()

            if any(x in lower_path for x in ["/about", "/company", "/story"]):
                result["about"] += " " + text[:1500]
            elif any(x in lower_path for x in ["/product", "/platform", "/solutions"]):
                result["product"] += " " + text[:1500]
            elif "/pricing" in lower_path:
                result["pricing"] += " " + text[:1000]
            elif "/team" in lower_path:
                result["team"] += " " + text[:1000]

        # Combine all text for Claude
        combined = " ".join([
            result["homepage"],
            result["about"],
            result["product"],
            result["pricing"],
            result["team"],
        ])
        result["all_text"] = _clean_text(combined)[:5000]

    except Exception as e:
        result["error"] = str(e)
        print(f"  [Website] Error: {e}")

    words = len(result["all_text"].split())
    print(f"  [Website] Extracted {words} words from {url}")
    return result


def _scrape_page(url: str) -> tuple[str, str]:
    """Fetch a single page and return (clean_text, page_title)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return "", ""

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer",
                          "header", "cookie", "popup"]):
            tag.decompose()

        title = soup.title.string if soup.title else ""

        # Extract meaningful text
        text_parts = []
        for tag in soup.find_all(["p", "h1", "h2", "h3", "li", "span"]):
            t = tag.get_text(separator=" ", strip=True)
            if len(t) > 30:  # skip very short fragments
                text_parts.append(t)

        return _clean_text(" ".join(text_parts)), title or ""

    except Exception:
        return "", ""


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and non-ASCII characters."""
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _base_url(url: str) -> str:
    """Extract base URL e.g. https://monzo.com from https://monzo.com/about."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


if __name__ == "__main__":
    result = scrape_website("https://monzo.com")
    print(f"\nHomepage preview:\n{result['homepage'][:300]}...")
    print(f"\nAbout preview:\n{result['about'][:300]}...")
    print(f"\nTotal text: {len(result['all_text'].split())} words")
