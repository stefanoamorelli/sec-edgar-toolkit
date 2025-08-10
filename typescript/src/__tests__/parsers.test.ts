import { OwnershipFormParser, Form4Parser, Form5Parser, OwnershipFormParseError } from '../parsers/ownership-forms';

describe('Ownership Form Parsers', () => {
  const sampleForm4XML = `<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <schemaVersion>X0306</schemaVersion>
  <documentType>4</documentType>
  <periodOfReport>2024-01-15</periodOfReport>
  <dateOfOriginalSubmission>2024-01-17</dateOfOriginalSubmission>
  
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc.</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001214128</rptOwnerCik>
      <rptOwnerName>Cook Timothy D</rptOwnerName>
      <rptOwnerStreet1>One Apple Park Way</rptOwnerStreet1>
      <rptOwnerCity>Cupertino</rptOwnerCity>
      <rptOwnerState>CA</rptOwnerState>
      <rptOwnerZipCode>95014</rptOwnerZipCode>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>false</isDirector>
      <isOfficer>true</isOfficer>
      <isTenPercentOwner>false</isTenPercentOwner>
      <isOther>false</isOther>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle>
        <value>Common Stock</value>
      </securityTitle>
      <transactionDate>
        <value>2024-01-15</value>
      </transactionDate>
      <transactionAmounts>
        <transactionShares>
          <value>10000</value>
        </transactionShares>
        <transactionPricePerShare>
          <value>185.50</value>
        </transactionPricePerShare>
        <transactionAcquiredDisposedCode>
          <value>D</value>
        </transactionAcquiredDisposedCode>
      </transactionAmounts>
      <postTransactionAmounts>
        <sharesOwnedFollowingTransaction>
          <value>3400000</value>
        </sharesOwnedFollowingTransaction>
        <directOrIndirectOwnership>
          <value>D</value>
        </directOrIndirectOwnership>
      </postTransactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>`;

  describe('OwnershipFormParser', () => {
    test('should parse Form 4 XML correctly', () => {
      const parser = new OwnershipFormParser(sampleForm4XML);
      const result = parser.parseAll();

      expect(result.documentInfo.formType).toBe('4');
      expect(result.documentInfo.schemaVersion).toBe('X0306');
      expect(result.documentInfo.periodOfReport).toEqual(new Date('2024-01-15'));
      
      expect(result.issuerInfo.cik).toBe('0000320193');
      expect(result.issuerInfo.name).toBe('Apple Inc.');
      expect(result.issuerInfo.tradingSymbol).toBe('AAPL');
      
      expect(result.reportingOwnerInfo.cik).toBe('0001214128');
      expect(result.reportingOwnerInfo.name).toBe('Cook Timothy D');
      expect(result.reportingOwnerInfo.relationship?.isOfficer).toBe(true);
      expect(result.reportingOwnerInfo.relationship?.officerTitle).toBe('Chief Executive Officer');
      
      expect(result.nonDerivativeTransactions).toHaveLength(1);
      const transaction = result.nonDerivativeTransactions[0];
      expect(transaction.securityTitle).toBe('Common Stock');
      expect(transaction.shares).toBe(10000);
      expect(transaction.pricePerShare).toBe(185.50);
      expect(transaction.acquiredDisposedCode).toBe('D');
      expect(transaction.sharesOwnedFollowingTransaction).toBe(3400000);
    });

    test('should handle invalid XML', () => {
      const invalidXML = 'not xml at all';
      expect(() => new OwnershipFormParser(invalidXML)).toThrow(OwnershipFormParseError);
    });

    test('should handle Buffer input', () => {
      const buffer = Buffer.from(sampleForm4XML, 'utf-8');
      const parser = new OwnershipFormParser(buffer);
      const result = parser.parseAll();
      
      expect(result.documentInfo.formType).toBe('4');
      expect(result.issuerInfo.name).toBe('Apple Inc.');
    });
  });

  describe('Form4Parser', () => {
    test('should create specialized Form 4 parser', () => {
      const parser = new Form4Parser(sampleForm4XML);
      const result = parser.parseAll();
      
      expect(result.documentInfo.formType).toBe('4');
      expect(result.issuerInfo.name).toBe('Apple Inc.');
    });
  });

  describe('Form5Parser', () => {
    test('should create specialized Form 5 parser', () => {
      const form5XML = sampleForm4XML.replace('<documentType>4</documentType>', '<documentType>5</documentType>');
      const parser = new Form5Parser(form5XML);
      const result = parser.parseAll();
      
      expect(result.documentInfo.formType).toBe('5');
    });
  });

  describe('Date parsing', () => {
    test('should parse different date formats', () => {
      const xmlWithSlashDate = sampleForm4XML.replace('2024-01-15', '01/15/2024');
      const parser = new OwnershipFormParser(xmlWithSlashDate);
      const result = parser.parseAll();
      
      // Compare just the date parts to avoid timezone issues
      const actualDate = result.documentInfo.periodOfReport;
      expect(actualDate?.getFullYear()).toBe(2024);
      expect(actualDate?.getMonth()).toBe(0); // January is 0
      expect(actualDate?.getDate()).toBe(15);
    });
  });

  describe('Error handling', () => {
    test('should throw OwnershipFormParseError for malformed XML', () => {
      expect(() => new OwnershipFormParser('completely invalid')).toThrow(OwnershipFormParseError);
    });

    test('should handle missing form type gracefully', () => {
      const xmlWithoutType = sampleForm4XML.replace('<documentType>4</documentType>', '');
      const parser = new OwnershipFormParser(xmlWithoutType);
      
      // Should fall back to checking schema version and assume Form 4
      expect(parser.parseDocumentInfo().formType).toBe('4');
    });
  });
});