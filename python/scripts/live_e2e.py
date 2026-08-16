"""Live E2E smoke test of the sec-edgar-toolkit object API against SEC EDGAR."""

import os
import sys

from sec_edgar_toolkit import (
    Company,
    Financials,
    get_current_filings,
    set_identity,
)

FAIL = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAIL.append(name)
    print(f"[{status}] {name} {detail}")


set_identity(os.environ.get("SEC_EDGAR_TOOLKIT_USER_AGENT", "sec-edgar-toolkit-e2e/1.0 (dev@example.com)"))

# --- Company ---
apple = Company("AAPL")
check("Company by ticker", apple.cik == "0000320193", apple.cik)
check("Company name", "Apple" in apple.name, apple.name)
check("Company sic", bool(apple.sic), f"sic={apple.sic}")
check("Company sic_description", bool(apple.sic_description))
check("Company state", bool(apple.state_of_incorporation))
check("Company fiscal_year_end", bool(apple.fiscal_year_end))
check("Company tickers", "AAPL" in apple.tickers, apple.tickers)

by_cik = Company("320193")
check("Company by short CIK", by_cik.cik == "0000320193")

# --- Filings collection ---
filings_10k = apple.get_filings(form="10-K")
check("get_filings(10-K) non-empty", len(filings_10k) > 0, f"n={len(filings_10k)}")
latest_10k = filings_10k.latest()
check("latest() works", latest_10k is not None, str(latest_10k))
check(
    "newest-first ordering",
    all(
        str(filings_10k[i].filing_date) >= str(filings_10k[i + 1].filing_date)
        for i in range(len(filings_10k) - 1)
    ),
)
check("filing_date has isoformat", hasattr(latest_10k.filing_date, "isoformat"))
check("filing.form alias", latest_10k.form == "10-K")
check("filing.file_number", bool(latest_10k.file_number), latest_10k.file_number)
check("filing.acceptance_datetime", bool(latest_10k.acceptance_datetime))
check("filing.period_of_report", bool(latest_10k.period_of_report))

form_list = apple.get_filings(form=["3", "4", "5"], limit=10)
check("get_filings(form list)", len(form_list) > 0, f"n={len(form_list)}")

# --- Filing text ---
text = latest_10k.text()
check("filing.text() works", len(text) > 100_000, f"chars={len(text)}")

# --- 10-K obj() ---
tenk = latest_10k.obj()
check("10-K obj() type", type(tenk).__name__ == "TenK", type(tenk).__name__)
check("10-K risk_factors", hasattr(tenk, "risk_factors") and len(tenk.risk_factors) > 1000)
check("10-K business", hasattr(tenk, "business") and len(tenk.business) > 500)
check("10-K mda", hasattr(tenk, "mda") and len(tenk.mda) > 500)
check("10-K financials attr", hasattr(tenk, "financials"))

# --- 8-K obj() ---
eightk_filing = apple.get_filings(form="8-K").latest()
eightk = eightk_filing.obj()
check("8-K obj() type", type(eightk).__name__ == "EightK", type(eightk).__name__)
check("8-K items", len(eightk.items) > 0, eightk.items)
check("8-K has_item", eightk.has_item(eightk.items[0]) if eightk.items else False)
check("8-K date_of_report", bool(eightk.date_of_report), eightk.date_of_report)
print(f"       press_release={eightk.has_press_release} {eightk.press_releases[:1]}")

# --- Form 4 obj() ---
form4_filing = apple.get_filings(form="4").latest()
form4 = form4_filing.obj()
check("Form4 obj() type", type(form4).__name__ == "OwnershipForm", type(form4).__name__)
check("Form4 owner_name", bool(form4.owner_name), form4.owner_name)
check(
    "Form4 relationship flags",
    isinstance(form4.is_director, bool) and isinstance(form4.is_officer, bool),
    f"director={form4.is_director} officer={form4.is_officer}",
)
tx_or_holding = bool(form4.transactions) or bool(form4.holdings)
check("Form4 transactions/holdings", tx_or_holding,
      f"tx={len(form4.transactions)} holdings={len(form4.holdings)}")
if form4.transactions:
    tx = form4.transactions[0]
    print(f"       tx: date={tx.transaction_date} code={tx.transaction_code} "
          f"shares={tx.shares} price={tx.price_per_share} after={tx.shares_owned_after} "
          f"A/D={tx.acquisition_or_disposition}")

# --- Facts ---
facts = apple.get_facts()
check("facts truthy", bool(facts))
check("facts.data us-gaap", "us-gaap" in facts.data)
rev = facts.get_fact("RevenueFromContractWithCustomerExcludingAssessedTax")
check("get_fact DataFrame", rev is not None and not rev.empty, f"rows={0 if rev is None else len(rev)}")
if rev is not None and not rev.empty:
    last = rev.iloc[-1]
    check("get_fact columns", all(c in rev.columns for c in ["fy", "fp", "value", "unit", "form", "end"]))
    print(f"       latest revenue: {last['value']:,} {last['unit']} end={last['end']}")

# --- Financials ---
fin = Financials.extract(latest_10k)
inc = fin.income_statement()
bal = fin.balance_sheet()
cf = fin.cash_flow()
check("income_statement DataFrame", hasattr(inc, "to_dict") and not inc.empty, f"shape={inc.shape}")
check("balance_sheet DataFrame", not bal.empty, f"shape={bal.shape}")
check("cash_flow DataFrame", not cf.empty, f"shape={cf.shape}")
check("NetIncomeLoss in income stmt", "NetIncomeLoss" in inc.index)

# --- XBRL filing-scoped statements ---
xbrl = latest_10k.xbrl()
statements = xbrl.get_all_statements()
check("get_all_statements", len(statements) > 10, f"n={len(statements)}")
segment_stmts = [
    s for s in statements
    if "segment" in s.get("definition", "").lower() and "detail" in s.get("definition", "").lower()
]
check("segment statements found", len(segment_stmts) > 0, f"n={len(segment_stmts)}")
if segment_stmts:
    stmt = xbrl.get_statement(segment_stmts[0]["role"])
    with_values = [i for i in stmt if i.get("has_values")]
    check("get_statement line items", len(with_values) > 0, f"items={len(stmt)} with_values={len(with_values)}")
    if with_values:
        item = with_values[0]
        print(f"       sample: {item['label'][:60]} -> {list(item['values'].items())[:1]} concept={item['concept'][:40]}")

# query API
q = xbrl.query("concept=Assets")
check("query('concept=X')", len(q) > 0, f"n={len(q)}")
df = q.to_dataframe()
check("query.to_dataframe", not df.empty and "concept" in df.columns)
q_all = xbrl.query("")
check("query('').by_concept", len(q_all.by_concept("NetIncomeLoss")) > 0)
hist = xbrl.facts.facts_history("Assets")
check("facts_history", not hist.empty, f"rows={len(hist)}")

# find_statement with CamelCase
fs = xbrl.find_statement("BalanceSheet")
check("find_statement CamelCase", fs is not None and bool(fs.get("data")))

# --- Global current filings ---
current = get_current_filings(form="8-K", page_size=10)
check("get_current_filings", len(current) > 0, f"n={len(current)}")
if current:
    f = current[0]
    check("current filing fields", bool(f.accession_number) and bool(f.company_name))

print()
if FAIL:
    print(f"FAILURES ({len(FAIL)}): {FAIL}")
    sys.exit(1)
print("ALL TOOLKIT E2E CHECKS PASSED")
