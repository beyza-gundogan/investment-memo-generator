"""
Investment Memo Generator — Streamlit Web App
Run with: streamlit run app.py

A clean, professional interface where users type a company name,
optionally add a website URL, and get a full investment memo generated
in real time using Claude API.
"""

import os
import glob
import streamlit as st
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Investment Memo Generator",
    page_icon="📋",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .memo-container {
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 2rem;
        margin-top: 1.5rem;
    }
    .status-box {
        background: #f0f7ff;
        border-left: 4px solid #2196F3;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .example-chip {
        display: inline-block;
        background: #f0f0f0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        margin: 4px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("About")
    st.write(
        "This tool automatically researches a company using public data "
        "sources and generates a structured investment memo using AI."
    )
    st.divider()

    st.subheader("Data sources")
    st.write("🌐 Company website")
    st.write("📖 Wikipedia")
    st.write("📰 News & press coverage")
    st.write("🤖 Claude AI (memo writing)")

    st.divider()
    st.subheader("Previous memos")

    # Show list of previously generated memos
    memo_files = sorted(
        glob.glob("memos/memo_*.md"),
        reverse=True
    )
    if memo_files:
        for f in memo_files[:8]:
            name = Path(f).stem.replace("memo_", "").rsplit("_", 2)[0]
            name = name.replace("_", " ").title()
            if st.button(f"📄 {name}", key=f, use_container_width=True):
                st.session_state["load_memo"] = f
    else:
        st.caption("No memos generated yet")

    st.divider()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        st.success("✓ Anthropic API connected")
    else:
        st.error("✗ ANTHROPIC_API_KEY missing in .env")


# ── Main content ──────────────────────────────────────────────────────────────

st.markdown('<p class="main-header">📋 Investment Memo Generator</p>',
            unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Enter a company name to generate a '
    'professional investment memo in seconds.</p>',
    unsafe_allow_html=True
)

# ── Input form ────────────────────────────────────────────────────────────────

col1, col2 = st.columns([2, 1])

with col1:
    company_name = st.text_input(
        "Company name",
        placeholder="e.g. Monzo, Stripe, Revolut, Notion...",
        value=st.session_state.get("example_name", ""),
        help="Enter the name of the company you want to analyse"
    )

with col2:
    website_url = st.text_input(
        "Website URL (optional)",
        placeholder="https://example.com",
        value=st.session_state.get("example_url", ""),
        help="Adding the website improves memo quality"
    )

# Example companies
st.markdown("**Try these examples:**")
example_cols = st.columns(6)
examples = [
    ("Monzo", "https://monzo.com"),
    ("Wise", "https://wise.com"),
    ("Starling Bank", "https://starlingbank.com"),
    ("GoCardless", "https://gocardless.com"),
    ("Checkout.com", "https://checkout.com"),
    ("Marshmallow", "https://marshmallow.com"),
]
for i, (name, url) in enumerate(examples):
    with example_cols[i]:
        if st.button(name, use_container_width=True):
            st.session_state["example_name"] = name
            st.session_state["example_url"]  = url
            st.session_state["auto_generate"] = True
            st.rerun()

# Clear example state after reading it
if "example_name" in st.session_state and company_name == st.session_state.get("example_name"):
    pass  # keep it set until user clears the field

# ── Generate button ───────────────────────────────────────────────────────────

generate_col, options_col = st.columns([1, 2])

with generate_col:
    generate_btn = st.button(
        "Generate memo",
        type="primary",
        use_container_width=True,
        disabled=not company_name or not os.getenv("ANTHROPIC_API_KEY")
    )

with options_col:
    use_cache = st.checkbox(
        "Use cached research (faster)",
        value=True,
        help="If you've researched this company before today, use saved data"
    )

# Trigger generation from example button click
auto_generate = st.session_state.pop("auto_generate", False)
should_generate = generate_btn or auto_generate

# ── Load a previous memo ──────────────────────────────────────────────────────

if "load_memo" in st.session_state:
    memo_path = st.session_state.pop("load_memo")
    try:
        memo_text = Path(memo_path).read_text(encoding="utf-8")
        st.divider()
        st.markdown(memo_text)
    except Exception as e:
        st.error(f"Could not load memo: {e}")

# ── Generation flow ───────────────────────────────────────────────────────────

elif should_generate and company_name:

    st.divider()

    try:
        from collectors.researcher import research_company
        from memo_generator import _build_prompt, _call_claude, _save_memo

        # Use st.status for reliable live progress display
        with st.status(f"Generating memo for {company_name}...", expanded=True) as status:

            st.write("📡 Step 1/3 — Scraping website...")
            st.write("📖 Step 1/3 — Fetching Wikipedia data...")
            st.write("📰 Step 1/3 — Collecting news articles...")

            research = research_company(
                company_name,
                website=website_url or None,
                use_cache=use_cache
            )

            summary    = research.get("research_summary", {})
            quality    = summary.get("data_quality", "Low")
            news_count = research["news_data"].get("total", 0)

            st.write(f"✅ Research complete — {news_count} articles, quality: {quality}")
            st.write("🤖 Step 2/3 — Writing memo with Claude AI (20–40 seconds)...")

            prompt = _build_prompt(research)
            memo   = _call_claude(prompt)

            if not memo:
                status.update(label="❌ Failed", state="error")
                st.error("Claude API call failed — check ANTHROPIC_API_KEY in .env")
            else:
                path = _save_memo(memo, company_name)
                st.write(f"💾 Step 3/3 — Saved to {path.name}")
                status.update(label="✅ Memo generated!", state="complete")

        if memo:
            # Research stats
            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            rcol1.metric("Wikipedia",     "✓" if summary.get("has_wikipedia") else "✗")
            rcol2.metric("Website",       "✓" if summary.get("has_website_text") else "✗")
            rcol3.metric("News articles", news_count)
            rcol4.metric("Data quality",  quality)

            if summary.get("founded"):
                st.write(f"**Founded:** {summary['founded']}")
            if summary.get("founders"):
                st.write(f"**Founders:** {summary['founders']}")

            st.divider()

            # Display memo
            st.markdown(memo)

            # Download button
            st.download_button(
                label="⬇️ Download memo as Markdown",
                data=memo,
                file_name=f"memo_{company_name.lower().replace(' ','_')}.md",
                mime="text/markdown",
            )

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)

# ── Empty state ───────────────────────────────────────────────────────────────

else:
    st.info(
        "Enter a company name above and click **Generate memo** to get started. "
        "The tool will research the company from public sources and generate "
        "a professional investment memo in about 30–60 seconds."
    )

    with st.expander("What does a generated memo look like?", expanded=False):
        st.markdown("""
**# Company Name — Investment Memo**
*Prepared: Month Year*

**## Executive Summary**
Overview of the company, its scale, and investment verdict.

**## Business Model**
How the company makes money, customer segments, defensibility.

**## Market Opportunity**
Market size, growth rate, competitive landscape.

**## Team & Execution**
Founding team, execution track record, hiring signals.

**## Traction & Financials**
Revenue, growth metrics, funding history, key KPIs.

**## Key Risks**
Regulatory, competitive, execution, and market risks.

**## Recommendation**
Pursue / Watch / Pass with specific rationale and next steps.
        """)
