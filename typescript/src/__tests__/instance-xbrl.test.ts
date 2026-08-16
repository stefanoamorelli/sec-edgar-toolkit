/**
 * Tests for the instance-XBRL layer and the coverage features.
 */

import { AsReportedStatements } from "../core/xbrl/as-reported";
import { InstanceDocument } from "../core/xbrl/instance-document";
import { LabelLinkbase, PresentationLinkbase } from "../core/xbrl/linkbases";
import { parseFilingIndexHtml } from "../core/exhibits";
import { OwnershipForm } from "../core/ownership";
import { ThirteenF } from "../core/form-13f";
import { ThirteenFParser } from "../parsers/thirteenf";
import { OwnershipFormParser } from "../parsers/ownership-forms";
import { ItemExtractor } from "../parsers/item-extractor";
import { DiskCache } from "../utils/disk-cache";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const INSTANCE_XML = `<?xml version="1.0" encoding="utf-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
  xmlns:us-gaap="http://fasb.org/us-gaap/2025"
  xmlns:srt="http://fasb.org/srt/2025"
  xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
  xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:href="t.xsd" xlink:type="simple"/>
  <context id="d1">
    <entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier></entity>
    <period><startDate>2024-01-01</startDate><endDate>2024-12-31</endDate></period>
  </context>
  <context id="d2">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000000001</identifier>
      <segment>
        <xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">us-gaap:ProductMember</xbrldi:explicitMember>
      </segment>
    </entity>
    <period><startDate>2024-01-01</startDate><endDate>2024-12-31</endDate></period>
  </context>
  <unit id="usd"><measure>iso4217:USD</measure></unit>
  <unit id="perShare"><divide>
    <unitNumerator><measure>iso4217:USD</measure></unitNumerator>
    <unitDenominator><measure>shares</measure></unitDenominator>
  </divide></unit>
  <us-gaap:Revenues contextRef="d1" unitRef="usd" decimals="0">1000</us-gaap:Revenues>
  <us-gaap:Revenues contextRef="d2" unitRef="usd" decimals="0">600</us-gaap:Revenues>
  <us-gaap:EarningsPerShareBasic contextRef="d1" unitRef="perShare" decimals="2">2.50</us-gaap:EarningsPerShareBasic>
</xbrl>`;

const PRE_XML = `<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
<link:presentationLink xlink:role="http://example.com/role/Income" xlink:type="extended">
  <link:loc xlink:type="locator" xlink:label="loc_abs" xlink:href="x.xsd#us-gaap_IncomeStatementAbstract"/>
  <link:loc xlink:type="locator" xlink:label="loc_rev" xlink:href="x.xsd#us-gaap_Revenues"/>
  <link:loc xlink:type="locator" xlink:label="loc_eps" xlink:href="x.xsd#us-gaap_EarningsPerShareBasic"/>
  <link:loc xlink:type="locator" xlink:label="loc_member" xlink:href="x.xsd#us-gaap_ProductMember"/>
  <link:presentationArc order="2" xlink:from="loc_abs" xlink:to="loc_eps" xlink:type="arc"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"/>
  <link:presentationArc order="1" xlink:from="loc_abs" xlink:to="loc_rev" xlink:type="arc"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"/>
  <link:presentationArc order="3" xlink:from="loc_abs" xlink:to="loc_member" xlink:type="arc"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"/>
</link:presentationLink>
</link:linkbase>`;

const LAB_XML = `<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
<link:labelLink xlink:role="http://www.xbrl.org/2003/role/link">
  <link:loc xlink:type="locator" xlink:label="loc_rev" xlink:href="x.xsd#us-gaap_Revenues"/>
  <link:label xlink:type="resource" xlink:label="lab_rev"
    xlink:role="http://www.xbrl.org/2003/role/label" xml:lang="en-US">Total revenue</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc_rev" xlink:to="lab_rev"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>
</link:labelLink>
</link:linkbase>`;

describe("InstanceDocument", () => {
  it("parses contexts, units, dimensions, and facts", () => {
    const doc = InstanceDocument.parse(INSTANCE_XML);

    expect(doc.contexts.get("d1")!.endDate).toBe("2024-12-31");
    expect(doc.contexts.get("d2")!.dimensions).toEqual({
      "srt:ProductOrServiceAxis": "us-gaap:ProductMember",
    });
    expect(doc.units.get("usd")).toBe("USD");
    expect(doc.units.get("perShare")).toBe("USD/shares");
    expect(doc.factsFor("us-gaap:Revenues")).toHaveLength(2);
    expect(
      doc.numericValue(doc.factsFor("us-gaap:EarningsPerShareBasic")[0]),
    ).toBe(2.5);
  });
});

describe("Linkbases", () => {
  it("orders presentation concepts and resolves roles", () => {
    const pre = PresentationLinkbase.parse(PRE_XML);
    const role = pre.findRole("Income");
    expect(role).toBe("http://example.com/role/Income");

    const concepts = pre.orderedConcepts(role!).map((n) => n.concept);
    expect(concepts[0]).toBe("us-gaap:IncomeStatementAbstract");
    expect(concepts.indexOf("us-gaap:Revenues")).toBeLessThan(
      concepts.indexOf("us-gaap:EarningsPerShareBasic"),
    );
  });

  it("resolves labels", () => {
    const lab = LabelLinkbase.parse(LAB_XML);
    expect(lab.labelFor("us-gaap:Revenues")).toBe("Total revenue");
  });
});

describe("AsReportedStatements", () => {
  it("assembles ordered statements and scopes dimensions to the role", async () => {
    const files: Record<string, string> = {
      "t.xsd": "<schema/>",
      "t_htm.xml": INSTANCE_XML,
      "t_pre.xml": PRE_XML,
      "t_lab.xml": LAB_XML,
    };
    const http = {
      getRaw: async (url: string) => files[url.split("/").pop()!],
    };
    const statements = new AsReportedStatements(
      "http://local",
      http,
      Object.keys(files),
    );
    expect(statements.isAvailable).toBe(true);

    const items = (await statements.getStatement("Income")).filter(
      (i) => i.hasValues,
    );
    expect(items[0].label).toBe("Total revenue");
    expect(items[0].values).toEqual({ "2024-12-31": 1000 });
    expect(items[1].dimensions).toEqual({
      "srt:ProductOrServiceAxis": "us-gaap:ProductMember",
    });
    expect(items[1].values).toEqual({ "2024-12-31": 600 });
  });
});

const FORM4_XML = `<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <periodOfReport>2026-08-11</periodOfReport>
  <issuer><issuerCik>2</issuerCik><issuerName>Test Corp</issuerName>
    <issuerTradingSymbol>TST</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerCik>1</rptOwnerCik><rptOwnerName>HOLDINGS LLC</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isTenPercentOwner>true</isTenPercentOwner></reportingOwnerRelationship>
  </reportingOwner>
  <reportingOwner>
    <reportingOwnerId><rptOwnerCik>2</rptOwnerCik><rptOwnerName>DOE JANE</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>true</isDirector></reportingOwnerRelationship>
  </reportingOwner>
  <footnotes><footnote id="F1">Shares held indirectly.</footnote></footnotes>
</ownershipDocument>`;

describe("Ownership upgrades", () => {
  it("parses every reporting owner and the footnotes", () => {
    const parsed = new OwnershipFormParser(FORM4_XML).parseAll();
    const form = new OwnershipForm(parsed);

    expect(form.owners).toHaveLength(2);
    expect(form.owners[0].name).toBe("HOLDINGS LLC");
    expect(form.owners[0].isTenPercentOwner).toBe(true);
    expect(form.owners[1].isDirector).toBe(true);
    expect(form.footnotes).toEqual({ F1: "Shares held indirectly." });
  });
});

const THIRTEENF_TABLE = `<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer><titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip><value>1000000</value>
    <shrsOrPrnAmt><sshPrnamt>5000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority><Sole>5000</Sole><Shared>0</Shared><None>0</None></votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>OTHER CO</nameOfIssuer><titleOfClass>COM</titleOfClass>
    <cusip>000000000</cusip><value>250000</value>
    <shrsOrPrnAmt><sshPrnamt>100</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
    <putCall>Put</putCall>
    <investmentDiscretion>DFND</investmentDiscretion>
    <votingAuthority><Sole>0</Sole><Shared>100</Shared><None>0</None></votingAuthority>
  </infoTable>
</informationTable>`;

describe("ThirteenF", () => {
  it("parses holdings and summarizes", () => {
    const holdings = new ThirteenFParser(THIRTEENF_TABLE).parseHoldings();
    const report = new ThirteenF(holdings);

    expect(report.holdingCount).toBe(2);
    expect(report.totalValue).toBe(1250000);
    expect(report.topHoldings(1)[0].nameOfIssuer).toBe("APPLE INC");
    expect(report.byIssuer("apple")[0].shares).toBe(5000);
    expect(holdings[1].putCall).toBe("Put");
  });
});

const INDEX_HTML = `<table class="tableFile" summary="Document Format Files">
<tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
<tr><td>1</td><td>10-K</td><td><a href="/Archives/x/doc.htm">doc.htm</a></td><td>10-K</td><td>100</td></tr>
<tr><td>2</td><td>PRESS RELEASE</td><td><a href="/Archives/x/ex99.htm">ex99.htm</a></td><td>EX-99.1</td><td>50</td></tr>
</table>`;

describe("Exhibits", () => {
  it("types documents from the filing index page", () => {
    const records = parseFilingIndexHtml(INDEX_HTML);
    expect(records).toHaveLength(2);
    expect(records[1].type).toBe("EX-99.1");
    expect(records[1].document).toBe("ex99.htm");
  });
});

describe("DiskCache", () => {
  it("expires API responses but keeps archive content", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "edgar-test-cache-"));
    const cache = new DiskCache(dir, 0);

    const apiUrl = "https://data.sec.gov/submissions/CIK1.json";
    cache.set(apiUrl, apiUrl, "api");
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(cache.get(apiUrl, apiUrl)).toBeNull();

    const archiveUrl = "https://www.sec.gov/Archives/edgar/data/1/doc.htm";
    cache.set(archiveUrl, archiveUrl, "archive");
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(cache.get(archiveUrl, archiveUrl)).toBe("archive");
  });
});

describe("20-F items", () => {
  it("supports 20-F item definitions", () => {
    const definitions = new ItemExtractor().getItemDefinitions("20-F");
    const numbers = definitions.map((d) => d.number);
    expect(numbers).toContain("5");
    expect(numbers).toContain("19");
  });
});
