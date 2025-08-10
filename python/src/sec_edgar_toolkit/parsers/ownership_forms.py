"""
Parser for SEC ownership forms (Form 3, 4, and 5) XML documents.

These forms contain information about insider transactions and holdings
by officers, directors, and significant shareholders.

Form 3: Initial statement of beneficial ownership
Form 4: Changes in beneficial ownership
Form 5: Annual statement of changes in beneficial ownership
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..exceptions import SecEdgarApiError
from ..utils.xml_parser import EnhancedXMLParser, parse_xml

logger = logging.getLogger(__name__)


class OwnershipFormParseError(SecEdgarApiError):
    """Exception raised when parsing ownership forms fails."""

    pass


class OwnershipFormParser:
    """
    Base parser for SEC ownership forms (Forms 3, 4, and 5).

    This parser extracts structured data from XML ownership forms filed with the SEC.
    The forms contain information about insider transactions and stock holdings.

    Attributes:
        xml_content: Raw XML content as string or bytes
        root: Parsed XML root element
        form_type: Type of form (3, 4, or 5)
    """

    def __init__(self, xml_content: Union[str, bytes]) -> None:
        """
        Initialize the ownership form parser.

        Args:
            xml_content: Raw XML content of the form

        Raises:
            OwnershipFormParseError: If XML parsing fails
        """
        self.xml_content = xml_content
        self.parser = EnhancedXMLParser(recover=True, remove_blank_text=True)

        try:
            self.root = self.parser.parse_string(xml_content)
        except Exception as e:
            raise OwnershipFormParseError(f"Failed to parse XML: {e}") from e

        self.form_type = self._extract_form_type()
        logger.info(f"Initialized parser for Form {self.form_type}")

    def _extract_form_type(self) -> str:
        """Extract the form type from the XML document."""
        # Try multiple possible locations for form type
        form_type_elem = self.root.find(".//documentType")
        if form_type_elem is not None and form_type_elem.text:
            return form_type_elem.text.strip()

        # Fallback: check schemaVersion or other indicators
        schema_elem = self.root.find(".//schemaVersion")
        if schema_elem is not None:
            # Assume it's a Form 4 if we can't find explicit type
            return "4"

        raise OwnershipFormParseError("Could not determine form type from XML")

    def _get_text(self, element: Optional[Any], default: str = "") -> str:
        """Safely extract text from an XML element."""
        return self.parser.get_text(element, default)

    def _get_float(self, element: Optional[Any], default: float = 0.0) -> float:
        """Safely extract float value from an XML element."""
        text = self._get_text(element)
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    def _get_date(self, element: Optional[Any]) -> Optional[datetime]:
        """Extract date from XML element and convert to datetime object."""
        date_text = self._get_text(element)
        if not date_text:
            return None

        # Try different date formats
        date_formats = [
            "%Y-%m-%d",  # 2024-01-15
            "%m/%d/%Y",  # 01/15/2024
            "%m-%d-%Y",  # 01-15-2024
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_text}")
        return None

    def parse_document_info(self) -> Dict[str, Any]:
        """
        Parse document-level information from the form.

        Returns:
            Dictionary containing document metadata
        """
        doc_info: Dict[str, Any] = {
            "form_type": self.form_type,
            "schema_version": self._get_text(self.root.find(".//schemaVersion")),
            "document_type": self._get_text(self.root.find(".//documentType")),
            "period_of_report": self._get_date(self.root.find(".//periodOfReport")),
            "date_of_original_submission": self._get_date(
                self.root.find(".//dateOfOriginalSubmission")
            ),
        }

        # Add notSubjectToSection16 flag if present
        not_subject_elem = self.root.find(".//notSubjectToSection16")
        if not_subject_elem is not None:
            doc_info["not_subject_to_section16"] = (
                self._get_text(not_subject_elem).lower() == "true"
            )

        return doc_info

    def parse_issuer_info(self) -> Dict[str, Any]:
        """
        Parse information about the issuer (company) from the form.

        Returns:
            Dictionary containing issuer information
        """
        issuer_elem = self.root.find(".//issuer")
        if issuer_elem is None:
            return {}

        return {
            "cik": self._get_text(issuer_elem.find("issuerCik")),
            "name": self._get_text(issuer_elem.find("issuerName")),
            "trading_symbol": self._get_text(issuer_elem.find("issuerTradingSymbol")),
        }

    def parse_reporting_owner_info(self) -> Dict[str, Any]:
        """
        Parse information about the reporting owner (insider) from the form.

        Returns:
            Dictionary containing reporting owner information
        """
        owner_elem = self.root.find(".//reportingOwner")
        if owner_elem is None:
            return {}

        owner_info: Dict[str, Any] = {}

        # Parse owner identification
        owner_id = owner_elem.find("reportingOwnerId")
        if owner_id is not None:
            owner_info.update(
                {
                    "cik": self._get_text(owner_id.find("rptOwnerCik")),
                    "name": self._get_text(owner_id.find("rptOwnerName")),
                    "street1": self._get_text(owner_id.find("rptOwnerStreet1")),
                    "street2": self._get_text(owner_id.find("rptOwnerStreet2")),
                    "city": self._get_text(owner_id.find("rptOwnerCity")),
                    "state": self._get_text(owner_id.find("rptOwnerState")),
                    "zip_code": self._get_text(owner_id.find("rptOwnerZipCode")),
                    "state_description": self._get_text(
                        owner_id.find("rptOwnerStateDescription")
                    ),
                }
            )

        # Parse owner relationship
        relationship = owner_elem.find("reportingOwnerRelationship")
        if relationship is not None:
            owner_info["relationship"] = {
                "is_director": self._get_text(relationship.find("isDirector")).lower()
                == "true",
                "is_officer": self._get_text(relationship.find("isOfficer")).lower()
                == "true",
                "is_ten_percent_owner": self._get_text(
                    relationship.find("isTenPercentOwner")
                ).lower()
                == "true",
                "is_other": self._get_text(relationship.find("isOther")).lower()
                == "true",
                "officer_title": self._get_text(relationship.find("officerTitle")),
                "other_text": self._get_text(relationship.find("otherText")),
            }

        return owner_info

    def parse_non_derivative_transactions(self) -> List[Dict[str, Any]]:
        """
        Parse non-derivative transactions from the form.

        Returns:
            List of dictionaries containing transaction information
        """
        transactions = []

        for transaction_elem in self.root.findall(".//nonDerivativeTransaction"):
            transaction: Dict[str, Any] = {}

            # Security title
            security = transaction_elem.find("securityTitle")
            if security is not None:
                transaction["security_title"] = self._get_text(security.find("value"))

            # Transaction date
            trans_date = transaction_elem.find("transactionDate")
            if trans_date is not None:
                transaction["transaction_date"] = self._get_date(
                    trans_date.find("value")
                )

            # Transaction amounts
            amounts = transaction_elem.find("transactionAmounts")
            if amounts is not None:
                transaction.update(
                    {
                        "shares": self._get_float(
                            amounts.find("transactionShares/value")
                        ),
                        "price_per_share": self._get_float(
                            amounts.find("transactionPricePerShare/value")
                        ),
                        "acquired_disposed_code": self._get_text(
                            amounts.find("transactionAcquiredDisposedCode/value")
                        ),
                    }
                )

            # Transaction coding
            coding = transaction_elem.find("transactionCoding")
            if coding is not None:
                transaction.update(
                    {
                        "form_type": self._get_text(coding.find("transactionFormType")),
                        "code": self._get_text(coding.find("transactionCode")),
                        "equity_swap_involved": self._get_text(
                            coding.find("equitySwapInvolved")
                        ).lower()
                        == "true",
                    }
                )

            # Post-transaction amounts
            post_trans = transaction_elem.find("postTransactionAmounts")
            if post_trans is not None:
                transaction.update(
                    {
                        "shares_owned_following_transaction": self._get_float(
                            post_trans.find("sharesOwnedFollowingTransaction/value")
                        ),
                        "direct_or_indirect_ownership": self._get_text(
                            post_trans.find("directOrIndirectOwnership/value")
                        ),
                    }
                )

            # Ownership nature
            ownership = transaction_elem.find("ownershipNature")
            if ownership is not None:
                transaction["nature_of_ownership"] = self._get_text(
                    ownership.find("value")
                )

            transactions.append(transaction)

        return transactions

    def parse_non_derivative_holdings(self) -> List[Dict[str, Any]]:
        """
        Parse non-derivative holdings from the form.

        Returns:
            List of dictionaries containing holding information
        """
        holdings = []

        for holding_elem in self.root.findall(".//nonDerivativeHolding"):
            holding: Dict[str, Any] = {}

            # Security title
            security = holding_elem.find("securityTitle")
            if security is not None:
                holding["security_title"] = self._get_text(security.find("value"))

            # Shares owned
            shares = holding_elem.find("sharesOwned")
            if shares is not None:
                holding["shares_owned"] = self._get_float(shares.find("value"))

            # Direct or indirect ownership
            ownership_type = holding_elem.find("directOrIndirectOwnership")
            if ownership_type is not None:
                holding["direct_or_indirect_ownership"] = self._get_text(
                    ownership_type.find("value")
                )

            # Nature of ownership
            nature = holding_elem.find("ownershipNature")
            if nature is not None:
                holding["nature_of_ownership"] = self._get_text(nature.find("value"))

            holdings.append(holding)

        return holdings

    def parse_derivative_transactions(self) -> List[Dict[str, Any]]:
        """
        Parse derivative transactions (options, warrants, etc.) from the form.

        Returns:
            List of dictionaries containing derivative transaction information
        """
        transactions = []

        for transaction_elem in self.root.findall(".//derivativeTransaction"):
            transaction: Dict[str, Any] = {}

            # Security title
            security = transaction_elem.find("securityTitle")
            if security is not None:
                transaction["security_title"] = self._get_text(security.find("value"))

            # Conversion or exercise price
            conversion = transaction_elem.find("conversionOrExercisePrice")
            if conversion is not None:
                transaction["conversion_or_exercise_price"] = self._get_float(
                    conversion.find("value")
                )

            # Transaction date
            trans_date = transaction_elem.find("transactionDate")
            if trans_date is not None:
                transaction["transaction_date"] = self._get_date(
                    trans_date.find("value")
                )

            # Transaction amounts
            amounts = transaction_elem.find("transactionAmounts")
            if amounts is not None:
                transaction.update(
                    {
                        "shares": self._get_float(
                            amounts.find("transactionShares/value")
                        ),
                        "total_value": self._get_float(
                            amounts.find("transactionTotalValue/value")
                        ),
                        "acquired_disposed_code": self._get_text(
                            amounts.find("transactionAcquiredDisposedCode/value")
                        ),
                    }
                )

            # Exercise date and expiration date
            exercise_date = transaction_elem.find("exerciseDate")
            if exercise_date is not None:
                transaction["exercise_date"] = self._get_date(
                    exercise_date.find("value")
                )

            expiration_date = transaction_elem.find("expirationDate")
            if expiration_date is not None:
                transaction["expiration_date"] = self._get_date(
                    expiration_date.find("value")
                )

            # Underlying security
            underlying = transaction_elem.find("underlyingSecurity")
            if underlying is not None:
                transaction["underlying_security"] = {
                    "title": self._get_text(
                        underlying.find("underlyingSecurityTitle/value")
                    ),
                    "shares": self._get_float(
                        underlying.find("underlyingSecurityShares/value")
                    ),
                }

            transactions.append(transaction)

        return transactions

    def parse_all(self) -> Dict[str, Any]:
        """
        Parse all information from the ownership form.

        Returns:
            Complete dictionary containing all parsed form data
        """
        return {
            "document_info": self.parse_document_info(),
            "issuer_info": self.parse_issuer_info(),
            "reporting_owner_info": self.parse_reporting_owner_info(),
            "non_derivative_transactions": self.parse_non_derivative_transactions(),
            "non_derivative_holdings": self.parse_non_derivative_holdings(),
            "derivative_transactions": self.parse_derivative_transactions(),
        }


class Form4Parser(OwnershipFormParser):
    """
    Specialized parser for Form 4 (Changes in Beneficial Ownership).

    Form 4 must be filed within 2 business days of a transaction.
    """

    def __init__(self, xml_content: Union[str, bytes]) -> None:
        super().__init__(xml_content)
        if self.form_type != "4":
            logger.warning(f"Expected Form 4, but found Form {self.form_type}")


class Form5Parser(OwnershipFormParser):
    """
    Specialized parser for Form 5 (Annual Statement of Changes in Beneficial Ownership).

    Form 5 is filed annually and reports transactions that were exempt from
    Form 4 reporting requirements.
    """

    def __init__(self, xml_content: Union[str, bytes]) -> None:
        super().__init__(xml_content)
        if self.form_type != "5":
            logger.warning(f"Expected Form 5, but found Form {self.form_type}")
