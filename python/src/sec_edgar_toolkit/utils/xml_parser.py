"""
Enhanced XML parser utilities using lxml with fallback to standard library.

This module provides robust XML parsing capabilities with better error handling,
namespace support, and XPath functionality when lxml is available.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

try:
    from lxml import etree
    from lxml.etree import Element, XMLParser

    LXML_AVAILABLE = True
except ImportError:
    from xml.etree import ElementTree as etree
    from xml.etree.ElementTree import Element

    XMLParser = None
    LXML_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnhancedXMLParser:
    """
    Enhanced XML parser with lxml features and standard library fallback.

    This parser provides:
    - Better error recovery with lxml
    - XPath support when available
    - Namespace handling
    - HTML parsing capabilities
    - Consistent API regardless of backend
    """

    def __init__(
        self,
        recover: bool = True,
        remove_blank_text: bool = True,
        huge_tree: bool = False,
        encoding: Optional[str] = None,
    ):
        """
        Initialize the XML parser.

        Args:
            recover: Try to recover from parsing errors (lxml only)
            remove_blank_text: Remove blank text nodes (lxml only)
            huge_tree: Enable parsing of huge documents (lxml only)
            encoding: Force specific encoding
        """
        self.recover = recover
        self.remove_blank_text = remove_blank_text
        self.huge_tree = huge_tree
        self.encoding = encoding

        if LXML_AVAILABLE:
            self.parser = etree.XMLParser(
                recover=recover,
                remove_blank_text=remove_blank_text,
                huge_tree=huge_tree,
                encoding=encoding,
            )
        else:
            self.parser = None
            if recover or huge_tree:
                logger.warning(
                    "Advanced parser options not available without lxml. "
                    "Install lxml for better XML parsing capabilities."
                )

    def parse_string(self, xml_content: Union[str, bytes]) -> Element:
        """
        Parse XML from string or bytes.

        Args:
            xml_content: XML content as string or bytes

        Returns:
            Parsed XML root element

        Raises:
            Exception: If parsing fails
        """
        if isinstance(xml_content, bytes) and self.encoding is None:
            # Try to detect encoding
            if xml_content.startswith(b"<?xml"):
                try:
                    encoding_start = xml_content.find(b'encoding="') + 10
                    encoding_end = xml_content.find(b'"', encoding_start)
                    if encoding_start > 10 and encoding_end > encoding_start:
                        self.encoding = xml_content[encoding_start:encoding_end].decode(
                            "ascii"
                        )
                except Exception:
                    pass

        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode(self.encoding or "utf-8")

        if LXML_AVAILABLE:
            return etree.fromstring(xml_content, parser=self.parser)
        else:
            return etree.fromstring(xml_content)

    def parse_file(self, file_path: str) -> Element:
        """
        Parse XML from file.

        Args:
            file_path: Path to XML file

        Returns:
            Parsed XML root element
        """
        if LXML_AVAILABLE:
            return etree.parse(file_path, parser=self.parser).getroot()
        else:
            return etree.parse(file_path).getroot()

    def xpath(
        self,
        element: Element,
        expression: str,
        namespaces: Optional[Dict[str, str]] = None,
    ) -> List[Any]:
        """
        Execute XPath expression on element.

        Args:
            element: XML element to search
            expression: XPath expression
            namespaces: Namespace mappings

        Returns:
            List of matching elements or values
        """
        if LXML_AVAILABLE:
            return element.xpath(expression, namespaces=namespaces)
        else:
            # Limited XPath support with standard library
            if expression.startswith("//"):
                tag = expression[2:].split("[")[0]  # Simple tag extraction
                return element.findall(f".//{tag}", namespaces)
            elif expression.startswith(".//"):
                tag = expression[3:].split("[")[0]
                return element.findall(f"./{tag}", namespaces)
            else:
                logger.warning(
                    f"Complex XPath '{expression}' not supported without lxml. "
                    "Install lxml for full XPath support."
                )
                return []

    def find(
        self,
        element: Element,
        path: str,
        namespaces: Optional[Dict[str, str]] = None,
    ) -> Optional[Element]:
        """
        Find first element matching path.

        Args:
            element: XML element to search
            path: Element path
            namespaces: Namespace mappings

        Returns:
            First matching element or None
        """
        if LXML_AVAILABLE and path.startswith(("/", "(")):
            # Use XPath for complex expressions
            results = self.xpath(element, path, namespaces)
            return results[0] if results else None
        else:
            return element.find(path, namespaces)

    def findall(
        self,
        element: Element,
        path: str,
        namespaces: Optional[Dict[str, str]] = None,
    ) -> List[Element]:
        """
        Find all elements matching path.

        Args:
            element: XML element to search
            path: Element path
            namespaces: Namespace mappings

        Returns:
            List of matching elements
        """
        if LXML_AVAILABLE and path.startswith(("/", "(")):
            # Use XPath for complex expressions
            return self.xpath(element, path, namespaces)
        else:
            return element.findall(path, namespaces)

    @staticmethod
    def get_text(element: Optional[Element], default: str = "") -> str:
        """
        Safely extract text from an XML element.

        Args:
            element: XML element
            default: Default value if element is None or has no text

        Returns:
            Element text or default value
        """
        if element is not None:
            if LXML_AVAILABLE:
                # lxml has text_content() method that gets all text
                text = element.text or ""
            else:
                text = element.text or ""
            return text.strip()
        return default

    @staticmethod
    def get_attribute(
        element: Optional[Element],
        attribute: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Safely get attribute value from element.

        Args:
            element: XML element
            attribute: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        if element is not None:
            return element.get(attribute, default)
        return default

    def to_dict(self, element: Element) -> Dict[str, Any]:
        """
        Convert XML element to dictionary.

        Args:
            element: XML element to convert

        Returns:
            Dictionary representation of the element
        """
        result = {}

        # Add attributes
        if element.attrib:
            result["@attributes"] = dict(element.attrib)

        # Add text content
        if element.text and element.text.strip():
            result["text"] = element.text.strip()

        # Add children
        children = {}
        for child in element:
            child_data = self.to_dict(child)
            if child.tag in children:
                # Convert to list if multiple children with same tag
                if not isinstance(children[child.tag], list):
                    children[child.tag] = [children[child.tag]]
                children[child.tag].append(child_data)
            else:
                children[child.tag] = child_data

        if children:
            result.update(children)

        # Simplify if only text content
        if len(result) == 1 and "text" in result:
            return result["text"]

        return result


class HTMLParser(EnhancedXMLParser):
    """
    HTML parser using lxml's HTML parser with fallback to XML parser.
    """

    def __init__(self, **kwargs):
        """Initialize HTML parser."""
        super().__init__(**kwargs)

        if LXML_AVAILABLE:
            self.parser = etree.HTMLParser(
                recover=True,
                remove_blank_text=self.remove_blank_text,
                encoding=self.encoding,
            )

    def parse_string(self, html_content: Union[str, bytes]) -> Element:
        """
        Parse HTML from string or bytes.

        Args:
            html_content: HTML content

        Returns:
            Parsed HTML root element
        """
        if isinstance(html_content, bytes):
            html_content = html_content.decode(
                self.encoding or "utf-8", errors="replace"
            )

        if LXML_AVAILABLE:
            return etree.fromstring(html_content, parser=self.parser)
        else:
            # Fallback to XML parser with lenient parsing
            try:
                return super().parse_string(html_content)
            except Exception:
                # Try to clean up common HTML issues
                html_content = html_content.replace("&nbsp;", " ")
                html_content = html_content.replace("&", "&amp;")
                return super().parse_string(html_content)


# Convenience functions
def parse_xml(content: Union[str, bytes], recover: bool = True, **kwargs) -> Element:
    """
    Parse XML content with enhanced parser.

    Args:
        content: XML content as string or bytes
        recover: Try to recover from errors
        **kwargs: Additional parser options

    Returns:
        Parsed XML root element
    """
    parser = EnhancedXMLParser(recover=recover, **kwargs)
    return parser.parse_string(content)


def parse_html(content: Union[str, bytes], **kwargs) -> Element:
    """
    Parse HTML content with enhanced parser.

    Args:
        content: HTML content as string or bytes
        **kwargs: Additional parser options

    Returns:
        Parsed HTML root element
    """
    parser = HTMLParser(**kwargs)
    return parser.parse_string(content)


def xpath(
    element: Element,
    expression: str,
    namespaces: Optional[Dict[str, str]] = None,
) -> List[Any]:
    """
    Execute XPath expression on element.

    Args:
        element: XML element
        expression: XPath expression
        namespaces: Namespace mappings

    Returns:
        List of matching elements or values
    """
    parser = EnhancedXMLParser()
    return parser.xpath(element, expression, namespaces)
