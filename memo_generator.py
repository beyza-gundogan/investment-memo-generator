"""
Investment Memo Generator
Takes a research package from the data collection layer and uses
Claude API to write a structured, analyst-quality investment memo.

Usage:
    python -m memo_generator Stripe https://stripe.com
    python -m memo_generator Monzo
    python -m memo_generator Revolut https://revolut.com
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from collectors.researcher import research_company

load_dotenv()

def _get_api_key() -> str:
    """Get Anthropic API key from Streamlit secrets or .env file."""
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
    except Exception:
        return os.getenv("ANTHROPIC_API_KEY", "")
MEMOS_DIR = Path("memos")
MEMOS_DIR.mkdir(exist_ok=True)


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_memo(company_name: str, website: str = None) -> str:
    """
    Full pipeline: research company → build prompt → call Claude → save memo.
    Returns the memo text.
    """
    if not _get_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set in .env file or Streamlit secrets")
        return ""

    # Step 1: Research
    print(f"\nGenerating investment memo for: {company_name}")
    print("=" * 50)
    research = research_company(company_name, website=website)

    # Step 2: Build prompt
    print("\n[Memo] Building prompt...")
    prompt = _build_prompt(research)
    print(f"[Memo] Prompt length: {len(prompt.split())} words")

    # Step 3: Call Claude
    print("[Memo] Calling Claude API...")
    memo = _call_claude(prompt)
    if not memo:
        return ""

    # Step 4: Save
    path = _save_memo(memo, company_name)
    print(f"[Memo] Saved → {path}")
    print("\n" + "=" * 50)
    print(memo)

    return memo


# ── Prompt engineering ────────────────────────────────────────────────────────

def _build_prompt(research: dict) -> str:
    """
    Build the full prompt for Claude.
    This is the most important function — prompt quality = memo quality.
    We feed in all collected data in a structured way so Claude
    can write an informed, specific memo rather than a generic one.
    """
    company  = research.get("company_name", "")
    wiki     = research.get("wikipedia_data", {})
    web      = research.get("website_data", {})
    news     = research.get("news_data", {})
    summary  = research.get("research_summary", {})

    # ── Format each data source clearly ──────────────────────────────────

    # Wikipedia facts
    wiki_text = ""
    if wiki.get("found"):
        wiki_text = f"""
WIKIPEDIA SUMMARY:
{wiki.get('summary', '')[:1000]}

KEY FACTS FROM WIKIPEDIA:
{chr(10).join(f'- {f}' for f in wiki.get('key_facts', [])[:6])}

Founded: {wiki.get('founded', 'Unknown')}
Founders: {wiki.get('founders', 'Unknown')}
Headquarters: {wiki.get('headquarters', 'Unknown')}
"""

    # Website content
    web_text = ""
    if web.get("all_text"):
        web_text = f"""
COMPANY WEBSITE CONTENT:
{web.get('all_text', '')[:1500]}
"""

    # News — formatted by category
    news_text = ""
    if news.get("total", 0) > 0:
        funding_lines = "\n".join(
            f"- [{a.get('source','?')}] {a.get('title','')}"
            for a in news.get("funding_news", [])[:4]
        )
        product_lines = "\n".join(
            f"- [{a.get('source','?')}] {a.get('title','')}"
            for a in news.get("product_news", [])[:4]
        )
        risk_lines = "\n".join(
            f"- [{a.get('source','?')}] {a.get('title','')}"
            for a in news.get("risk_news", [])[:3]
        )
        general_lines = "\n".join(
            f"- [{a.get('source','?')}] {a.get('title','')}"
            for a in news.get("general_news", [])[:4]
        )
        news_text = f"""
RECENT NEWS ({news.get('total', 0)} articles found):

Funding/Investment news:
{funding_lines if funding_lines else '- None found'}

Product/Launch news:
{product_lines if product_lines else '- None found'}

Risk/Regulatory signals:
{risk_lines if risk_lines else '- None found'}

General coverage:
{general_lines if general_lines else '- None found'}
"""

    # Data quality warning for Claude
    quality = summary.get("data_quality", "Medium")
    quality_note = ""
    if quality == "Low":
        quality_note = (
            "NOTE: Limited data was available for this company. "
            "Be explicit about data gaps and avoid speculation. "
            "Flag clearly where more research is needed."
        )

    # ── The actual prompt ─────────────────────────────────────────────────
    return f"""You are a senior investment analyst at a top-tier venture capital firm.
Your task is to write a professional investment memo for {company} based on the research data below.

CRITICAL INSTRUCTIONS:
- Write in a direct, analytical tone — like a McKinsey analyst, not a Wikipedia editor
- Every claim must be grounded in the data provided below
- Where data is missing or unclear, say so explicitly — do not invent facts
- Be specific: use numbers, dates, and names from the data where available
- Identify genuine risks and weaknesses, not just positives
- The memo will be read by a senior partner making an investment decision
- Write in prose paragraphs — no bullet points anywhere in the memo
- Total length: 600-800 words
{quality_note}

---
RESEARCH DATA:
{wiki_text}
{web_text}
{news_text}
---

Write the memo using EXACTLY this structure:

# {company} — Investment Memo
*Prepared: {datetime.now().strftime('%B %Y')}*

## Executive Summary
[3-4 sentences. What the company does, its stage/scale, the core investment thesis, and your overall verdict. Be direct — state clearly whether this is worth pursuing.]

## Business Model
[2-3 paragraphs. How does the company make money? Who are the customers and what problem does it solve for them? What is the pricing model or revenue structure? What makes the business model defensible or not?]

## Market Opportunity
[2 paragraphs. How large is the addressable market and is it growing? What structural tailwinds or headwinds exist? Where does this company sit in the competitive landscape — who are the main competitors and what is the differentiation?]

## Team & Execution
[1-2 paragraphs. What do we know about the founding team and their relevant experience? What does the company's trajectory so far suggest about execution capability? What hiring or operational signals are visible?]

## Traction & Financials
[1-2 paragraphs. What traction signals are available — revenue, customers, growth, funding raised? What does the funding history suggest about investor confidence? Be honest about what is unknown.]

## Key Risks
[2 paragraphs. What are the 3-4 most significant risks to this investment? These should be specific and credible — regulatory exposure, competitive threats, execution risks, market timing concerns. Do not be generic.]

## Recommendation
[1 paragraph. Clear verdict: Pursue / Watch / Pass. What is the primary reason for this recommendation? What would need to be true — or what additional information is needed — before making a final decision?]
"""


# ── Claude API call ───────────────────────────────────────────────────────────

def _call_claude(prompt: str) -> str:
    """Call Anthropic Claude API and return the memo text."""
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         _get_api_key(),
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 2500,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )

        if resp.status_code != 200:
            print(f"[Claude] API error {resp.status_code}: {resp.text[:200]}")
            return ""

        data = resp.json()
        return data["content"][0]["text"]

    except Exception as e:
        print(f"[Claude] Error: {e}")
        return ""


# ── Save memo ─────────────────────────────────────────────────────────────────

def _save_memo(memo: str, company_name: str) -> Path:
    """Save memo as a markdown file."""
    safe   = company_name.lower().replace(" ", "_").replace("/", "-")
    ts     = datetime.now().strftime("%Y%m%d_%H%M")
    path   = MEMOS_DIR / f"memo_{safe}_{ts}.md"
    path.write_text(memo, encoding="utf-8")
    return path


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m memo_generator <company_name> [website_url]")
        print("Example: python -m memo_generator Stripe https://stripe.com")
        sys.exit(1)

    name    = sys.argv[1]
    website = sys.argv[2] if len(sys.argv) > 2 else None
    generate_memo(name, website)
