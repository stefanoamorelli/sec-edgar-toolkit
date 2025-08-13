# SEC EDGAR Toolkit

[![npm version](https://badge.fury.io/js/sec-edgar-toolkit.svg)](https://badge.fury.io/js/sec-edgar-toolkit)
[![PyPI version](https://badge.fury.io/py/sec-edgar-toolkit.svg)](https://badge.fury.io/py/sec-edgar-toolkit)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![TypeScript CI](https://github.com/stefanoamorelli/sec-edgar-toolkit/actions/workflows/typescript-ci.yml/badge.svg)](https://github.com/stefanoamorelli/sec-edgar-toolkit/actions/workflows/typescript-ci.yml)
[![Python CI](https://github.com/stefanoamorelli/sec-edgar-toolkit/actions/workflows/python-ci.yml/badge.svg)](https://github.com/stefanoamorelli/sec-edgar-toolkit/actions/workflows/python-ci.yml)
[![Docker](https://img.shields.io/badge/docker-available-blue.svg)](https://hub.docker.com/r/stefanoamorelli/sec-edgar-toolkit)
[![codecov](https://codecov.io/gh/stefanoamorelli/sec-edgar-toolkit/branch/main/graph/badge.svg)](https://codecov.io/gh/stefanoamorelli/sec-edgar-toolkit)

Open source toolkit to facilitate working with the [SEC EDGAR database](https://www.sec.gov/edgar/searchedgar/companysearch).

## Disclaimer

This toolkit is not affiliated with, endorsed by, or maintained by the U.S. Securities and Exchange Commission (SEC). It is an independent, open-source project designed to facilitate access to publicly available EDGAR data.

## Overview

The SEC EDGAR Toolkit provides easy-to-use libraries for both TypeScript/JavaScript and Python developers to access and work with SEC filing data from the EDGAR database. This monorepo contains:

- **TypeScript Package**: Full-featured TypeScript/JavaScript library with type safety
- **Python Package**: Pythonic interface for data analysis and research

## Features

- Search and retrieve SEC filings (10-K, 10-Q, 8-K, etc.)
- Parse and extract structured data from filings
- Extract individual items from filings (Item 1, Item 1A, etc.)
- XML parsing for SEC ownership forms (Forms 3, 4, and 5)
- High-performance async/await support
- Available for both npm and pip installation
- Type-safe interfaces (TypeScript) and type hints (Python)
- Rate limiting and retry logic built-in
- Comprehensive documentation and examples

## Functionality Comparison

| Feature | TypeScript/JavaScript | Python |
|---------|----------------------|--------|
| Company Search | ✅ By ticker, CIK, name | ✅ By ticker, CIK, name |
| Filing Retrieval | ✅ All filing types | ✅ All filing types |
| Date Filtering | ✅ From/to date ranges | ✅ From/to date ranges |
| XBRL Data Access | ✅ Company facts, concepts, frames | ✅ Company facts, concepts, frames |
| XML Parsing | ✅ Forms 3, 4, 5 | ✅ Forms 3, 4, 5 |
| Item Extraction | ✅ 10-K, 10-Q, 8-K items | ✅ 10-K, 10-Q, 8-K items |
| Rate Limiting | ✅ Automatic (10 req/sec) | ✅ Automatic (10 req/sec) |
| Retry Logic | ✅ Exponential backoff | ✅ Exponential backoff |
| Type Safety | ✅ Full TypeScript types | ✅ Type hints (mypy) |
| Async Support | ✅ Promise-based | ✅ async/await |
| Error Handling | ✅ Typed exceptions | ✅ Typed exceptions |
| User Agent | ✅ Required | ✅ Required |
| Caching | ❌ | ✅ 24-hour ticker cache |

## Installation

### TypeScript/JavaScript

```bash
pnpm add sec-edgar-toolkit
# or
npm install sec-edgar-toolkit
# or
yarn add sec-edgar-toolkit
```

### Python

```bash
pip install sec-edgar-toolkit
```

## Quick Start

### TypeScript/JavaScript

```typescript
import { createClient } from 'sec-edgar-toolkit';

const client = createClient({
  userAgent: "YourApp/1.0 (your.email@example.com)"
});

// Find company and get filings
const company = await client.companies.lookup("AAPL");
const filings = await company.filings.formTypes(["10-K"]).recent(5).fetch();

// Extract items from filing
const filing = filings[0];
const items = await filing.extractItems(); // Get all items
const riskFactors = await filing.getItem("1A"); // Get specific item
```

### Python

```python
from sec_edgar_toolkit import create_client

client = create_client("YourApp/1.0 (your.email@example.com)")

# Find company and get filings
company = client.companies.lookup("AAPL")
filings = company.filings.form_types(["10-K"]).recent(5).fetch()

# Extract items from filing
filing = filings[0]
items = filing.extract_items()  # Get all items
risk_factors = filing.get_item("1A")  # Get specific item
```

### Item Extraction

Extract individual items from SEC filings:

```python
# Python example
filing = company.get_filing("10-K")
items = filing.extract_items()

# Output structure:
{
  "1": "Item 1. Business\nThe Company designs, manufactures...",
  "1A": "Item 1A. Risk Factors\nThe Company's business...", 
  "1B": "Item 1B. Unresolved Staff Comments\nNone.",
  "2": "Item 2. Properties\nThe Company's headquarters...",
  # ... all other items
}
```

## Docker Development

This project includes Docker support for both development and production environments.

### Available Docker Images

- **`sec-edgar-toolkit:typescript`** - TypeScript/Node.js production image
- **`sec-edgar-toolkit:python`** - Python production image  
- **`sec-edgar-toolkit:dev`** - Combined development environment

### Building Images

```bash
# Build specific targets
docker build --target typescript -t sec-edgar-toolkit:typescript .
docker build --target python -t sec-edgar-toolkit:python .
docker build --target dev -t sec-edgar-toolkit:dev .
```

### Development with Docker Compose

```bash
# TypeScript development with hot reload
docker-compose up typescript-dev

# Python development with test coverage
docker-compose up python-dev

# Combined interactive development environment
docker-compose up dev

# Production builds
docker-compose up typescript-prod python-prod
```

### Development Workflow

1. **TypeScript Development:**
   ```bash
   docker-compose up typescript-dev
   # Runs tests in watch mode on http://localhost:3000
   ```

2. **Python Development:**
   ```bash
   docker-compose up python-dev  
   # Runs pytest with coverage reports
   ```

3. **Interactive Development:**
   ```bash
   docker-compose up dev
   # Combined environment with both TypeScript and Python
   # Access via: docker-compose exec dev bash
   ```

## Documentation

- [TypeScript Documentation](./typescript/README.md)
- [Python Documentation](./python/README.md)

## Acknowledgements and Thanks

This project was inspired by and builds upon the excellent work of the SEC EDGAR community. Special thanks to the maintainers and contributors of these projects that have paved the way for accessible financial data:

### Python Community
- **[python-edgar](https://pypi.org/project/python-edgar/)** - For pioneering Python-based EDGAR access
- **[sec-api](https://github.com/janlukasschroeder/sec-api-python)** - For demonstrating clean API design patterns
- **[edgar-crawler](https://github.com/nlpaueb/edgar-crawler)** - For innovative approaches to document parsing
- **[pyedgar](https://github.com/gaulinmp/pyedgar)** - For comprehensive filing download capabilities
- **[sec-edgar-downloader](https://github.com/jadchaar/sec-edgar-downloader)** - For simplified bulk download functionality

### JavaScript/TypeScript Community
- **[sec-api](https://github.com/janlukasschroeder/sec-api)** - For bringing EDGAR data to the Node.js ecosystem

### R Community
- **[edgarWebR](https://github.com/mwaldstein/edgarWebR)** - For making EDGAR data accessible to data scientists using R

We're grateful for the open-source community's collective effort in democratizing access to public financial data. This toolkit aims to contribute to this ecosystem by providing a modern, type-safe, and multi-language solution.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This software is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

This means:
- You can use, modify, and distribute this software
- If you modify and distribute it, you must release your changes under AGPL-3.0
- If you run a modified version on a server, you must provide the source code to users

For commercial licensing options or other licensing inquiries, please contact stefano@amorelli.tech.

See the [LICENSE](LICENSE) file for the full license text.

---

Copyright © 2025 [Stefano Amorelli](https://amorelli.tech). All rights reserved.
