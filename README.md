Investment Memo Generator

An AI-powered tool that researches any company from public sources and generates a structured, analyst-quality investment memo in under 60 seconds — built to automate the first-pass analysis workflow used in venture capital, private equity, and strategy consulting.

Demo

https://beyza-gundogan-investment-memo-generator.streamlit.app/

What it does
1. Research — automatically scrapes the company website, fetches Wikipedia data, and aggregates recent news articles and press coverage from multiple sources.
2. Analyse — categorises news by type (funding announcements, product launches, regulatory/risk signals) and extracts structured facts (founding date, founders, headquarters, key financial metrics).
3. Write — sends all collected research to Claude API with a carefully engineered prompt and generates a structured 700–900 word investment memo covering 7 sections.
4. Export — renders the memo inline in the browser and offers a one-click Markdown download.

Example output
# Monzo — Investment Memo
Prepared: June 2026

## Executive Summary
Monzo is a UK-based digital banking platform that has scaled to 15.2 million
personal customers as of May 2026, operating a diversified fintech business
spanning current accounts, lending, savings products, and telecommunications
services. The company achieved its first annual profit of £15.4 million in the
year ending March 2024, reversing a £116.3 million loss the prior year...

## Key Risks
The primary risk is credit quality deterioration in a consumer lending book
that has grown rapidly. Loan loss provisions doubling year-on-year while the
company only just turned profitable indicates either conservative provisioning
or early signs of credit stress...

## Recommendation
Watch, with conditions. Monzo has demonstrated the business model can work at
scale, but the combination of credit risk exposure, strategic overextension into
telecommunications, and margin pressure warrants caution at current valuations...

Memo structure
Every generated memo covers 7 sections in a standardised format:
SectionWhat it coversExecutive SummaryCompany overview, scale, and investment verdictBusiness ModelRevenue streams, customer segments, defensibilityMarket OpportunityTAM, growth rate, competitive landscapeTeam & ExecutionFounding team, track record, hiring signalsTraction & FinancialsRevenue, funding history, key metricsKey RisksRegulatory, competitive, execution, market risksRecommendationPursue / Watch / Pass with specific rationale

Tech stack

Python 3.12
Streamlit — web interface
Anthropic Claude API — memo generation (~$0.005 per memo)
BeautifulSoup + requests — website scraping
Wikipedia API — company facts and funding history
NewsAPI — press coverage and funding announcements
Google News RSS / Bing News RSS — additional news coverage (no key needed)


Setup
1. Clone the repo
bashgit clone https://github.com/beyza-gundogan/investment-memo-generator.git
cd investment-memo-generator
2. Create a virtual environment
bashpython3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
3. Install dependencies
bashpip install -r requirements.txt
4. Set up API keys
bashcp .env.example .env
Then open .env and fill in your keys:
KeyWhere to get itCostANTHROPIC_API_KEYconsole.anthropic.com~$0.005/memoNEWS_API_KEYnewsapi.org/registerFreeCOMPANIES_HOUSE_API_KEYdeveloper.company-information.service.gov.ukFree
5. Run the app
bashstreamlit run app.py
Opens at http://localhost:8501. Type any company name and click Generate memo.
6. Or run from the terminal
bashpython -m memo_generator Monzo https://monzo.com
python -m memo_generator Revolut https://revolut.com
python -m memo_generator Stripe
Memos are saved to the memos/ folder as Markdown files.

Project structure
investment-memo-generator/
├── app.py                        # Streamlit web interface
├── memo_generator.py             # Core memo generation + Claude API
├── collectors/
│   ├── researcher.py             # Research orchestrator
│   ├── website_scraper.py        # Company website scraper
│   ├── wikipedia_collector.py    # Wikipedia data fetcher
│   └── news_collector.py         # News aggregator
├── .env.example                  # API key template
└── requirements.txt

Data quality
The tool rates research quality as High / Medium / Low based on what was found:
RatingMeaningHighWikipedia found + website scraped + 5+ news articlesMediumWikipedia found or website scraped, limited newsLowLimited public data — memo will flag gaps explicitly
Where data is missing, the memo says so explicitly rather than fabricating information. This is intentional — flagging data gaps is a core part of real investment analysis.

Limitations

Works best for companies with a Wikipedia page and active press coverage
Financial data relies on publicly available information — private company financials are rarely disclosed
Website scraping may fail for sites with aggressive bot protection
NewsAPI free tier is limited to top headlines — full article search requires a paid plan


Built as part of a VC/PE career development project. Designed to demonstrate how AI can streamline analyst workflows in investment and strategy roles.
