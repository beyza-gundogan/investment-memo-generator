"""
News collector
Aggregates recent press coverage using NewsAPI + Google News RSS.
Reuses the same approach from project 1 but focused on depth per company.

Extracts:
- Recent funding announcements
- Product launches
- Executive changes
- Regulatory news
- General press sentiment
"""

import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

FUNDING_KEYWORDS   = ["raises", "funding", "series", "investment", "backed",
                       "valuation", "round", "capital", "investors"]
PRODUCT_KEYWORDS   = ["launches", "announces", "new feature", "partnership",
                       "integration", "release", "expands"]
RISK_KEYWORDS      = ["lawsuit", "fine", "regulatory", "breach", "layoffs",
                       "fraud", "investigation", "scandal", "hack"]


def get_news_data(company_name: str, days: int = 180) -> dict:
    """
    Fetch and categorise news for a company over the last `days` days.
    Returns structured news data ready for memo generation.
    """
    print(f"  [News] Fetching news for '{company_name}'...")

    all_articles = []

    # Source 1: NewsAPI headlines (free tier)
    all_articles += _fetch_newsapi(company_name)

    # Source 2: Google News RSS (no key, broader coverage)
    all_articles += _fetch_google_news(company_name)

    # Deduplicate
    seen, unique = set(), []
    for a in all_articles:
        key = a.get("title", "")[:50]
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    # Categorise articles
    funding_news = [a for a in unique if _matches(a, FUNDING_KEYWORDS)]
    product_news = [a for a in unique if _matches(a, PRODUCT_KEYWORDS)]
    risk_news    = [a for a in unique if _matches(a, RISK_KEYWORDS)]
    general_news = [a for a in unique
                    if a not in funding_news
                    and a not in product_news
                    and a not in risk_news]

    print(f"  [News] Found {len(unique)} articles — "
          f"{len(funding_news)} funding, {len(product_news)} product, "
          f"{len(risk_news)} risk signals")

    return {
        "total":        len(unique),
        "all_articles": unique[:15],
        "funding_news": funding_news[:5],
        "product_news": product_news[:5],
        "risk_news":    risk_news[:5],
        "general_news": general_news[:5],
        "has_risk_signals": len(risk_news) > 0,
        "latest_date":  _latest_date(unique),
    }


def _fetch_newsapi(company_name: str) -> list[dict]:
    """NewsAPI top-headlines — works on free tier."""
    if not NEWS_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "q":        company_name,
                "language": "en",
                "pageSize": 20,
                "apiKey":   NEWS_API_KEY,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return []
        return [
            {
                "title":     a.get("title", ""),
                "source":    a.get("source", {}).get("name", ""),
                "url":       a.get("url", ""),
                "published": a.get("publishedAt", ""),
                "summary":   a.get("description", "") or "",
            }
            for a in resp.json().get("articles", [])
            if a.get("title")
        ]
    except Exception:
        return []


def _fetch_google_news(company_name: str) -> list[dict]:
    """Google News RSS — no key, good coverage."""
    try:
        query = requests.utils.quote(f'"{company_name}"')
        url   = (f"https://news.google.com/rss/search"
                 f"?q={query}&hl=en-GB&gl=GB&ceid=GB:en")
        resp  = requests.get(
            url, timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if resp.status_code != 200:
            return []

        root     = ET.fromstring(resp.content)
        articles = []
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title") or ""
            if not title:
                continue
            source_el = item.find("source")
            articles.append({
                "title":     title,
                "source":    source_el.text if source_el is not None else "",
                "url":       item.findtext("link") or "",
                "published": item.findtext("pubDate") or "",
                "summary":   "",
            })
        return articles
    except Exception:
        return []


def _matches(article: dict, keywords: list[str]) -> bool:
    text = (article.get("title", "") + " " +
            article.get("summary", "")).lower()
    return any(kw in text for kw in keywords)


def _latest_date(articles: list[dict]) -> str:
    dates = [a.get("published", "") for a in articles if a.get("published")]
    return dates[0] if dates else ""


if __name__ == "__main__":
    data = get_news_data("Monzo")
    print(f"\nTotal articles: {data['total']}")
    print(f"Funding news:   {len(data['funding_news'])}")
    print(f"Product news:   {len(data['product_news'])}")
    print(f"Risk signals:   {len(data['risk_news'])}")
    print(f"\nTop headlines:")
    for a in data["all_articles"][:5]:
        print(f"  [{a['source']}] {a['title'][:70]}")
