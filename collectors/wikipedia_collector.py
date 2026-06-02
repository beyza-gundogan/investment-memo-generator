"""
Wikipedia collector
Fetches structured facts about a company from Wikipedia.
Uses the wikipedia-api library — no key needed.

Extracts:
- Company summary
- Founded date and founders
- Key facts from the infobox
- Funding history if mentioned
- Acquisitions
"""

import re
import requests
import wikipediaapi


def get_wikipedia_data(company_name: str) -> dict:
    """
    Fetch Wikipedia data for a company.
    Tries multiple search variations to find the right article.
    """
    print(f"  [Wikipedia] Searching for '{company_name}'...")

    result = {
        "found":       False,
        "title":       "",
        "summary":     "",
        "full_text":   "",
        "url":         "",
        "founded":     "",
        "founders":    "",
        "headquarters":"",
        "key_facts":   [],
        "error":       None,
    }

    # Try variations of the company name
    search_terms = [
        company_name,
        f"{company_name} company",
        f"{company_name} startup",
        f"{company_name} Inc",
        f"{company_name} Ltd",
    ]

    wiki = wikipediaapi.Wikipedia(
        language="en",
        user_agent="memo-generator/1.0"
    )

    page = None
    for term in search_terms:
        candidate = wiki.page(term)
        if candidate.exists():
            page = candidate
            break

    if not page:
        # Fallback: use Wikipedia search API
        page = _search_wikipedia(company_name, wiki)

    if not page:
        result["error"] = f"No Wikipedia page found for '{company_name}'"
        print(f"  [Wikipedia] Not found")
        return result

    result["found"]     = True
    result["title"]     = page.title
    result["url"]       = page.fullurl
    result["summary"]   = page.summary[:1500]
    result["full_text"] = page.text[:4000]

    # Extract structured facts from text
    result["founded"]      = _extract_founded(page.text)
    result["founders"]     = _extract_founders(page.text)
    result["headquarters"] = _extract_headquarters(page.text)
    result["key_facts"]    = _extract_key_facts(page.text)

    print(f"  [Wikipedia] Found: {page.title}")
    return result


def _search_wikipedia(query: str, wiki) -> object:
    """Use Wikipedia's search API to find the best matching page."""
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action":   "query",
                "list":     "search",
                "srsearch": query,
                "format":   "json",
                "srlimit":  3,
            },
            timeout=8,
        )
        results = resp.json().get("query", {}).get("search", [])
        if results:
            title = results[0]["title"]
            page  = wiki.page(title)
            if page.exists():
                return page
    except Exception:
        pass
    return None


def _extract_founded(text: str) -> str:
    patterns = [
        r"[Ff]ounded\s*\|\s*(\w+\s+\d{4}|\d{4})",   # infobox format
        r"[Ff]ounded\s+in\s+(\d{4})",
        r"[Ff]ounded\s+(\w+\s+\d{4})",
        r"established\s+in\s+(\d{4})",
        r"incorporated\s+in\s+(\d{4})",
        r"launched\s+in\s+(\d{4})",
        r"launched\s+(\w+\s+\d{4})",
        r"in\s+(\d{4}),?\s+\w+\s+(?:was\s+)?founded",
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1)
    return ""


def _extract_founders(text: str) -> str:
    patterns = [
        # Most common Wikipedia format: "founded in YEAR by Name, Name and Name"
        r"founded\s+in\s+\d{4}\s+by\s+((?:[A-Z][a-z]+\s+[A-Z][a-z]+)(?:(?:\s*,\s*|\s+and\s+)(?:[A-Z][a-z]+\s+[A-Z][a-z]+))*)",
        r"founded\s+by\s+((?:[A-Z][a-z]+\s+[A-Z][a-z]+)(?:(?:\s*,\s*|\s+and\s+)(?:[A-Z][a-z]+\s+[A-Z][a-z]+))*)",
        r"[Cc]o-?[Ff]ounders?\s+(?:include\s+)?((?:[A-Z][a-z]+\s+[A-Z][a-z]+)(?:(?:\s*,\s*|\s+and\s+)(?:[A-Z][a-z]+\s+[A-Z][a-z]+))*)",
        r"[Ff]ounder[s]?[:\s]+((?:[A-Z][a-z]+\s+[A-Z][a-z]+)(?:(?:\s*,\s*|\s+and\s+)(?:[A-Z][a-z]+\s+[A-Z][a-z]+))*)",
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            result = match.group(1).strip()
            # Extract only proper names (two capitalised words) from the match
            names = re.findall(r'[A-Z][a-z]+\s+[A-Z][a-z]+', result)
            if names:
                return ", ".join(names[:5])
    return ""


def _extract_headquarters(text: str) -> str:
    patterns = [
        r"headquartered\s+in\s+([A-Z][a-zA-Z\s,]+?)[\.\,]",
        r"headquarters\s+in\s+([A-Z][a-zA-Z\s,]+?)[\.\,]",
        r"based\s+in\s+([A-Z][a-zA-Z\s,]+?)[\.\,]",
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1).strip()[:80]
    return ""


def _extract_key_facts(text: str) -> list[str]:
    """Extract sentences containing key financial/business facts."""
    facts = []
    sentences = text.split(". ")
    keywords = ["million", "billion", "valuation", "revenue", "funding",
                "raised", "acquired", "employees", "customers", "users",
                "IPO", "Series", "unicorn", "growth"]
    for sent in sentences[:100]:
        if any(kw.lower() in sent.lower() for kw in keywords):
            clean = sent.strip()
            if 30 < len(clean) < 300:
                facts.append(clean)
        if len(facts) >= 8:
            break
    return facts


if __name__ == "__main__":
    for company in ["Monzo", "Stripe", "Revolut"]:
        data = get_wikipedia_data(company)
        print(f"\n{company}:")
        print(f"  Found: {data['found']}")
        print(f"  Founded: {data['founded']}")
        print(f"  Founders: {data['founders']}")
        print(f"  Summary: {data['summary'][:150]}...")
        print(f"  Key facts: {len(data['key_facts'])}")
