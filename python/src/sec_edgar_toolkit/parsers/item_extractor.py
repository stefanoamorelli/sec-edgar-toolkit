"""
SEC Filing Item Extractor

Extracts individual items from SEC filings (10-K, 10-Q, 8-K, etc.)
based on standard item numbering and structure.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Union


class FormType(Enum):
    """Supported SEC form types for item extraction."""

    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_20F = "20-F"
    FORM_40F = "40-F"


@dataclass
class ItemDefinition:
    """Definition of an SEC filing item."""

    number: str
    title: str
    aliases: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class ExtractedItem:
    """Represents an extracted item from a filing."""

    item_number: str
    title: str
    content: str
    start_position: int
    end_position: int


class ItemExtractor:
    """Extracts individual items from SEC filings."""

    # 10-K Item definitions
    FORM_10K_ITEMS = [
        ItemDefinition("1", "Business"),
        ItemDefinition("1A", "Risk Factors"),
        ItemDefinition("1B", "Unresolved Staff Comments"),
        ItemDefinition("1C", "Cybersecurity", required=False),  # Added in 2023
        ItemDefinition("2", "Properties"),
        ItemDefinition("3", "Legal Proceedings"),
        ItemDefinition("4", "Mine Safety Disclosures", required=False),
        ItemDefinition("5", "Market for Registrant's Common Equity"),
        ItemDefinition("6", "Reserved", required=False),
        ItemDefinition("7", "Management's Discussion and Analysis", aliases=["MD&A"]),
        ItemDefinition(
            "7A", "Quantitative and Qualitative Disclosures About Market Risk"
        ),
        ItemDefinition("8", "Financial Statements and Supplementary Data"),
        ItemDefinition("9", "Changes in and Disagreements with Accountants"),
        ItemDefinition("9A", "Controls and Procedures"),
        ItemDefinition("9B", "Other Information"),
        ItemDefinition(
            "9C", "Disclosure Regarding Foreign Jurisdictions", required=False
        ),
        ItemDefinition("10", "Directors, Executive Officers and Corporate Governance"),
        ItemDefinition("11", "Executive Compensation"),
        ItemDefinition("12", "Security Ownership"),
        ItemDefinition("13", "Certain Relationships and Related Transactions"),
        ItemDefinition("14", "Principal Accountant Fees and Services"),
        ItemDefinition("15", "Exhibits and Financial Statement Schedules"),
    ]

    # 10-Q Item definitions
    FORM_10Q_ITEMS = [
        ItemDefinition("1", "Financial Statements"),
        ItemDefinition("2", "Management's Discussion and Analysis", aliases=["MD&A"]),
        ItemDefinition(
            "3", "Quantitative and Qualitative Disclosures About Market Risk"
        ),
        ItemDefinition("4", "Controls and Procedures"),
        ItemDefinition("1", "Legal Proceedings", aliases=["Part II, Item 1"]),
        ItemDefinition("1A", "Risk Factors", aliases=["Part II, Item 1A"]),
        ItemDefinition(
            "2", "Unregistered Sales of Equity Securities", aliases=["Part II, Item 2"]
        ),
        ItemDefinition(
            "3", "Defaults Upon Senior Securities", aliases=["Part II, Item 3"]
        ),
        ItemDefinition(
            "4", "Mine Safety Disclosures", aliases=["Part II, Item 4"], required=False
        ),
        ItemDefinition("5", "Other Information", aliases=["Part II, Item 5"]),
        ItemDefinition("6", "Exhibits", aliases=["Part II, Item 6"]),
    ]

    # 8-K Item definitions (most common items)
    FORM_8K_ITEMS = [
        ItemDefinition("1.01", "Entry into a Material Definitive Agreement"),
        ItemDefinition("1.02", "Termination of a Material Definitive Agreement"),
        ItemDefinition("2.01", "Completion of Acquisition or Disposition of Assets"),
        ItemDefinition("2.02", "Results of Operations and Financial Condition"),
        ItemDefinition("2.03", "Creation of a Direct Financial Obligation"),
        ItemDefinition("3.01", "Notice of Delisting or Failure to Satisfy"),
        ItemDefinition("3.02", "Unregistered Sales of Equity Securities"),
        ItemDefinition("4.01", "Changes in Registrant's Certifying Accountant"),
        ItemDefinition(
            "4.02", "Non-Reliance on Previously Issued Financial Statements"
        ),
        ItemDefinition("5.01", "Changes in Control of Registrant"),
        ItemDefinition("5.02", "Departure of Directors or Certain Officers"),
        ItemDefinition("5.03", "Amendments to Articles of Incorporation or Bylaws"),
        ItemDefinition("7.01", "Regulation FD Disclosure"),
        ItemDefinition("8.01", "Other Events"),
        ItemDefinition("9.01", "Financial Statements and Exhibits"),
    ]

    def __init__(self):
        """Initialize the item extractor."""
        self.form_items = {
            FormType.FORM_10K: self.FORM_10K_ITEMS,
            FormType.FORM_10Q: self.FORM_10Q_ITEMS,
            FormType.FORM_8K: self.FORM_8K_ITEMS,
        }

    def extract_items(
        self, content: str, form_type: Union[str, FormType]
    ) -> Dict[str, str]:
        """
        Extract all items from a filing.

        Args:
            content: The filing content (HTML or text)
            form_type: The type of form (e.g., "10-K", "10-Q", "8-K")

        Returns:
            Dictionary mapping item numbers to their content

        Example:
            {
                "1": "Item 1. Business\n...",
                "1A": "Item 1A. Risk Factors\n...",
                "2": "Item 2. Properties\n..."
            }
        """
        # Convert string form type to enum
        if isinstance(form_type, str):
            form_type = self._parse_form_type(form_type)

        if form_type not in self.form_items:
            raise ValueError(f"Unsupported form type: {form_type}")

        # Clean content
        clean_content = self._clean_content(content)

        # Extract table of contents if available
        toc_items = self._extract_table_of_contents(clean_content)

        # Extract items
        items = self._extract_items_from_content(clean_content, form_type, toc_items)

        # Post-process and validate
        return self._post_process_items(items, form_type)

    def extract_specific_items(
        self, content: str, form_type: Union[str, FormType], item_numbers: List[str]
    ) -> Dict[str, str]:
        """
        Extract specific items from a filing.

        Args:
            content: The filing content
            form_type: The type of form
            item_numbers: List of item numbers to extract (e.g., ["1", "1A", "7"])

        Returns:
            Dictionary with only the requested items
        """
        all_items = self.extract_items(content, form_type)
        return {k: v for k, v in all_items.items() if k in item_numbers}

    def _parse_form_type(self, form_type_str: str) -> FormType:
        """Parse string form type to FormType enum."""
        form_type_upper = form_type_str.upper()

        # Handle variations
        if "10-K" in form_type_upper or "10K" in form_type_upper:
            return FormType.FORM_10K
        elif "10-Q" in form_type_upper or "10Q" in form_type_upper:
            return FormType.FORM_10Q
        elif "8-K" in form_type_upper or "8K" in form_type_upper:
            return FormType.FORM_8K
        elif "20-F" in form_type_upper or "20F" in form_type_upper:
            return FormType.FORM_20F
        elif "40-F" in form_type_upper or "40F" in form_type_upper:
            return FormType.FORM_40F
        else:
            raise ValueError(f"Unknown form type: {form_type_str}")

    def _clean_content(self, content: str) -> str:
        """Clean HTML content for better text extraction."""
        # Remove HTML tags but preserve structure
        content = re.sub(r"<[^>]+>", " ", content)

        # Normalize whitespace
        content = re.sub(r"\s+", " ", content)

        # Preserve line breaks for item boundaries
        content = re.sub(
            r"(Item\s+\d+[A-Z]?\.)", r"\n\n\1", content, flags=re.IGNORECASE
        )

        return content.strip()

    def _extract_table_of_contents(self, content: str) -> List[Tuple[str, int]]:
        """
        Extract table of contents to help locate items.

        Returns:
            List of (item_number, position) tuples
        """
        toc_items = []

        # Look for table of contents section
        toc_match = re.search(
            r"TABLE\s+OF\s+CONTENTS(.*?)(?:Item\s+1\.|PART\s+I\s)",
            content,
            re.IGNORECASE | re.DOTALL,
        )

        if toc_match:
            toc_content = toc_match.group(1)

            # Extract item references from TOC
            item_pattern = r"Item\s+(\d+[A-Z]?)\.\s*([^\n\r\.]+)"
            for match in re.finditer(item_pattern, toc_content, re.IGNORECASE):
                item_num = match.group(1).upper()
                toc_items.append((item_num, match.start()))

        return toc_items

    def _extract_items_from_content(
        self, content: str, form_type: FormType, toc_items: List[Tuple[str, int]]
    ) -> Dict[str, ExtractedItem]:
        """Extract items from the main content."""
        items = {}
        item_definitions = self.form_items[form_type]

        # Create patterns for each item
        for item_def in item_definitions:
            # Build pattern with item number and possible variations
            patterns = [
                rf"Item\s+{re.escape(item_def.number)}\.\s*{re.escape(item_def.title)}",
                rf"Item\s+{re.escape(item_def.number)}\.\s*(?=[A-Z])",
                rf"Item\s+{re.escape(item_def.number)}(?:\.|:|\s)",
            ]

            # Add alias patterns
            for alias in item_def.aliases:
                patterns.append(rf"{re.escape(alias)}")

            # Try each pattern
            for pattern in patterns:
                matches = list(
                    re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                )

                if matches:
                    # Use the first match after TOC (if TOC exists)
                    match = matches[0]
                    if len(matches) > 1 and toc_items:
                        # Skip matches that appear in TOC
                        for m in matches[1:]:
                            if not self._is_in_toc(m.start(), toc_items):
                                match = m
                                break

                    start_pos = match.start()

                    # Find the end position (start of next item)
                    end_pos = self._find_item_end(content, start_pos, item_definitions)

                    # Extract content
                    item_content = content[start_pos:end_pos].strip()

                    items[item_def.number] = ExtractedItem(
                        item_number=item_def.number,
                        title=item_def.title,
                        content=item_content,
                        start_position=start_pos,
                        end_position=end_pos,
                    )
                    break

        return items

    def _is_in_toc(self, position: int, toc_items: List[Tuple[str, int]]) -> bool:
        """Check if a position is within the table of contents."""
        if not toc_items:
            return False

        # Rough heuristic: if position is before the last TOC item + buffer
        if toc_items:
            last_toc_pos = max(item[1] for item in toc_items)
            return position < last_toc_pos + 500

        return False

    def _find_item_end(
        self, content: str, start_pos: int, item_definitions: List[ItemDefinition]
    ) -> int:  # noqa: ARG002
        """Find where an item ends (usually the start of the next item)."""
        # Look for the next item
        next_item_pattern = r"Item\s+\d+[A-Z]?[\.:]\s*[A-Z]"

        match = re.search(next_item_pattern, content[start_pos + 10 :], re.IGNORECASE)

        if match:
            return start_pos + 10 + match.start()
        else:
            # No next item found, return end of content
            return len(content)

    def _post_process_items(
        self, items: Dict[str, ExtractedItem], form_type: FormType
    ) -> Dict[str, str]:  # noqa: ARG002
        """Post-process extracted items."""
        processed = {}

        for item_num, extracted_item in items.items():
            # Clean up the content
            content = extracted_item.content

            # Remove excessive whitespace
            content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

            # Ensure we have some content
            if len(content.strip()) > 50:  # Minimum content threshold
                processed[item_num] = content
            else:
                # Try to handle empty or placeholder items
                if "none" in content.lower() or "not applicable" in content.lower():
                    processed[item_num] = content
                else:
                    processed[item_num] = ""

        return processed

    def get_item_definitions(
        self, form_type: Union[str, FormType]
    ) -> List[ItemDefinition]:
        """Get the item definitions for a specific form type."""
        if isinstance(form_type, str):
            form_type = self._parse_form_type(form_type)

        return self.form_items.get(form_type, [])
