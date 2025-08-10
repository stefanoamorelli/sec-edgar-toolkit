/**
 * Tests for Ownership Forms Parser
 */

import { OwnershipFormParser, Form4Parser, Form5Parser } from '../parsers/ownership-forms';

describe('OwnershipFormParser', () => {
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

  describe('constructor', () => {
    it('should parse valid XML content', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      expect(parser).toBeDefined();
      expect(parser.formType).toBe('4');
    });

    it('should throw error on invalid XML', () => {
      expect(() => new OwnershipFormParser('invalid xml')).toThrow();
    });
  });

  describe('parseDocumentInfo', () => {
    it('should extract document metadata', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const docInfo = parser.parseDocumentInfo();
      
      expect(docInfo.formType).toBe('4');
      expect(docInfo.schemaVersion).toBe('X0306');
      expect(docInfo.documentType).toBe('4');
      expect(docInfo.periodOfReport).toEqual(new Date('2024-01-15'));
    });
  });

  describe('parseIssuerInfo', () => {
    it('should extract issuer information', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const issuerInfo = parser.parseIssuerInfo();
      
      expect(issuerInfo.cik).toBe('0000320193');
      expect(issuerInfo.name).toBe('APPLE INC');
      expect(issuerInfo.tradingSymbol).toBe('AAPL');
    });
  });

  describe('parseReportingOwnerInfo', () => {
    it('should extract reporting owner details', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const ownerInfo = parser.parseReportingOwnerInfo();
      
      expect(ownerInfo.cik).toBe('0001234567');
      expect(ownerInfo.name).toBe('COOK TIMOTHY D');
      expect(ownerInfo.street1).toBe('ONE APPLE PARK WAY');
      expect(ownerInfo.city).toBe('CUPERTINO');
      expect(ownerInfo.state).toBe('CA');
      expect(ownerInfo.zipCode).toBe('95014');
      
      expect(ownerInfo.relationship).toEqual({
        isDirector: true,
        isOfficer: true,
        isTenPercentOwner: false,
        isOther: false,
        officerTitle: 'Chief Executive Officer',
        otherText: ''
      });
    });
  });

  describe('parseNonDerivativeTransactions', () => {
    it('should extract non-derivative transactions', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const transactions = parser.parseNonDerivativeTransactions();
      
      expect(transactions).toHaveLength(1);
      const transaction = transactions[0];
      
      expect(transaction.securityTitle).toBe('Common Stock');
      expect(transaction.transactionDate).toEqual(new Date('2024-01-15'));
      expect(transaction.shares).toBe(50000);
      expect(transaction.pricePerShare).toBe(150.00);
      expect(transaction.acquiredDisposedCode).toBe('A');
      expect(transaction.formType).toBe('4');
      expect(transaction.code).toBe('M');
      expect(transaction.equitySwapInvolved).toBe(false);
      expect(transaction.sharesOwnedFollowingTransaction).toBe(1000000);
      expect(transaction.directOrIndirectOwnership).toBe('D');
    });
  });

  describe('parseAll', () => {
    it('should parse all form data', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const result = parser.parseAll();
      
      expect(result).toHaveProperty('documentInfo');
      expect(result).toHaveProperty('issuerInfo');
      expect(result).toHaveProperty('reportingOwnerInfo');
      expect(result).toHaveProperty('nonDerivativeTransactions');
      expect(result).toHaveProperty('nonDerivativeHoldings');
      expect(result).toHaveProperty('derivativeTransactions');
    });
  });
});

describe('Form4Parser', () => {
  const sampleForm4XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>4</documentType>
</ownershipDocument>`;

  it('should initialize with Form 4', () => {
    const parser = new Form4Parser(sampleForm4XML);
    expect(parser.formType).toBe('4');
  });

  it('should warn if not Form 4', () => {
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    const form5XML = sampleForm4XML.replace('documentType>4<', 'documentType>5<');
    new Form4Parser(form5XML);
    
    expect(consoleSpy).toHaveBeenCalledWith('Expected Form 4, but found Form 5');
    consoleSpy.mockRestore();
  });
});

describe('Form5Parser', () => {
  const sampleForm5XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <documentType>5</documentType>
</ownershipDocument>`;

  it('should initialize with Form 5', () => {
    const parser = new Form5Parser(sampleForm5XML);
    expect(parser.formType).toBe('5');
  });

  it('should warn if not Form 5', () => {
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    const form4XML = sampleForm5XML.replace('documentType>5<', 'documentType>4<');
    new Form5Parser(form4XML);
    
    expect(consoleSpy).toHaveBeenCalledWith('Expected Form 5, but found Form 4');
    consoleSpy.mockRestore();
  });
});