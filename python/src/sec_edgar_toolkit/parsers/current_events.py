"""Parser for 8-K current events documents."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types.current_events import (
    Acquisition,
    Agreement,
    EarningsData,
    Event,
    ExecutiveChange,
    ParsedCurrentEvent,
)

logger = logging.getLogger(__name__)


class CurrentEventParser:
    """Parser for SEC 8-K current event forms."""

    def __init__(self, raw_content: str) -> None:
        """
        Initialize the current event parser.

        Args:
            raw_content: Raw content of the 8-K filing
        """
        self.raw_content = raw_content

    def parse_all(self) -> ParsedCurrentEvent:
        """
        Parse all current events from the 8-K filing.

        Returns:
            ParsedCurrentEvent containing all extracted information
        """
        header = self._parse_header()

        return ParsedCurrentEvent(
            form_type=header["form_type"],
            filing_date=header["filing_date"],
            cik=header["cik"],
            company_name=header["company_name"],
            ticker=header["ticker"],
            events=self.get_current_events(),
            material_agreements=self.get_material_agreements(),
            executive_changes=self.get_executive_changes(),
            acquisitions=self.get_acquisitions(),
            earnings_results=self.get_earnings_results(),
        )

    def get_current_events(self) -> List[Event]:
        """
        Extract current events from the filing.

        Returns:
            List of Event objects
        """
        events: List[Event] = []

        # Extract Item numbers and descriptions
        item_pattern = re.compile(r"ITEM\s+(\d+\.\d+)\s+([^\n\r]+)", re.IGNORECASE)

        for match in item_pattern.finditer(self.raw_content):
            item_number = match.group(1)
            description = match.group(2).strip()

            events.append(
                Event(
                    type=self._map_item_to_event_type(item_number),
                    description=description,
                    date=self._extract_filing_date(),
                    item=f"Item {item_number}",
                    significance=self._assess_event_significance(description),
                    details={
                        "item_number": item_number,
                        "full_text": self._extract_item_content(item_number),
                    },
                )
            )

        return events

    def get_material_agreements(self) -> List[Agreement]:
        """
        Extract material agreements from the filing.

        Returns:
            List of Agreement objects
        """
        agreements: List[Agreement] = []

        # Look for agreement-related content
        agreement_section = self._extract_section(
            r"ITEM 1\.01|MATERIAL AGREEMENT|DEFINITIVE AGREEMENT"
        )

        if agreement_section:
            agreement_pattern = re.compile(
                r"agreement.*?with\s+([^,.]+)", re.IGNORECASE
            )

            for match in agreement_pattern.finditer(agreement_section):
                agreements.append(
                    Agreement(
                        type="Material Agreement",
                        parties=[match.group(1).strip()],
                        effective_date=self._extract_filing_date(),
                        description=agreement_section[:500],
                        value=self._extract_agreement_value(agreement_section),
                        currency="USD",
                    )
                )

        return agreements

    def get_executive_changes(self) -> List[ExecutiveChange]:
        """
        Extract executive changes from the filing.

        Returns:
            List of ExecutiveChange objects
        """
        changes: List[ExecutiveChange] = []

        # Look for executive change content
        change_section = self._extract_section(
            r"ITEM 5\.02|DEPARTURE.*DIRECTOR|APPOINTMENT.*OFFICER"
        )

        if change_section:
            name_pattern = re.compile(
                r"([A-Z][a-z]+\s+[A-Z][a-z]+).*?(appointed|resigned|terminated)",
                re.IGNORECASE,
            )

            for match in name_pattern.finditer(change_section):
                name = match.group(1).strip()
                action = match.group(2).lower()

                change_type: str
                if "appointed" in action:
                    change_type = "appointment"
                elif "resigned" in action:
                    change_type = "resignation"
                else:
                    change_type = "termination"

                changes.append(
                    ExecutiveChange(
                        type=change_type,
                        person={
                            "name": name,
                            "position": self._extract_position(change_section, name),
                        },
                        effective_date=self._extract_filing_date(),
                    )
                )

        return changes

    def get_acquisitions(self) -> List[Acquisition]:
        """
        Extract acquisitions and mergers from the filing.

        Returns:
            List of Acquisition objects
        """
        acquisitions: List[Acquisition] = []

        # Look for acquisition content
        acquisition_section = self._extract_section(
            r"ITEM 2\.01|ACQUISITION|MERGER|DIVESTITURE"
        )

        if acquisition_section:
            acquisitions.append(
                Acquisition(
                    type="acquisition",
                    target={
                        "name": self._extract_target_name(acquisition_section),
                        "description": acquisition_section[:300],
                    },
                    value=self._extract_transaction_value(acquisition_section),
                    currency="USD",
                    expected_closing_date=None,
                    status="announced",
                )
            )

        return acquisitions

    def get_earnings_results(self) -> Optional[EarningsData]:
        """
        Extract earnings results from the filing.

        Returns:
            EarningsData object or None if no earnings data found
        """
        # Look for earnings-related content
        earnings_section = self._extract_section(
            r"ITEM 2\.02|RESULTS.*OPERATIONS|EARNINGS"
        )

        if not earnings_section:
            return None

        return EarningsData(
            period=self._extract_reporting_period(),
            revenue=self._extract_metric(earnings_section, r"revenue|sales"),
            net_income=self._extract_metric(earnings_section, r"net income|earnings"),
            earnings_per_share=self._extract_metric(
                earnings_section, r"earnings per share|EPS"
            ),
            guidance=self._extract_guidance(earnings_section),
        )

    # Helper methods

    def _parse_header(self) -> Dict[str, Any]:
        """Parse header information from the filing."""
        cik_match = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", self.raw_content)
        company_match = re.search(
            r"COMPANY CONFORMED NAME:\s*([^\n\r]+)", self.raw_content
        )
        form_type_match = re.search(r"FORM TYPE:\s*([^\n\r]+)", self.raw_content)
        filing_date_match = re.search(r"FILED AS OF DATE:\s*(\d{8})", self.raw_content)

        return {
            "cik": cik_match.group(1) if cik_match else "",
            "company_name": company_match.group(1).strip() if company_match else "",
            "form_type": form_type_match.group(1).strip() if form_type_match else "",
            "ticker": "",  # Would need to extract from trading symbol
            "filing_date": self._parse_date(
                filing_date_match.group(1) if filing_date_match else None
            ),
        }

    def _extract_section(self, pattern: str) -> str:
        """Extract a section based on pattern."""
        match = re.search(pattern, self.raw_content, re.IGNORECASE)
        if not match:
            return ""

        start_index = match.start()
        # Find next ITEM or end of document
        next_item = re.search(r"ITEM", self.raw_content[start_index + 1 :])
        end_index = (
            start_index + 1 + next_item.start() if next_item else start_index + 10000
        )

        return self.raw_content[start_index:end_index]

    def _map_item_to_event_type(self, item_number: str) -> str:
        """Map item number to event type."""
        item_map = {
            "1.01": "Material Agreement",
            "1.02": "Termination of Material Agreement",
            "2.01": "Acquisition or Disposition",
            "2.02": "Results of Operations",
            "3.01": "Notice of Delisting",
            "5.02": "Executive Changes",
            "8.01": "Other Events",
        }

        return item_map.get(item_number, "Other Event")

    def _assess_event_significance(self, description: str) -> str:
        """Assess the significance of an event."""
        high_keywords = ["acquisition", "merger", "bankruptcy", "material adverse"]
        medium_keywords = ["agreement", "executive", "earnings", "results"]

        text = description.lower()

        if any(keyword in text for keyword in high_keywords):
            return "high"
        elif any(keyword in text for keyword in medium_keywords):
            return "medium"

        return "low"

    def _extract_item_content(self, item_number: str) -> str:
        """Extract content for a specific item."""
        item_pattern = re.compile(
            rf"ITEM\s+{re.escape(item_number)}[^]*?(?=ITEM|$)", re.IGNORECASE
        )
        match = item_pattern.search(self.raw_content)
        return match.group(0) if match else ""

    def _extract_filing_date(self) -> datetime:
        """Extract filing date from the document."""
        date_match = re.search(r"FILED AS OF DATE:\s*(\d{8})", self.raw_content)
        return self._parse_date(date_match.group(1) if date_match else None)

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse date from YYYYMMDD format."""
        if not date_str:
            return datetime.now()

        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])

        return datetime(year, month, day)

    def _extract_agreement_value(self, text: str) -> Optional[float]:
        """Extract monetary value from text."""
        value_pattern = re.compile(
            r"\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?", re.IGNORECASE
        )
        match = value_pattern.search(text)

        if match:
            value = float(match.group(1).replace(",", ""))
            if "million" in text.lower():
                value *= 1_000_000
            elif "billion" in text.lower():
                value *= 1_000_000_000
            return value

        return None

    def _extract_position(self, text: str, name: str) -> str:
        """Extract position/title for a person."""
        position_pattern = re.compile(
            rf"{name}.*?(CEO|CFO|President|Director|Officer|Vice President)",
            re.IGNORECASE,
        )
        match = position_pattern.search(text)
        return match.group(1) if match else "Executive"

    def _extract_target_name(self, text: str) -> str:
        """Extract target company name from acquisition text."""
        target_pattern = re.compile(
            r"(?:acquire|purchase|merger with)\s+([A-Z][^,.]{10,50})", re.IGNORECASE
        )
        match = target_pattern.search(text)
        return match.group(1).strip() if match else "Target Company"

    def _extract_transaction_value(self, text: str) -> Optional[float]:
        """Extract transaction value."""
        return self._extract_agreement_value(text)

    def _extract_reporting_period(self) -> str:
        """Extract reporting period."""
        period_match = re.search(
            r"CONFORMED PERIOD OF REPORT:\s*(\d{8})", self.raw_content
        )
        if period_match:
            date = self._parse_date(period_match.group(1))
            quarter = (date.month - 1) // 3 + 1
            return f"Q{quarter} {date.year}"
        return "Current Period"

    def _extract_metric(self, text: str, pattern: str) -> Optional[float]:
        """Extract a financial metric from text."""
        metric_pattern = re.compile(
            rf"{pattern}.*?\$([0-9,]+(?:\.[0-9]+)?)", re.IGNORECASE
        )
        match = metric_pattern.search(text)
        return float(match.group(1).replace(",", "")) if match else None

    def _extract_guidance(self, text: str) -> List[Dict[str, str]]:
        """Extract guidance information."""
        guidance: List[Dict[str, str]] = []

        guidance_pattern = re.compile(
            r"(?:guidance|expects?).*?([a-zA-Z\s]+).*?(\$[0-9,]+|\d+%)",
            re.IGNORECASE,
        )

        for match in guidance_pattern.finditer(text):
            guidance.append(
                {
                    "metric": match.group(1).strip(),
                    "value": match.group(2),
                }
            )

        return guidance
