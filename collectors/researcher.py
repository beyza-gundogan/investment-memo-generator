"""
Research orchestrator
Runs all collectors in sequence for a given company and
returns a single clean research package ready for memo generation.

Usage:
    from collectors.researcher import research_company
    data = research_company("Monzo", website="https://monzo.com")
"""

import json
import time
from pathlib import Path
from datetime import datetime

from collectors.website_scraper    import scrape_website
from collectors.wikipedia_collector import get_wikipedia_data
from collectors.news_collector     import get_news_data

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def research_company(company_name: str,
                     website: str = None,
                     use_cache: bool = True) -> dict:
    """
    Main research function. Runs all collectors and returns
    a unified research package.

    company_name: e.g. "Monzo"
    website:      e.g. "https://monzo.com" (optional but improves quality)
    use_cache:    if True, loads from disk if already researched today
    """

    # Check cache first
    cache_path = _cache_path(company_name)
    if use_cache and cache_path.exists():
        cached = json.loads(cache_path.read_text())
        cached_date = cached.get("researched_on", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if cached_date == today:
            print(f"[Research] Using cached data for '{company_name}'")
            return cached

    print(f"\n[Research] Starting research for '{company_name}'...")
    print(f"{'─'*45}")

    package = {
        "company_name":  company_name,
        "website":       website or "",
        "researched_on": datetime.now().strftime("%Y-%m-%d"),
        "researched_at": datetime.now().strftime("%H:%M"),
    }

    # ── 1. Website scraping ───────────────────────────────────────────────
    if website:
        package["website_data"] = scrape_website(website)
    else:
        # Try to guess the website
        guessed = _guess_website(company_name)
        if guessed:
            package["website_data"] = scrape_website(guessed)
            package["website"] = guessed
        else:
            package["website_data"] = {"all_text": "", "error": "No website provided"}
    time.sleep(0.5)

    # ── 2. Wikipedia ──────────────────────────────────────────────────────
    package["wikipedia_data"] = get_wikipedia_data(company_name)
    time.sleep(0.5)

    # ── 3. News ───────────────────────────────────────────────────────────
    package["news_data"] = get_news_data(company_name)
    time.sleep(0.5)

    # ── 4. Summary stats ─────────────────────────────────────────────────
    package["research_summary"] = _summarise(package)

    # Save to cache
    cache_path.write_text(json.dumps(package, indent=2, default=str))

    print(f"{'─'*45}")
    print(f"[Research] Complete for '{company_name}'")
    _print_summary(package["research_summary"])

    return package


def _summarise(package: dict) -> dict:
    """Build a quick summary of what was found."""
    wiki  = package.get("wikipedia_data", {})
    news  = package.get("news_data", {})
    web   = package.get("website_data", {})

    return {
        "has_wikipedia":    wiki.get("found", False),
        "has_website_text": len(web.get("all_text", "")) > 100,
        "news_count":       news.get("total", 0),
        "has_funding_news": len(news.get("funding_news", [])) > 0,
        "has_risk_signals": news.get("has_risk_signals", False),
        "founded":          wiki.get("founded", ""),
        "founders":         wiki.get("founders", ""),
        "headquarters":     wiki.get("headquarters", ""),
        "data_quality":     _data_quality_score(wiki, news, web),
    }


def _data_quality_score(wiki: dict, news: dict, web: dict) -> str:
    """Rate the quality of data collected — High / Medium / Low."""
    score = 0
    if wiki.get("found"):             score += 3
    if len(web.get("all_text",""))>500: score += 2
    if news.get("total", 0) > 5:      score += 2
    if wiki.get("key_facts"):         score += 1
    if news.get("funding_news"):      score += 1
    if score >= 7: return "High"
    if score >= 4: return "Medium"
    return "Low"


def _guess_website(company_name: str) -> str:
    """Try common website patterns for a company name."""
    import requests as req
    slug = company_name.lower().replace(" ", "").replace(",", "")
    candidates = [
        f"https://www.{slug}.com",
        f"https://{slug}.com",
        f"https://www.{slug}.io",
        f"https://{slug}.io",
        f"https://www.{slug}.co.uk",
    ]
    for url in candidates:
        try:
            r = req.head(url, timeout=4, allow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code < 400:
                return url
        except Exception:
            continue
    return ""


def _cache_path(company_name: str) -> Path:
    safe = company_name.lower().replace(" ", "_").replace("/", "-")
    return DATA_DIR / f"{safe}_research.json"


def _print_summary(summary: dict):
    print(f"  Wikipedia:     {'✓' if summary['has_wikipedia'] else '✗'}")
    print(f"  Website text:  {'✓' if summary['has_website_text'] else '✗'}")
    print(f"  News articles: {summary['news_count']}")
    print(f"  Funding news:  {'✓' if summary['has_funding_news'] else '✗'}")
    print(f"  Risk signals:  {'✓' if summary['has_risk_signals'] else '✗'}")
    print(f"  Data quality:  {summary['data_quality']}")


if __name__ == "__main__":
    # Test with multiple companies to see which sources work
    import sys
    company = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    website = sys.argv[2] if len(sys.argv) > 2 else None
    data = research_company(company, website=website, use_cache=False)
    s = data["research_summary"]
    print(f"\nFounded:    {s['founded']}")
    print(f"Founders:   {s['founders']}")
    print(f"HQ:         {s['headquarters']}")
    print(f"Quality:    {s['data_quality']}")

    # Show sample of what was collected
    web = data.get("website_data", {})
    if web.get("error"):
        print(f"\nWebsite error: {web['error']}")
    elif web.get("all_text"):
        print(f"\nWebsite sample: {web['all_text'][:200]}")

    news = data.get("news_data", {})
    if news.get("all_articles"):
        print(f"\nTop news:")
        for a in news["all_articles"][:3]:
            print(f"  [{a['source']}] {a['title'][:70]}")
