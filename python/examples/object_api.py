"""
Object-style API example.

Demonstrates the sec_edgar_toolkit.compat interface: identity setup,
company lookup, filings with .latest(), form objects, facts, and XBRL.

Run with:
    SEC_EDGAR_TOOLKIT_USER_AGENT="MyApp/1.0 (me@example.com)" python object_api.py
"""

from sec_edgar_toolkit.compat import (
    Company,
    get_current_filings,
    set_identity,
)


def main() -> None:
    set_identity("SecEdgarToolkitExample/1.0 (example@example.com)")

    # Company lookup by ticker or CIK
    company = Company("AAPL")
    print(f"{company.name} (CIK {company.cik}, {company.exchange})")
    print(f"SIC: {company.sic} - {company.sic_description}")

    # Filings, newest first, with .latest()
    latest_10k = company.get_filings(form="10-K").latest()
    print(f"Latest 10-K: {latest_10k.accession_number} on {latest_10k.filing_date}")

    # Form-specific objects
    tenk = latest_10k.obj()
    if hasattr(tenk, "risk_factors"):
        print(f"Risk factors: {len(tenk.risk_factors)} characters")

    # Company facts
    facts = company.get_facts()
    revenue = facts.get_fact("RevenueFromContractWithCustomerExcludingAssessedTax")
    if revenue is not None:
        latest = revenue.iloc[-1]
        print(f"Latest revenue: {latest['value']:,} {latest['unit']} ({latest['end']})")

    # Filing-scoped XBRL statements
    xbrl = latest_10k.xbrl()
    statements = xbrl.get_all_statements()
    print(f"Rendered reports in the filing: {len(statements)}")

    # Global recent filings feed
    recent = get_current_filings(form="8-K", page_size=5)
    for filing in recent:
        print(f"  {filing.filing_date} {filing.company_name}: {filing.form_type}")


if __name__ == "__main__":
    main()
