# SEC EDGAR Toolkit - Python

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![PyPI Version](https://img.shields.io/pypi/v/sec-edgar-toolkit.svg)](https://pypi.org/project/sec-edgar-toolkit/)
[![License](https://img.shields.io/badge/license-AGPL%20v3-blue.svg)](LICENSE)
[![Test Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](htmlcov/index.html)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![Tests](https://img.shields.io/badge/tests-41%20passed-brightgreen.svg)](tests/)

## Disclaimer

**This toolkit is not affiliated with, endorsed by, or connected to the U.S. Securities and Exchange Commission (SEC).** This is an independent open-source project designed to facilitate programmatic access to publicly available SEC EDGAR data.

- **Use at your own risk**: Users are responsible for ensuring compliance with all applicable laws and regulations
- **Rate limiting**: Please respect the SEC's [fair access policy](https://www.sec.gov/os/accessing-edgar-data) (max 10 requests per second)
- **Data accuracy**: This tool provides access to data as-is from SEC EDGAR; users should verify important information independently
- **No warranties**: This software is provided "as is" without any warranties or guarantees

## Overview

A comprehensive Python library for accessing and analyzing SEC EDGAR filings, with support for XBRL data parsing, company lookup, and financial data extraction. Built on top of the official [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

## Key Features

- **Company Lookup**: Search by ticker, CIK, or company name
- **Filing Access**: Get 10-K, 10-Q, 8-K, and other SEC filings
- **XBRL Support**: Parse and analyze structured financial data
- **Frame Data**: Access market-wide aggregated XBRL data
- **Rate Limiting**: Built-in respect for SEC fair access policies
- **Type Safety**: Full type hints and mypy compatibility
- **Well Tested**: 97% test coverage with comprehensive test suite

## Installation

```bash
pip install sec-edgar-toolkit
```

## Quick Start

```python
from sec_edgar_toolkit import SecEdgarApi

# Initialize with required User-Agent (SEC requirement)
api = SecEdgarApi(user_agent="MyCompany/1.0 (contact@example.com)")

# Find Apple by ticker
company = api.get_company_by_ticker("AAPL")
print(f"Company: {company['title']}, CIK: {company['cik_str']}")

# Get recent filings
submissions = api.get_company_submissions(company['cik_str'])
recent_filings = submissions['filings']['recent']
```

## API Reference

### Company Information

```python
# Search by ticker symbol
company = api.get_company_by_ticker("AAPL")

# Search by CIK (Central Index Key)
company = api.get_company_by_cik("0000320193")

# Search companies by name
results = api.search_companies("Apple")

# Get all company tickers (cached for 24 hours)
all_tickers = api.get_company_tickers()
```

### Company Filings & Submissions

```python
# Get all submissions for a company
submissions = api.get_company_submissions("0000320193")

# Filter by form type
annual_reports = api.get_company_submissions(
    "0000320193", 
    submission_type="10-K"
)

# Filter by date range
recent_filings = api.get_company_submissions(
    "0000320193",
    from_date="2023-01-01",
    to_date="2023-12-31"
)

# Get specific filing details
filing = api.get_filing("0000320193", "0000320193-23-000077")
```

### XBRL Financial Data

```python
# Get company facts (all XBRL data for a company)
facts = api.get_company_facts("0000320193")

# Get specific concept data (e.g., Assets over time)
assets = api.get_company_concept(
    cik="0000320193",
    taxonomy="us-gaap", 
    tag="Assets",
    unit="USD"
)

# Get market-wide frame data (aggregated across all companies)
market_data = api.get_frames(
    taxonomy="us-gaap",
    tag="Revenues", 
    unit="USD",
    year=2023
)

# Get quarterly data
quarterly_data = api.get_frames(
    taxonomy="us-gaap",
    tag="Assets",
    unit="USD", 
    year=2023,
    quarter=4
)
```

## Complete Example

```python
from sec_edgar_toolkit import SecEdgarApi, SecEdgarApiError
from datetime import datetime, timedelta

# Initialize API client
api = SecEdgarApi(user_agent="MyApp/1.0 (contact@example.com)")

try:
    # Find a company
    company = api.get_company_by_ticker("AAPL")
    if not company:
        print("Company not found")
        return
    
    cik = company['cik_str']
    print(f"Found: {company['title']} (CIK: {cik})")
    
    # Get recent 10-K filings
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2*365)  # Last 2 years
    
    filings = api.get_company_submissions(
        cik,
        submission_type="10-K",
        from_date=start_date.strftime("%Y-%m-%d"),
        to_date=end_date.strftime("%Y-%m-%d")
    )
    
    print(f"Found {len(filings['filings']['recent']['form'])} 10-K filings")
    
    # Get financial facts
    facts = api.get_company_facts(cik)
    if 'us-gaap' in facts['facts']:
        gaap_concepts = facts['facts']['us-gaap']
        print(f"Available GAAP concepts: {len(gaap_concepts)}")
        
        # Get revenue data over time
        if 'Revenues' in gaap_concepts:
            revenue_data = api.get_company_concept(
                cik, "us-gaap", "Revenues", unit="USD"
            )
            usd_data = revenue_data['units']['USD']
            annual_revenue = [d for d in usd_data if d.get('fp') == 'FY']
            
            print("Annual Revenue:")
            for item in annual_revenue[-3:]:  # Last 3 years
                revenue_b = item['val'] / 1_000_000_000
                print(f"  FY {item['fy']}: ${revenue_b:.1f}B")

except SecEdgarApiError as e:
    print(f"API Error: {e}")
```

## Rate Limiting & Fair Access

This library automatically implements the SEC's fair access requirements:

- **Rate limiting**: Maximum 10 requests per second
- **User-Agent required**: Must include your app name and contact info
- **Retry logic**: Built-in exponential backoff for failed requests

Learn more about the [SEC's fair access policy](https://www.sec.gov/os/accessing-edgar-data).

## Error Handling

```python
from sec_edgar_toolkit import (
    SecEdgarApiError,
    RateLimitError, 
    NotFoundError,
    AuthenticationError
)

try:
    company = api.get_company_by_ticker("INVALID")
except NotFoundError:
    print("Company not found")
except RateLimitError:
    print("Rate limit exceeded - please wait")
except SecEdgarApiError as e:
    print(f"API error: {e}")
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/

# Run type checking  
mypy src/ tests/

# Generate coverage report
pytest --cov=src tests/
```

## Resources

- [SEC EDGAR APIs Documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC Fair Access Policy](https://www.sec.gov/os/accessing-edgar-data)
- [XBRL Taxonomy Guide](https://www.sec.gov/structureddata/osd-inline-xbrl-faq)
- [Company Tickers JSON](https://www.sec.gov/files/company_tickers_exchange.json)

## License

GNU Affero General Public License v3.0 - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see our [CONTRIBUTING](CONTRIBUTING.md) guide for details on how to get started.

For major changes, please open an issue first to discuss what you would like to change.