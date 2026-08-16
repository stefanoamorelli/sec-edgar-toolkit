"""
SEC Filing Item Extractor

Extraction engine that pulls individual items out of SEC filings
(10-K, 10-Q, 8-K) using the definitions in :mod:`.items`.
"""

import re
from typing import Dict, List, Optional, Tuple, Union

from .items import (
    FORM_8K_ITEMS,
    FORM_10K_ITEMS,
    FORM_10Q_ITEMS,
    FORM_ITEM_DEFINITIONS,
    EightKItem,
    ExtractedItem,
    FormType,
    ItemDefinition,
    TenKItem,
    TenQItem,
)

__all__ = [
    "ItemExtractor",
    "FormType",
    "ItemDefinition",
    "ExtractedItem",
    "TenKItem",
    "TenQItem",
    "EightKItem",
    "FORM_10K_ITEMS",
    "FORM_10Q_ITEMS",
    "FORM_8K_ITEMS",
    "FORM_ITEM_DEFINITIONS",
]


class ItemExtractor:
    """Extracts individual items from SEC filings."""

    FORM_10K_ITEMS = FORM_10K_ITEMS
    FORM_10Q_ITEMS = FORM_10Q_ITEMS
    FORM_8K_ITEMS = FORM_8K_ITEMS

    def __init__(self):
        """Initialize the item extractor."""
        self.form_items = dict(FORM_ITEM_DEFINITIONS)

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
                    # The same heading occurs in the table of contents, the
                    # cover page, and the body; the body occurrence is the
                    # one followed by real content, so pick the match with
                    # the longest span to the next item heading.
                    best: Tuple[int, int] = (-1, -1)  # (length, start)
                    for m in matches:
                        if toc_items and self._is_in_toc(m.start(), toc_items):
                            continue
                        end = self._find_item_end(content, m.start(), item_definitions)
                        length = end - m.start()
                        if length > best[0]:
                            best = (length, m.start())
                    if best[1] < 0:
                        end = self._find_item_end(
                            content, matches[0].start(), item_definitions
                        )
                        best = (end - matches[0].start(), matches[0].start())

                    start_pos = best[1]
                    end_pos = start_pos + best[0]

                    # Extract content
                    item_content = content[start_pos:end_pos].strip()

                    items[item_def.result_key()] = ExtractedItem(
                        item_number=item_def.result_key(),
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
