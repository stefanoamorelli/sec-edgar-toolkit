/** Live E2E for the TS instance-XBRL and coverage features. */
const os = require('os');
const fs = require('fs');
const path = require('path');
const {
  Company, ThirteenF, fullTextSearch, searchFilings, setIdentity,
} = require('../dist/index.js');

const failures = [];
function check(name, condition, detail = '') {
  console.log(`[${condition ? 'PASS' : 'FAIL'}] ${name} ${detail}`);
  if (!condition) failures.push(name);
}

async function main() {
  const cacheDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edgar-cache-'));
  setIdentity(process.env.SEC_EDGAR_TOOLKIT_USER_AGENT || 'sec-edgar-toolkit-e2e/1.0 (dev@example.com)', { diskCacheDir: cacheDir });

  // as-reported statements
  const apple = await Company.lookup('AAPL');
  const tenK = (await apple.getFilings({ form: '10-K' })).latest();
  const xbrl = tenK.xbrl();
  const stmt = (await xbrl.getStatement('CONSOLIDATEDSTATEMENTSOFOPERATIONS')).filter((i) => i.hasValues);
  const net = stmt.find((i) => i.concept === 'us-gaap:NetIncomeLoss' && Object.keys(i.dimensions).length === 0);
  check('as-reported income statement', net && net.values['2025-09-27'] === 112010000000);
  check('presentation order', stmt[0].concept.endsWith('AssessedTax'), stmt[0].baseLabel);
  const eps = stmt.find((i) => i.concept === 'us-gaap:EarningsPerShareBasic');
  check('as-reported EPS', eps && eps.values['2025-09-27'] === 7.49);
  const seg = await xbrl.getStatement('SegmentInformationandGeographicDataInformationbyReportableSegmentDetails');
  const members = new Set(seg.filter((i) => Object.keys(i.dimensions).length > 0).map((i) => i.section));
  check('dimensional segment rows', Array.from(members).some((m) => m.includes('Americas')), `signatures=${members.size}`);

  // full-text search
  const results = await fullTextSearch('"substantial doubt"', { forms: '10-K' });
  check('fullTextSearch', results.total > 100, `total=${results.total}`);
  const found = await searchFilings('"supply chain"', { forms: '8-K' });
  check('searchFilings -> Filing objects', found.length > 0 && Boolean(found[0].accessionNumber));

  // typed exhibits + press release by type
  const eightKFiling = (await apple.getFilings({ form: '8-K' })).latest();
  const exhibits = await eightKFiling.getExhibits();
  check('typed exhibits', exhibits.some((a) => a.type.startsWith('EX-99')), JSON.stringify(exhibits.slice(0, 2).map((a) => a.type)));
  const eightK = await eightKFiling.obj();
  check('press release via exhibit type', eightK.hasPressRelease === true);

  // 13F
  const brk = await Company.lookup('1067983');
  const tf = await (await brk.getFilings({ form: '13F-HR' })).latest().obj();
  check('13F obj() type', tf.constructor.name === 'ThirteenF');
  check('13F holdings parsed', tf.holdingCount > 50, `n=${tf.holdingCount}`);
  check('13F manager', tf.managerName.includes('Berkshire'), tf.managerName);
  check('13F totals', tf.totalValue > 1e11, `$${(tf.totalValue / 1e9).toFixed(1)}B`);
  check('13F issuer lookup', tf.byIssuer('apple').length > 0);

  // multi-owner Form 4
  let multi = null;
  for (const filing of await brk.getFilings({ form: '4', limit: 10 })) {
    const form = await filing.obj();
    if (form.owners && form.owners.length >= 2) { multi = form; break; }
  }
  check('multi-owner Form 4', multi !== null, multi ? `${multi.owners.length} owners: ${multi.owners.map((o) => o.name).slice(0, 2)}` : '');

  // footnotes
  const f4 = await (await apple.getFilings({ form: '4' })).latest().obj();
  check('Form4 owners + footnotes', f4.owners.length >= 1 && typeof f4.footnotes === 'object', `${f4.owners[0]?.name} fn=${Object.keys(f4.footnotes).length}`);

  // 20-F IFRS financials
  const tsm = await Company.lookup('1046179');
  const twentyF = (await tsm.getFilings({ form: '20-F' })).latest();
  check('20-F located', twentyF !== null, String(twentyF && twentyF.filingDate));
  const fin = await tsm.getFinancials();
  Object.defineProperty(fin, 'formType', { value: '20-F' });
  const income = fin.incomeStatement();
  check('IFRS income statement rows', income.rows.length > 3, `rows=${income.rows.length}`);
  check('IFRS concepts present', income.rows.some((r) => r.concept === 'Revenue' || r.concept === 'ProfitLoss'));

  // amendments flag
  const plain = await apple.getFilings({ form: '10-K' });
  const withA = await apple.getFilings({ form: '10-K', amendments: true });
  check('amendments superset', withA.length >= plain.length);

  // disk cache
  const bodies = fs.readdirSync(cacheDir).filter((f) => f.endsWith('.body'));
  check('disk cache populated', bodies.length > 10, `${bodies.length} cached responses`);
  const t0 = Date.now();
  const apple2 = await Company.lookup('AAPL');
  await apple2.getFilings({ form: '10-K' });
  check('cache warm read', Date.now() - t0 < 500, `${Date.now() - t0}ms`);

  console.log('');
  if (failures.length > 0) {
    console.log(`FAILURES (${failures.length}): ${JSON.stringify(failures)}`);
    process.exit(1);
  }
  console.log('ALL TS FEATURE E2E CHECKS PASSED');
}

main().catch((e) => { console.error('E2E crashed:', e); process.exit(1); });
