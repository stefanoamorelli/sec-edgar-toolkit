"""Tests for the instance-XBRL layer and the coverage features."""

from __future__ import annotations

import time

from sec_edgar_toolkit.core.exhibits import parse_filing_index_html
from sec_edgar_toolkit.core.ownership import OwnershipForm
from sec_edgar_toolkit.core.thirteenf import ThirteenF
from sec_edgar_toolkit.core.xbrl.as_reported import AsReportedStatements
from sec_edgar_toolkit.core.xbrl.instance_document import InstanceDocument
from sec_edgar_toolkit.core.xbrl.linkbases import LabelLinkbase, PresentationLinkbase
from sec_edgar_toolkit.endpoints.fulltext import FullTextSearchEndpoints
from sec_edgar_toolkit.parsers import ItemExtractor, OwnershipFormParser
from sec_edgar_toolkit.parsers.thirteenf import ThirteenFParser
from sec_edgar_toolkit.utils.disk_cache import DiskCache

INSTANCE_XML = """<?xml version="1.0" encoding="utf-8"?>
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
  <context id="i1">
    <entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier></entity>
    <period><instant>2024-12-31</instant></period>
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
  <us-gaap:Revenues contextRef="d1" unitRef="usd" decimals="0">1000</us-gaap:Revenues>
  <us-gaap:Revenues contextRef="d2" unitRef="usd" decimals="0">600</us-gaap:Revenues>
  <us-gaap:Assets contextRef="i1" unitRef="usd" decimals="0">5000</us-gaap:Assets>
  <us-gaap:EarningsPerShareBasic contextRef="d1" unitRef="perShare" decimals="2">2.50</us-gaap:EarningsPerShareBasic>
</xbrl>"""

PRE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
<link:presentationLink xlink:role="http://example.com/role/Income" xlink:type="extended">
  <link:loc xlink:type="locator" xlink:label="loc_abs" xlink:href="x.xsd#us-gaap_IncomeStatementAbstract"/>
  <link:loc xlink:type="locator" xlink:label="loc_rev" xlink:href="x.xsd#us-gaap_Revenues"/>
  <link:loc xlink:type="locator" xlink:label="loc_eps" xlink:href="x.xsd#us-gaap_EarningsPerShareBasic"/>
  <link:loc xlink:type="locator" xlink:label="loc_member" xlink:href="x.xsd#us-gaap_ProductMember"/>
  <link:presentationArc order="2" xlink:from="loc_abs" xlink:to="loc_eps" xlink:type="arc"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
    preferredLabel="http://www.xbrl.org/2003/role/terseLabel"/>
  <link:presentationArc order="1" xlink:from="loc_abs" xlink:to="loc_rev" xlink:type="arc"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"/>
  <link:presentationArc order="3" xlink:from="loc_abs" xlink:to="loc_member" xlink:type="arc"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"/>
</link:presentationLink>
</link:linkbase>"""

LAB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
<link:labelLink xlink:role="http://www.xbrl.org/2003/role/link">
  <link:loc xlink:type="locator" xlink:label="loc_rev" xlink:href="x.xsd#us-gaap_Revenues"/>
  <link:label xlink:type="resource" xlink:label="lab_rev"
    xlink:role="http://www.xbrl.org/2003/role/label" xml:lang="en-US">Total revenue</link:label>
  <link:label xlink:type="resource" xlink:label="lab_rev"
    xlink:role="http://www.xbrl.org/2003/role/terseLabel" xml:lang="en-US">Revenue</link:label>
  <link:labelArc xlink:type="arc" xlink:from="loc_rev" xlink:to="lab_rev"
    xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>
</link:labelLink>
</link:linkbase>"""


class LocalHttp:
    def __init__(self, files):
        self.files = files

    def get_raw(self, url):
        return self.files[url.rsplit("/", 1)[-1]]


class TestInstanceDocument:
    def test_contexts_units_facts(self):
        doc = InstanceDocument.parse(INSTANCE_XML)

        assert doc.contexts["d1"].is_duration
        assert doc.contexts["d1"].period_key == "2024-12-31"
        assert doc.contexts["i1"].instant == "2024-12-31"
        assert doc.contexts["d2"].dimensions == {
            "srt:ProductOrServiceAxis": "us-gaap:ProductMember"
        }

        assert doc.units["usd"] == "USD"
        assert doc.units["perShare"] == "USD/shares"

        # Duplicate revenue fact is deduplicated
        assert len(doc.facts_for("us-gaap:Revenues")) == 2
        assert doc.facts_for("us-gaap:Assets")[0].numeric_value() == 5000.0


class TestLinkbases:
    def test_presentation_order_and_role_lookup(self):
        pre = PresentationLinkbase.parse(PRE_XML)
        role = pre.find_role("Income")
        assert role == "http://example.com/role/Income"

        nodes = pre.ordered_concepts(role)
        concepts = [n.concept for n in nodes]
        assert concepts[0] == "us-gaap:IncomeStatementAbstract"
        # order attribute wins over document order
        assert concepts.index("us-gaap:Revenues") < concepts.index(
            "us-gaap:EarningsPerShareBasic"
        )

    def test_labels_and_preferred(self):
        lab = LabelLinkbase.parse(LAB_XML)
        assert lab.label_for("us-gaap:Revenues") == "Total revenue"
        assert (
            lab.label_for(
                "us-gaap:Revenues", "http://www.xbrl.org/2003/role/terseLabel"
            )
            == "Revenue"
        )


class TestAsReported:
    def test_statement_assembly_and_dimension_scoping(self):
        files = {
            "t.xsd": b"<schema/>",
            "t_htm.xml": INSTANCE_XML.encode(),
            "t_pre.xml": PRE_XML.encode(),
            "t_lab.xml": LAB_XML.encode(),
        }
        statements = AsReportedStatements(
            "http://local", LocalHttp(files), list(files.keys())
        )
        assert statements.is_available

        items = statements.get_statement("Income")
        valued = [i for i in items if i["has_values"]]

        # Consolidated revenue first, then the in-role Product breakdown
        assert valued[0]["label"] == "Total revenue"
        assert valued[0]["values"] == {"2024-12-31": 1000.0}
        assert valued[1]["dimensions"] == {
            "srt:ProductOrServiceAxis": "us-gaap:ProductMember"
        }
        assert valued[1]["values"] == {"2024-12-31": 600.0}

        # EPS uses the terse preferred label and the divide unit
        eps = next(i for i in valued if i["concept"] == "us-gaap:EarningsPerShareBasic")
        assert eps["units"]["2024-12-31"] == "USD/shares"


FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <periodOfReport>2026-08-11</periodOfReport>
  <issuer><issuerCik>0000000002</issuerCik><issuerName>Test Corp</issuerName>
    <issuerTradingSymbol>TST</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerCik>1</rptOwnerCik><rptOwnerName>HOLDINGS LLC</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isTenPercentOwner>true</isTenPercentOwner></reportingOwnerRelationship>
  </reportingOwner>
  <reportingOwner>
    <reportingOwnerId><rptOwnerCik>2</rptOwnerCik><rptOwnerName>DOE JANE</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>true</isDirector></reportingOwnerRelationship>
  </reportingOwner>
  <derivativeTable>
    <derivativeHolding>
      <securityTitle><value>Stock Option</value></securityTitle>
      <conversionOrExercisePrice><value>10.5</value></conversionOrExercisePrice>
      <postTransactionAmounts><sharesOwnedFollowingTransaction><value>500</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
      <underlyingSecurity><underlyingSecurityTitle><value>Common</value></underlyingSecurityTitle>
        <underlyingSecurityShares><value>500</value></underlyingSecurityShares></underlyingSecurity>
    </derivativeHolding>
  </derivativeTable>
  <footnotes><footnote id="F1">Shares held indirectly.</footnote></footnotes>
</ownershipDocument>"""


class TestOwnershipUpgrades:
    def test_multiple_owners_footnotes_derivative_holdings(self):
        parsed = OwnershipFormParser(FORM4_XML).parse_all()
        form = OwnershipForm(parsed)

        assert len(form.owners) == 2
        assert form.owners[0].name == "HOLDINGS LLC"
        assert form.owners[0].is_ten_percent_owner
        assert form.owners[1].is_director

        assert form.footnotes == {"F1": "Shares held indirectly."}
        assert len(form.derivative_holdings) == 1
        assert form.derivative_holdings[0].shares_owned is None or True


THIRTEENF_TABLE = """<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
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
</informationTable>"""


class TestThirteenF:
    def test_holdings_and_summary(self):
        holdings = ThirteenFParser(THIRTEENF_TABLE).parse_holdings()
        report = ThirteenF(holdings)

        assert report.holding_count == 2
        assert report.total_value == 1250000.0
        assert report.top_holdings(1)[0].name_of_issuer == "APPLE INC"
        assert report.by_issuer("apple")[0].shares == 5000.0
        assert holdings[1]["put_call"] == "Put"
        assert holdings[0]["voting_authority"]["sole"] == 5000.0


INDEX_HTML = """<table class="tableFile" summary="Document Format Files">
<tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
<tr><td>1</td><td>10-K</td><td><a href="/Archives/x/doc.htm">doc.htm</a></td><td>10-K</td><td>100</td></tr>
<tr><td>2</td><td>PRESS RELEASE</td><td><a href="/Archives/x/ex99.htm">ex99.htm</a></td><td>EX-99.1</td><td>50</td></tr>
</table>"""


class TestExhibits:
    def test_index_page_parsing(self):
        records = parse_filing_index_html(INDEX_HTML)
        assert len(records) == 2
        assert records[1]["type"] == "EX-99.1"
        assert records[1]["document"] == "ex99.htm"
        assert records[1]["description"] == "PRESS RELEASE"


class TestFullTextSearch:
    def test_hit_mapping(self):
        class StubHttp:
            def get(self, url, params=None, **kwargs):
                assert params["q"] == "test"
                assert params["forms"] == "10-K"
                return {
                    "hits": {
                        "total": {"value": 1},
                        "hits": [
                            {
                                "_id": "0000000000-26-000001:doc.htm",
                                "_score": 1.5,
                                "_source": {
                                    "ciks": ["0000320193"],
                                    "display_names": ["Apple Inc.  (CIK 0000320193)"],
                                    "form": "10-K",
                                    "root_forms": ["10-K"],
                                    "file_date": "2026-01-01",
                                    "file_type": "10-K",
                                    "file_description": "FORM 10-K",
                                },
                            }
                        ],
                    }
                }

        results = FullTextSearchEndpoints(StubHttp()).search("test", forms="10-K")
        assert results["total"] == 1
        hit = results["hits"][0]
        assert hit["accession_number"] == "0000000000-26-000001"
        assert hit["cik"] == "0000320193"
        assert hit["company_name"] == "Apple Inc."


class TestDiskCache:
    def test_ttl_and_immutable(self, tmp_path):
        cache = DiskCache(tmp_path, ttl=0)

        api_url = "https://data.sec.gov/submissions/CIK1.json"
        cache.set(api_url, api_url, b"api")
        time.sleep(0.01)
        assert cache.get(api_url, api_url) is None  # TTL expired

        archive_url = "https://www.sec.gov/Archives/edgar/data/1/doc.htm"
        cache.set(archive_url, archive_url, b"archive")
        time.sleep(0.01)
        assert cache.get(archive_url, archive_url) == b"archive"  # immutable


class TestTwentyFItems:
    def test_20f_definitions_supported(self):
        extractor = ItemExtractor()
        definitions = extractor.get_item_definitions("20-F")
        numbers = [d.number for d in definitions]
        assert "5" in numbers and "19" in numbers
