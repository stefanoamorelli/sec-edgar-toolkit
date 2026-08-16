/** Live E2E of the sec-edgar-toolkit TypeScript object API against SEC EDGAR. */

const {
  Company,
  Financials,
  getCurrentFilings,
  setIdentity,
  TenKItem,
  EightKItem,
} = require('../dist/index.js');

const failures = [];

function check(name, condition, detail = '') {
  const status = condition ? 'PASS' : 'FAIL';
  if (!condition) failures.push(name);
  console.log(`[${status}] ${name} ${detail}`);
}

async function main() {
  setIdentity(process.env.SEC_EDGAR_TOOLKIT_USER_AGENT || 'sec-edgar-toolkit-e2e/1.0 (dev@example.com)');

  // --- Company ---
  const apple = await Company.lookup('AAPL');
  check('Company by ticker', apple.cik === '0000320193', apple.cik);
  check('Company name', apple.name.includes('Apple'), apple.name);
  check('Company sic', Boolean(await apple.sic()), `sic=${await apple.sic()}`);
  check('Company sicDescription', Boolean(await apple.sicDescription()));
  check('Company state', Boolean(await apple.stateOfIncorporation()));
  check('Company tickers', (await apple.tickers()).includes('AAPL'));

  const byCik = await Company.lookup('320193');
  check('Company by short CIK', byCik.cik === '0000320193');

  // --- Filings collection ---
  const tenKs = await apple.getFilings({ form: '10-K' });
  check('getFilings(10-K) non-empty', tenKs.length > 0, `n=${tenKs.length}`);
  const latest10K = tenKs.latest();
  check('latest() works', latest10K !== null, String(latest10K));
  check(
    'newest-first ordering',
    tenKs.every((f, i) => i === 0 || tenKs[i - 1].filingDate >= f.filingDate)
  );
  check('filing.fileNumber', Boolean(latest10K.fileNumber), latest10K.fileNumber);
  check('filing.acceptanceDatetime', Boolean(latest10K.acceptanceDatetime));
  check('filing.periodOfReport', Boolean(latest10K.periodOfReport));

  const formList = await apple.getFilings({ form: ['3', '4', '5'], limit: 10 });
  check('getFilings(form list)', formList.length > 0, `n=${formList.length}`);

  // --- Filing text ---
  const text = await latest10K.text();
  check('filing.text() works', text.length > 100000, `chars=${text.length}`);

  // --- 10-K obj() ---
  const tenK = await latest10K.obj();
  check('10-K obj() type', tenK.constructor.name === 'TenK', tenK.constructor.name);
  check('10-K riskFactors', Boolean(tenK.riskFactors) && tenK.riskFactors.length > 1000);
  check('10-K business', Boolean(tenK.business) && tenK.business.length > 500);
  check('10-K mda', Boolean(tenK.mda) && tenK.mda.length > 500);

  // Enum-based item access
  const mda = await latest10K.getItem(TenKItem.MANAGEMENT_DISCUSSION_AND_ANALYSIS);
  check('getItem(TenKItem enum)', Boolean(mda) && mda.length > 500);

  // --- 8-K obj() ---
  const latest8K = (await apple.getFilings({ form: '8-K' })).latest();
  const eightK = await latest8K.obj();
  check('8-K obj() type', eightK.constructor.name === 'EightK', eightK.constructor.name);
  check('8-K items', eightK.items.length > 0, JSON.stringify(eightK.items));
  check('8-K hasItem(enum)', eightK.hasItem(EightKItem.RESULTS_OF_OPERATIONS));
  check('8-K dateOfReport', Boolean(eightK.dateOfReport), eightK.dateOfReport);
  console.log(
    `       pressRelease=${eightK.hasPressRelease} ${JSON.stringify(eightK.pressReleases.slice(0, 1))}`
  );
  check('8-K press release detected', eightK.hasPressRelease === true);

  // --- Form 4 obj() ---
  const form4Filing = (await apple.getFilings({ form: '4' })).latest();
  const form4 = await form4Filing.obj();
  check('Form4 obj() type', form4.constructor.name === 'OwnershipForm', form4.constructor.name);
  check('Form4 ownerName', Boolean(form4.ownerName), form4.ownerName);
  check(
    'Form4 relationship flags',
    typeof form4.isDirector === 'boolean' && typeof form4.isOfficer === 'boolean',
    `director=${form4.isDirector} officer=${form4.isOfficer}`
  );
  check(
    'Form4 transactions/holdings',
    form4.transactions.length > 0 || form4.holdings.length > 0,
    `tx=${form4.transactions.length} holdings=${form4.holdings.length}`
  );
  if (form4.transactions.length > 0) {
    const tx = form4.transactions[0];
    console.log(
      `       tx: date=${tx.transactionDate} code=${tx.transactionCode} shares=${tx.shares} ` +
        `price=${tx.pricePerShare} after=${tx.sharesOwnedAfter} A/D=${tx.acquisitionOrDisposition}`
    );
  }

  // --- Facts ---
  const facts = await apple.getFacts();
  check('facts non-empty', !facts.isEmpty);
  check('facts.data us-gaap', 'us-gaap' in facts.data);
  const revenue = facts.getFact('RevenueFromContractWithCustomerExcludingAssessedTax');
  check('getFact rows', revenue !== null && revenue.length > 0, `rows=${revenue ? revenue.length : 0}`);
  if (revenue) {
    const last = revenue[revenue.length - 1];
    check(
      'getFact row fields',
      last.fy != null && last.value != null && Boolean(last.unit) && Boolean(last.end)
    );
    console.log(`       latest revenue: ${last.value.toLocaleString()} ${last.unit} end=${last.end}`);
  }

  // --- Financials ---
  const financials = await Financials.extract(latest10K);
  const income = financials.incomeStatement();
  const balance = financials.balanceSheet();
  const cashFlow = financials.cashFlow();
  check('incomeStatement table', income.rows.length > 5, `rows=${income.rows.length} periods=${income.periods.length}`);
  check('balanceSheet table', balance.rows.length > 5, `rows=${balance.rows.length}`);
  check('cashFlow table', cashFlow.rows.length > 3, `rows=${cashFlow.rows.length}`);
  check(
    'NetIncomeLoss in income stmt',
    income.rows.some((row) => row.concept === 'NetIncomeLoss')
  );

  // --- XBRL filing-scoped statements ---
  const xbrl = latest10K.xbrl();
  const statements = await xbrl.getAllStatements();
  check('getAllStatements', statements.length > 10, `n=${statements.length}`);
  const segmentStatements = statements.filter(
    (s) =>
      s.definition.toLowerCase().includes('segment') &&
      s.definition.toLowerCase().includes('detail')
  );
  check('segment statements found', segmentStatements.length > 0, `n=${segmentStatements.length}`);
  if (segmentStatements.length > 0) {
    const statement = await xbrl.getStatement(segmentStatements[0].role);
    const withValues = statement.filter((item) => item.hasValues);
    check(
      'getStatement line items',
      withValues.length > 0,
      `items=${statement.length} withValues=${withValues.length}`
    );
    if (withValues.length > 0) {
      const item = withValues[0];
      const firstPeriod = Object.entries(item.values)[0];
      console.log(
        `       sample: ${item.label.slice(0, 60)} -> ${JSON.stringify(firstPeriod)} concept=${item.concept.slice(0, 40)}`
      );
    }
    const sectioned = statement.filter((i) => i.hasValues && i.section !== '');
    check('segment members carry sections', sectioned.length > 0, `sectioned=${sectioned.length}`);
    if (false) {
    }
  }

  // --- query API ---
  const assetsFacts = await xbrl.query({ concept: 'Assets' });
  check('query({concept})', assetsFacts.length > 0, `n=${assetsFacts.length}`);
  check(
    'query record fields',
    assetsFacts[0].context !== undefined || assetsFacts[0].period_instant !== undefined
  );
  const history = await xbrl.factsHistory('Assets');
  check('factsHistory', history.length > 0, `rows=${history.length}`);

  // findStatement with CamelCase
  const balanceSheet = await xbrl.findStatement('BalanceSheet');
  check(
    'findStatement CamelCase',
    balanceSheet !== null && Object.keys(balanceSheet.data).length > 0
  );

  // --- Global current filings ---
  const current = await getCurrentFilings('8-K', 10);
  check('getCurrentFilings', current.length > 0, `n=${current.length}`);
  if (current.length > 0) {
    check(
      'current filing fields',
      Boolean(current[0].accessionNumber) && Boolean(current[0].companyName)
    );
  }

  console.log('');
  if (failures.length > 0) {
    console.log(`FAILURES (${failures.length}): ${JSON.stringify(failures)}`);
    process.exit(1);
  }
  console.log('ALL TYPESCRIPT E2E CHECKS PASSED');
}

main().catch((error) => {
  console.error('E2E crashed:', error);
  process.exit(1);
});
