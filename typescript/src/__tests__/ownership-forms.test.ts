/**
 * Tests for Ownership Forms Parser
 */

import {
  OwnershipFormParser,
  Form4Parser,
  Form5Parser,
} from "../parsers/ownership-forms";
import { OwnershipHolding } from "../core/ownership";

describe("OwnershipFormParser", () => {
  const sampleForm4XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0306</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2024-01-15</periodOfReport>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>APPLE INC</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>COOK TIMOTHY D</rptOwnerName>
            <rptOwnerStreet1>ONE APPLE PARK WAY</rptOwnerStreet1>
            <rptOwnerCity>CUPERTINO</rptOwnerCity>
            <rptOwnerState>CA</rptOwnerState>
            <rptOwnerZipCode>95014</rptOwnerZipCode>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>true</isDirector>
            <isOfficer>true</isOfficer>
            <isTenPercentOwner>false</isTenPercentOwner>
            <isOther>false</isOther>
            <officerTitle>Chief Executive Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTransaction>
        <securityTitle>
            <value>Common Stock</value>
        </securityTitle>
        <transactionDate>
            <value>2024-01-15</value>
        </transactionDate>
        <transactionAmounts>
            <transactionShares>
                <value>50000</value>
            </transactionShares>
            <transactionPricePerShare>
                <value>150.00</value>
            </transactionPricePerShare>
            <transactionAcquiredDisposedCode>
                <value>A</value>
            </transactionAcquiredDisposedCode>
        </transactionAmounts>
        <transactionCoding>
            <transactionFormType>4</transactionFormType>
            <transactionCode>M</transactionCode>
            <equitySwapInvolved>false</equitySwapInvolved>
        </transactionCoding>
        <postTransactionAmounts>
            <sharesOwnedFollowingTransaction>
                <value>1000000</value>
            </sharesOwnedFollowingTransaction>
            <directOrIndirectOwnership>
                <value>D</value>
            </directOrIndirectOwnership>
        </postTransactionAmounts>
    </nonDerivativeTransaction>
</ownershipDocument>`;

  describe("constructor", () => {
    it("should parse valid XML content", () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      expect(parser).toBeDefined();
      expect(parser.formType).toBe("4");
    });

    it("should throw error on invalid XML", () => {
      expect(() => new OwnershipFormParser("invalid xml")).toThrow();
    });
  });

  describe("parseDocumentInfo", () => {
    it("should extract document metadata", () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const docInfo = parser.parseDocumentInfo();

      expect(docInfo.formType).toBe("4");
      expect(docInfo.schemaVersion).toBe("X0306");
      expect(docInfo.documentType).toBe("4");
      expect(docInfo.periodOfReport).toEqual(new Date("2024-01-15"));
    });
  });

  describe("parseIssuerInfo", () => {
    it("should extract issuer information", () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const issuerInfo = parser.parseIssuerInfo();

      expect(issuerInfo.cik).toBe("0000320193");
      expect(issuerInfo.name).toBe("APPLE INC");
      expect(issuerInfo.tradingSymbol).toBe("AAPL");
    });
  });

  describe("parseReportingOwnerInfo", () => {
    it("should extract reporting owner details", () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const ownerInfo = parser.parseReportingOwnerInfo();

      expect(ownerInfo.cik).toBe("0001234567");
      expect(ownerInfo.name).toBe("COOK TIMOTHY D");
      expect(ownerInfo.street1).toBe("ONE APPLE PARK WAY");
      expect(ownerInfo.city).toBe("CUPERTINO");
      expect(ownerInfo.state).toBe("CA");
      expect(ownerInfo.zipCode).toBe("95014");

      expect(ownerInfo.relationship).toEqual({
        isDirector: true,
        isOfficer: true,
        isTenPercentOwner: false,
        isOther: false,
        officerTitle: "Chief Executive Officer",
        otherText: "",
      });
    });
  });

  describe("parseNonDerivativeTransactions", () => {
    it("should extract non-derivative transactions", () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const transactions = parser.parseNonDerivativeTransactions();

      expect(transactions).toHaveLength(1);
      const transaction = transactions[0];

      expect(transaction.securityTitle).toBe("Common Stock");
      expect(transaction.transactionDate).toEqual(new Date("2024-01-15"));
      expect(transaction.shares).toBe(50000);
      expect(transaction.pricePerShare).toBe(150.0);
      expect(transaction.acquiredDisposedCode).toBe("A");
      expect(transaction.formType).toBe("4");
      expect(transaction.code).toBe("M");
      expect(transaction.equitySwapInvolved).toBe(false);
      expect(transaction.sharesOwnedFollowingTransaction).toBe(1000000);
      expect(transaction.directOrIndirectOwnership).toBe("D");
    });
  });

  describe("parseAll", () => {
    it("should parse all form data", () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const result = parser.parseAll();

      expect(result).toHaveProperty("documentInfo");
      expect(result).toHaveProperty("issuerInfo");
      expect(result).toHaveProperty("reportingOwnerInfo");
      expect(result).toHaveProperty("nonDerivativeTransactions");
      expect(result).toHaveProperty("nonDerivativeHoldings");
      expect(result).toHaveProperty("derivativeTransactions");
    });
  });
});

describe("Form4Parser", () => {
  const sampleForm4XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
</ownershipDocument>`;

  it("should initialize with Form 4", () => {
    const parser = new Form4Parser(sampleForm4XML);
    expect(parser.formType).toBe("4");
  });

  it("should warn if not Form 4", () => {
    const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
    const form5XML = sampleForm4XML.replace(
      "documentType>4<",
      "documentType>5<",
    );
    new Form4Parser(form5XML);

    expect(consoleSpy).toHaveBeenCalledWith(
      "Expected Form 4, but found Form 5",
    );
    consoleSpy.mockRestore();
  });
});

describe("Form5Parser", () => {
  const sampleForm5XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>5</documentType>
</ownershipDocument>`;

  it("should initialize with Form 5", () => {
    const parser = new Form5Parser(sampleForm5XML);
    expect(parser.formType).toBe("5");
  });

  it("should warn if not Form 5", () => {
    const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
    const form4XML = sampleForm5XML.replace(
      "documentType>5<",
      "documentType>4<",
    );
    new Form5Parser(form4XML);

    expect(consoleSpy).toHaveBeenCalledWith(
      "Expected Form 5, but found Form 4",
    );
    consoleSpy.mockRestore();
  });
});

describe("OwnershipFormParser boolean encodings", () => {
  const numericForm4XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0306</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2026-09-22</periodOfReport>
    <notSubjectToSection16>0</notSubjectToSection16>
    <issuer>
        <issuerCik>0001318605</issuerCik>
        <issuerName>Tesla, Inc.</issuerName>
        <issuerTradingSymbol>TSLA</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001494730</rptOwnerCik>
            <rptOwnerName>Musk Elon</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>1</isOfficer>
            <isTenPercentOwner>1</isTenPercentOwner>
            <isOther>0</isOther>
            <officerTitle>CEO</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-09-22</value></transactionDate>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>S</transactionCode>
                <equitySwapInvolved>1</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>100</value></transactionShares>
                <transactionPricePerShare><value>250.5</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>900</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
            <ownershipNature>
                <directOrIndirectOwnership><value>I</value></directOrIndirectOwnership>
                <natureOfOwnership><value>By Trust</value></natureOfOwnership>
            </ownershipNature>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>`;

  it("accepts 1/0 for the reporting owner relationship flags", () => {
    const parser = new OwnershipFormParser(numericForm4XML);
    const relationship = parser.parseReportingOwnerInfo().relationship;

    expect(relationship).toEqual({
      isDirector: true,
      isOfficer: true,
      isTenPercentOwner: true,
      isOther: false,
      officerTitle: "CEO",
      otherText: "",
    });
  });

  it("accepts 1/0 for equitySwapInvolved and notSubjectToSection16", () => {
    const parser = new OwnershipFormParser(numericForm4XML);

    expect(parser.parseNonDerivativeTransactions()[0].equitySwapInvolved).toBe(
      true,
    );
    expect(parser.parseDocumentInfo().notSubjectToSection16).toBe(false);
  });

  it("reads ownership fields nested under ownershipNature", () => {
    const parser = new OwnershipFormParser(numericForm4XML);
    const transaction = parser.parseNonDerivativeTransactions()[0];

    expect(transaction.directOrIndirectOwnership).toBe("I");
    expect(transaction.natureOfOwnership).toBe("By Trust");
    expect(transaction.sharesOwnedFollowingTransaction).toBe(900);
  });
});

describe("OwnershipFormParser derivative transaction details", () => {
  const derivativeForm4XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0306</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2026-09-15</periodOfReport>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>Apple Inc.</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001214128</rptOwnerCik>
            <rptOwnerName>Newstead Jennifer</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isOfficer>true</isOfficer>
            <officerTitle>SVP, GC and Government Affairs</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <derivativeTable>
        <derivativeTransaction>
            <securityTitle><value>Restricted Stock Unit</value></securityTitle>
            <conversionOrExercisePrice><footnoteId id="F2"/></conversionOrExercisePrice>
            <transactionDate><value>2026-09-15</value></transactionDate>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>M</transactionCode>
                <equitySwapInvolved>0</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>30104</value></transactionShares>
                <transactionPricePerShare><value>12.5</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <exerciseDate><footnoteId id="F4"/></exerciseDate>
            <expirationDate><footnoteId id="F4"/></expirationDate>
            <underlyingSecurity>
                <underlyingSecurityTitle><value>Common Stock</value></underlyingSecurityTitle>
                <underlyingSecurityShares><value>30104</value></underlyingSecurityShares>
            </underlyingSecurity>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>180624</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
            <ownershipNature>
                <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
            </ownershipNature>
        </derivativeTransaction>
    </derivativeTable>
</ownershipDocument>`;

  it("keeps the coding, price and post-transaction blocks", () => {
    const parser = new OwnershipFormParser(derivativeForm4XML);
    const transaction = parser.parseDerivativeTransactions()[0];

    expect(transaction.securityTitle).toBe("Restricted Stock Unit");
    expect(transaction.code).toBe("M");
    expect(transaction.formType).toBe("4");
    expect(transaction.equitySwapInvolved).toBe(false);
    expect(transaction.pricePerShare).toBe(12.5);
    expect(transaction.shares).toBe(30104);
    expect(transaction.acquiredDisposedCode).toBe("D");
    expect(transaction.sharesOwnedFollowingTransaction).toBe(180624);
    expect(transaction.directOrIndirectOwnership).toBe("D");
    expect(transaction.underlyingSecurity).toEqual({
      title: "Common Stock",
      shares: 30104,
    });
  });
});

describe("OwnershipFormParser holding layouts", () => {
  const filedHoldingXML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0508</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2026-06-30</periodOfReport>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>Apple Inc.</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001214128</rptOwnerCik>
            <rptOwnerName>COOK TIMOTHY D</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>1</isOfficer>
            <officerTitle>Chief Executive Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeHolding>
            <securityTitle><value>Common Stock</value></securityTitle>
            <postTransactionAmounts>
                <sharesOwnedFollowingTransaction><value>56000</value></sharesOwnedFollowingTransaction>
            </postTransactionAmounts>
            <ownershipNature>
                <directOrIndirectOwnership><value>I</value></directOrIndirectOwnership>
                <natureOfOwnership><value>By Spouse</value></natureOfOwnership>
            </ownershipNature>
        </nonDerivativeHolding>
    </nonDerivativeTable>
</ownershipDocument>`;

  it("reads shares and ownership from the filed layout", () => {
    const parser = new OwnershipFormParser(filedHoldingXML);
    const holding = parser.parseNonDerivativeHoldings()[0];

    expect(holding.securityTitle).toBe("Common Stock");
    expect(holding.sharesOwned).toBe(56000);
    expect(holding.directOrIndirectOwnership).toBe("I");
    expect(holding.natureOfOwnership).toBe("By Spouse");
  });

  it("maps derivative holding shares onto OwnershipHolding", () => {
    const holding = new OwnershipHolding({
      securityTitle: "Restricted Stock Unit",
      shares: 66600,
    } as any);

    expect(holding.sharesOwned).toBe(66600);
  });
});
