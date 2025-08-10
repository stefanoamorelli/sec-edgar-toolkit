/**
 * Tests for Current Events (8-K) Parser
 */

import { CurrentEventParser } from '../parsers/current-events';

describe('CurrentEventParser', () => {
  const sample8KContent = `
UNITED STATES
SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549

FORM 8-K

CURRENT REPORT
Pursuant to Section 13 or 15(d) of the Securities Exchange Act of 1934

Date of Report: January 15, 2024

APPLE INC.
(Exact name of registrant as specified in its charter)

California 000-10030 94-2404110
(State of incorporation) (Commission File Number) (IRS Employer ID)

One Apple Park Way
Cupertino, California 95014
(408) 996-1010

Item 1.01 Entry into a Material Definitive Agreement.

On January 15, 2024, Apple Inc. (the "Company") entered into a Strategic Partnership Agreement 
(the "Agreement") with Example Technologies, Inc. ("Example Tech"), a leading provider of 
artificial intelligence solutions. Under the terms of the Agreement, the Company will integrate 
Example Tech's AI technology into its product ecosystem over the next three years.

The Agreement provides for total consideration of up to $500 million, consisting of an upfront 
payment of $200 million and potential milestone payments of up to $300 million based on 
achievement of certain technical and commercial objectives.

Item 2.02 Results of Operations and Financial Condition.

On January 15, 2024, the Company announced its financial results for the fiscal quarter ended 
December 31, 2023. The Company reported revenue of $120 billion, representing a 5% increase 
year-over-year, and net income of $30 billion.

The full earnings release is attached as Exhibit 99.1 to this Current Report on Form 8-K.

Item 5.02 Departure of Directors or Certain Officers; Election of Directors; Appointment of 
Certain Officers; Compensatory Arrangements of Certain Officers.

(b) On January 15, 2024, John Smith, Senior Vice President of Hardware Engineering, notified 
the Company of his intention to retire effective March 31, 2024. Mr. Smith has served in 
this role since 2015 and has been with the Company for over 20 years.

(c) The Board of Directors appointed Jane Doe, age 45, as the new Senior Vice President of 
Hardware Engineering, effective April 1, 2024. Ms. Doe currently serves as Vice President 
of Product Design and has been with the Company since 2010.

Item 7.01 Regulation FD Disclosure.

The Company is furnishing the following information pursuant to Item 7.01 of Form 8-K:

Product Launch Update: The Company plans to announce several new products at its Spring 
event scheduled for March 2024, including updates to the iPad and MacBook product lines.

Item 8.01 Other Events.

The Company announced today that its Board of Directors has authorized a new share repurchase 
program of up to $90 billion. This new authorization replaces the previous program, under which 
approximately $85 billion was repurchased.

SIGNATURES

Pursuant to the requirements of the Securities Exchange Act of 1934, the registrant has duly 
caused this report to be signed on its behalf by the undersigned hereunto duly authorized.

APPLE INC.

By: /s/ Luca Maestri
Luca Maestri
Senior Vice President and Chief Financial Officer

Date: January 15, 2024`;

  describe('constructor', () => {
    it('should initialize with form content', () => {
      const parser = new CurrentEventParser(sample8KContent);
      expect(parser).toBeDefined();
    });
  });

  describe('getCurrentEvents', () => {
    it('should extract all current events', () => {
      const parser = new CurrentEventParser(sample8KContent);
      const events = parser.getCurrentEvents();
      
      // Log events to see what's being found
      console.log('Found events:', events.map(e => ({ item: e.item, desc: e.description.substring(0, 50) })));
      expect(events.length).toBeGreaterThanOrEqual(5);
      
      // Check Item 1.01
      const item101 = events.find(e => e.details?.itemNumber === '1.01');
      expect(item101).toBeDefined();
      expect(item101?.description).toContain('Entry into a Material Definitive Agreement');
      expect(item101?.details?.fullText).toBeTruthy();
      
      // Check Item 2.02
      const item202 = events.find(e => e.details?.itemNumber === '2.02');
      expect(item202).toBeDefined();
      expect(item202?.description).toContain('Results of Operations and Financial Condition');
      expect(item202?.details?.fullText).toBeTruthy();
      
      // Check Item 5.02
      const item502 = events.find(e => e.details?.itemNumber === '5.02');
      expect(item502).toBeDefined();
      expect(item502?.description).toContain('Departure of Directors');
      expect(item502?.details?.fullText).toBeTruthy();
      
      // Check Item 7.01
      const item701 = events.find(e => e.details?.itemNumber === '7.01');
      expect(item701).toBeDefined();
      expect(item701?.description).toContain('Regulation FD Disclosure');
      
      // Check Item 8.01
      const item801 = events.find(e => e.details?.itemNumber === '8.01');
      expect(item801).toBeDefined();
      expect(item801?.description).toContain('Other Events');
      expect(item801?.details?.fullText).toBeTruthy();
    });
  });

  describe('getMaterialAgreements', () => {
    it('should extract material agreement details', () => {
      const parser = new CurrentEventParser(sample8KContent);
      const agreements = parser.getMaterialAgreements();
      
      expect(agreements).toHaveLength(1);
      const agreement = agreements[0];
      
      expect(agreement.parties).toContain('APPLE INC.');
      expect(agreement.parties).toContain('Example Technologies');
      expect(agreement.type).toBe('Strategic Partnership Agreement');
      // Check date within 1 day to account for timezone differences
      const agreementDate = agreement.effectiveDate;
      const expectedDate = new Date('2024-01-15');
      const daysDiff = Math.abs(agreementDate.getTime() - expectedDate.getTime()) / (1000 * 60 * 60 * 24);
      expect(daysDiff).toBeLessThan(2);
      expect(agreement.description).toContain('AI technology');
      expect(agreement.value).toBe(500000000);
    });
  });

  describe('getExecutiveChanges', () => {
    it('should extract executive change details', () => {
      const parser = new CurrentEventParser(sample8KContent);
      const changes = parser.getExecutiveChanges();
      
      expect(changes).toHaveLength(2);
      
      // Departure
      const departure = changes.find(c => c.type === 'resignation');
      expect(departure?.person.name).toBe('John Smith');
      expect(departure?.person.position).toBe('Senior Vice President of Hardware Engineering');
      // Check date within 1 day to account for timezone differences
      const departureDate = departure?.effectiveDate;
      const expectedDepartureDate = new Date('2024-03-31');
      if (departureDate) {
        const daysDiff = Math.abs(departureDate.getTime() - expectedDepartureDate.getTime()) / (1000 * 60 * 60 * 24);
        expect(daysDiff).toBeLessThan(2);
      }
      
      // Appointment
      const appointment = changes.find(c => c.type === 'appointment');
      expect(appointment?.person.name).toBe('Jane Doe');
      expect(appointment?.person.position).toBe('Senior Vice President of Hardware Engineering');
      // Check date within 1 day to account for timezone differences  
      const appointmentDate = appointment?.effectiveDate;
      const expectedAppointmentDate = new Date('2024-04-01');
      if (appointmentDate) {
        const daysDiff = Math.abs(appointmentDate.getTime() - expectedAppointmentDate.getTime()) / (1000 * 60 * 60 * 24);
        expect(daysDiff).toBeLessThan(2);
      }
    });
  });

  describe('getEarningsResults', () => {
    it('should extract earnings results', () => {
      const parser = new CurrentEventParser(sample8KContent);
      const results = parser.getEarningsResults();
      
      expect(results).toBeDefined();
      if (results) {
        expect(results.period).toContain('December 31, 2023');
        expect(results.revenue).toBe(120000000000);
        expect(results.netIncome).toBe(30000000000);
      }
    });
  });

  describe('edge cases', () => {
    it('should handle content without events', () => {
      const emptyContent = 'This is a document without any items.';
      const parser = new CurrentEventParser(emptyContent);
      const events = parser.getCurrentEvents();
      
      expect(events).toHaveLength(0);
    });

    it('should handle malformed item numbers', () => {
      const malformedContent = `
Item 1.1 Invalid Item Number
Some content here

ITEM 2.02. Valid Item
More content`;
      
      const parser = new CurrentEventParser(malformedContent);
      const events = parser.getCurrentEvents();
      
      console.log('Malformed test events:', events);
      // Should find both items since the pattern is case-insensitive
      expect(events).toHaveLength(2);
      expect(events[0].details?.itemNumber).toBe('1.1');
      expect(events[1].details?.itemNumber).toBe('2.02');
    });
  });
});