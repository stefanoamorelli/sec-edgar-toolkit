"""Tests for recent filings functionality (get_recent_filings / get_current_filings)."""

from __future__ import annotations

import pytest
import responses

from sec_edgar_toolkit import SecEdgarApi
from sec_edgar_toolkit.endpoints.filings import FilingsEndpoints

# Sample Atom feed response from SEC EDGAR
SAMPLE_ATOM_FEED = b"""<?xml version="1.0" encoding="ISO-8859-1" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Latest Filings - Sun, 29 Mar 2026 12:53:07 EDT</title>
<link rel="alternate" href="/cgi-bin/browse-edgar?action=getcurrent"/>
<link rel="self" href="/cgi-bin/browse-edgar?action=getcurrent"/>
<id>https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent</id>
<author><name>Webmaster</name><email>webmaster@sec.gov</email></author>
<updated>2026-03-29T12:53:07-04:00</updated>
<entry>
<title>10-K - AIM ImmunoTech Inc. (0000946644) (Filer)</title>
<link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/946644/000149315226013301/0001493152-26-013301-index.htm"/>
<summary type="html">
 &lt;b&gt;Filed:&lt;/b&gt; 2026-03-27 &lt;b&gt;AccNo:&lt;/b&gt; 0001493152-26-013301 &lt;b&gt;Size:&lt;/b&gt; 11 MB
</summary>
<updated>2026-03-27T17:30:45-04:00</updated>
<category scheme="https://www.sec.gov/" label="form type" term="10-K"/>
<id>urn:tag:sec.gov,2008:accession-number=0001493152-26-013301</id>
</entry>
<entry>
<title>10-K - Space Asset Acquisition Corp. (0002091222) (Filer)</title>
<link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/2091222/000121390026035748/0001213900-26-035748-index.htm"/>
<summary type="html">
 &lt;b&gt;Filed:&lt;/b&gt; 2026-03-27 &lt;b&gt;AccNo:&lt;/b&gt; 0001213900-26-035748 &lt;b&gt;Size:&lt;/b&gt; 3 MB
</summary>
<updated>2026-03-27T17:29:29-04:00</updated>
<category scheme="https://www.sec.gov/" label="form type" term="10-K"/>
<id>urn:tag:sec.gov,2008:accession-number=0001213900-26-035748</id>
</entry>
<entry>
<title>8-K - TESLA INC (0001318605) (Filer)</title>
<link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/1318605/000131860526000015/0001318605-26-000015-index.htm"/>
<summary type="html">
 &lt;b&gt;Filed:&lt;/b&gt; 2026-03-26 &lt;b&gt;AccNo:&lt;/b&gt; 0001318605-26-000015 &lt;b&gt;Size:&lt;/b&gt; 1 MB
</summary>
<updated>2026-03-26T08:10:00-04:00</updated>
<category scheme="https://www.sec.gov/" label="form type" term="8-K"/>
<id>urn:tag:sec.gov,2008:accession-number=0001318605-26-000015</id>
</entry>
</feed>"""


class TestAtomFeedParser:
    """Test the Atom feed parsing logic."""

    def test_parse_atom_feed_basic(self):
        """Test parsing a valid Atom feed."""
        filings = FilingsEndpoints._parse_atom_feed(SAMPLE_ATOM_FEED)

        assert len(filings) == 3

    def test_parse_atom_feed_first_entry(self):
        """Test fields of the first parsed entry."""
        filings = FilingsEndpoints._parse_atom_feed(SAMPLE_ATOM_FEED)
        first = filings[0]

        assert first["cik"] == "0000946644"
        assert first["accession_number"] == "0001493152-26-013301"
        assert first["form_type"] == "10-K"
        assert first["filing_date"] == "2026-03-27"
        assert first["company_name"] == "AIM ImmunoTech Inc."
        assert "946644" in first["url"]

    def test_parse_atom_feed_second_entry(self):
        """Test fields of the second parsed entry."""
        filings = FilingsEndpoints._parse_atom_feed(SAMPLE_ATOM_FEED)
        second = filings[1]

        assert second["cik"] == "0002091222"
        assert second["accession_number"] == "0001213900-26-035748"
        assert second["form_type"] == "10-K"
        assert second["company_name"] == "Space Asset Acquisition Corp."

    def test_parse_atom_feed_8k_entry(self):
        """Test parsing an 8-K entry."""
        filings = FilingsEndpoints._parse_atom_feed(SAMPLE_ATOM_FEED)
        third = filings[2]

        assert third["form_type"] == "8-K"
        assert third["company_name"] == "TESLA INC"
        assert third["cik"] == "0001318605"
        assert third["filing_date"] == "2026-03-26"

    def test_parse_atom_feed_empty(self):
        """Test parsing an empty feed."""
        empty_feed = b"""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Latest Filings</title>
        </feed>"""
        filings = FilingsEndpoints._parse_atom_feed(empty_feed)
        assert filings == []

    def test_parse_atom_feed_invalid_xml(self):
        """Test handling invalid XML."""
        filings = FilingsEndpoints._parse_atom_feed(b"not xml at all")
        assert filings == []

    def test_parse_atom_feed_all_fields_present(self):
        """Test that all expected fields are present in parsed entries."""
        filings = FilingsEndpoints._parse_atom_feed(SAMPLE_ATOM_FEED)
        expected_keys = {
            "cik",
            "accession_number",
            "form_type",
            "filing_date",
            "company_name",
            "url",
        }

        for filing in filings:
            assert set(filing.keys()) == expected_keys


class TestGetRecentFilings:
    """Test the get_recent_filings endpoint method."""

    @pytest.fixture
    def api_client(self) -> SecEdgarApi:
        """Create a test API client."""
        return SecEdgarApi(
            user_agent="TestClient/1.0 (test@example.com)",
            rate_limit_delay=0.01,
        )

    @responses.activate
    def test_get_recent_filings_single_form(self, api_client):
        """Test fetching recent filings with a single form type."""
        responses.add(
            responses.GET,
            "https://www.sec.gov/cgi-bin/browse-edgar",
            body=SAMPLE_ATOM_FEED,
            status=200,
            content_type="application/atom+xml",
        )

        filings = api_client.get_recent_filings(form_type="10-K", limit=10)

        assert len(filings) == 3
        assert filings[0]["form_type"] == "10-K"
        assert filings[0]["cik"] == "0000946644"

    @responses.activate
    def test_get_recent_filings_no_form_filter(self, api_client):
        """Test fetching recent filings without form type filter."""
        responses.add(
            responses.GET,
            "https://www.sec.gov/cgi-bin/browse-edgar",
            body=SAMPLE_ATOM_FEED,
            status=200,
            content_type="application/atom+xml",
        )

        filings = api_client.get_recent_filings(limit=10)

        assert len(filings) == 3

    @responses.activate
    def test_get_recent_filings_list_form_types(self, api_client):
        """Test fetching recent filings with multiple form types."""
        # Each form type makes a separate request
        responses.add(
            responses.GET,
            "https://www.sec.gov/cgi-bin/browse-edgar",
            body=SAMPLE_ATOM_FEED,
            status=200,
            content_type="application/atom+xml",
        )
        responses.add(
            responses.GET,
            "https://www.sec.gov/cgi-bin/browse-edgar",
            body=SAMPLE_ATOM_FEED,
            status=200,
            content_type="application/atom+xml",
        )

        filings = api_client.get_recent_filings(form_type=["10-K", "8-K"], limit=5)

        assert len(filings) <= 5
        # Results should be sorted by date descending
        dates = [f["filing_date"] for f in filings if f["filing_date"]]
        assert dates == sorted(dates, reverse=True)

    @responses.activate
    def test_get_recent_filings_server_error(self, api_client):
        """Test graceful handling of server errors."""
        responses.add(
            responses.GET,
            "https://www.sec.gov/cgi-bin/browse-edgar",
            body=b"Server Error",
            status=500,
        )

        filings = api_client.get_recent_filings(form_type="10-K", limit=10)

        # Should return empty list on error, not raise
        assert filings == []


class TestGetRecentFilingsGlobalFunction:
    """Test the global get_filings() function without company filter."""

    @responses.activate
    def test_get_filings_global(self):
        """Test that get_filings() without company returns recent filings."""
        from sec_edgar_toolkit.core.global_functions import get_filings, set_identity

        set_identity("TestClient/1.0 (test@example.com)")

        responses.add(
            responses.GET,
            "https://www.sec.gov/cgi-bin/browse-edgar",
            body=SAMPLE_ATOM_FEED,
            status=200,
            content_type="application/atom+xml",
        )

        filings = get_filings(form="10-K", limit=5)

        assert len(filings) > 0
        # Should return Filing objects, not dicts
        first = filings[0]
        assert hasattr(first, "cik")
        assert hasattr(first, "accession_number")
        assert hasattr(first, "form_type")
        assert hasattr(first, "filing_date")
