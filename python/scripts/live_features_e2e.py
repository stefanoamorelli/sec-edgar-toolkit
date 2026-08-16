"""Live E2E for the instance-XBRL and coverage features."""

import os
import sys
import tempfile



from sec_edgar_toolkit import (
    Company,
    ThirteenF,
    full_text_search,
    search_filings,
    set_identity,
)

FAIL = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAIL.append(name)
    print(f"[{status}] {name} {detail}")


cache_dir = tempfile.mkdtemp(prefix="edgar-cache-")
set_identity(os.environ.get("SEC_EDGAR_TOOLKIT_USER_AGENT", "sec-edgar-toolkit-e2e/1.0 (dev@example.com)"), cache_dir=cache_dir)

# --- as-reported statements (instance + linkbases) ---
apple = Company("AAPL")
tenk = apple.get_filings(form="10-K").latest()
xbrl = tenk.xbrl()
stmt = [i for i in xbrl.get_statement("CONSOLIDATEDSTATEMENTSOFOPERATIONS") if i["has_values"]]
net = next(i for i in stmt if i["concept"] == "us-gaap:NetIncomeLoss" and not i["dimensions"])
check("as-reported income statement", net["values"].get("2025-09-27") == 112010000000.0)
order_ok = [i["base_label"] for i in stmt[:3]] and stmt[0]["concept"].endswith("AssessedTax")
check("presentation order", bool(order_ok), stmt[0]["base_label"])
eps = next(i for i in stmt if i["concept"] == "us-gaap:EarningsPerShareBasic")
check("as-reported EPS", eps["values"].get("2025-09-27") == 7.49)

bal = [i for i in xbrl.get_statement("CONSOLIDATEDBALANCESHEETS") if i["has_values"]]
assets = next(i for i in bal if i["concept"] == "us-gaap:Assets" and not i["dimensions"])
check("as-reported balance sheet (instant periods)", "2025-09-27" in assets["values"])

# 2012-era filing: old-style instance file name
old = next(f for f in apple.get_filings(form="10-K", deep=True) if str(f.filing_date).startswith("2012"))
ostmt = old.xbrl().as_reported
check("2012 filing instance fileset", ostmt.is_available)

# --- full-text search ---
results = full_text_search('"substantial doubt"', forms="10-K")
check("full_text_search", results["total"] > 100, f"total={results['total']}")
hits = results["hits"]
check("fts hit fields", bool(hits and hits[0]["accession_number"] and hits[0]["cik"]))
filings = search_filings('"supply chain"', forms="8-K")
check("search_filings -> Filing objects", len(filings) > 0 and bool(filings[0].accession_number))

# --- typed exhibits + press release by type ---
eightk_filing = apple.get_filings(form="8-K").latest()
exhibits = eightk_filing.exhibits
check("typed exhibits", any(a.type.startswith("EX-99") for a in exhibits),
      [(a.type, a.document) for a in exhibits[:3]])
eightk = eightk_filing.obj()
check("press release via exhibit type", eightk.has_press_release)

# --- 13F holdings ---
brk = Company("1067983")
tf_filing = brk.get_filings(form="13F-HR").latest()
tf = tf_filing.obj()
check("13F obj() type", type(tf).__name__ == "ThirteenF")
check("13F holdings parsed", tf.holding_count > 50, f"n={tf.holding_count}")
check("13F manager", "Berkshire" in tf.manager_name, tf.manager_name)
apple_pos = tf.by_issuer("apple")
check("13F position lookup", len(apple_pos) > 0 and sum(h.shares for h in apple_pos) > 1e8)
check("13F totals", tf.total_value > 1e11, f"${tf.total_value/1e9:.1f}B")

# --- multiple reporting owners on one Form 4 (Berkshire-style joint filing) ---
oxy_form4s = brk.get_filings(form="4", limit=10)
multi = None
for filing in oxy_form4s:
    form = filing.obj()
    if hasattr(form, "owners") and len(form.owners) >= 2:
        multi = form
        break
if multi is None:
    check("multi-owner Form 4", False, "no joint filing found in sample")
else:
    check("multi-owner Form 4", True,
          f"{len(multi.owners)} owners: {[o.name for o in multi.owners][:3]}")

# --- footnotes + derivative holdings surface ---
f4 = apple.get_filings(form="4").latest().obj()
check("Form4 owners list", len(f4.owners) >= 1, f4.owners[0].name if f4.owners else "")
check("Form4 footnotes dict", isinstance(f4.footnotes, dict), f"n={len(f4.footnotes)}")

# --- foreign filer: TSMC 20-F with IFRS financials ---
tsm = Company("1046179")
twentyf = tsm.get_filings(form="20-F").latest()
check("20-F located", twentyf is not None, str(twentyf))
fin = tsm.get_financials()
fin.form_type = "20-F"
income = fin.income_statement()
check("IFRS income statement rows", not income.empty, f"shape={income.shape}")
check("IFRS concepts present", any(c in income.index for c in ("Revenue", "ProfitLoss")),
      list(income.index)[:4])

# --- amendments flag ---
plain = apple.get_filings(form="10-K")
with_a = apple.get_filings(form="10-K", amendments=True)
check("amendments superset", len(with_a) >= len(plain))

# --- disk cache ---
body_files = len([f for f in os.listdir(cache_dir) if f.endswith(".body")])
check("disk cache populated", body_files > 10, f"{body_files} cached responses")
import time
t0 = time.time()
apple2 = Company("AAPL")
apple2.get_filings(form="10-K")
warm = time.time() - t0
check("cache warm read", warm < 0.5, f"{warm*1000:.0f}ms")

print()
if FAIL:
    print(f"FAILURES ({len(FAIL)}): {FAIL}")
    sys.exit(1)
print("ALL FEATURE E2E CHECKS PASSED")
