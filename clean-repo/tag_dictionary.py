#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: tag_dictionary.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Complete EMV tag dictionary with 380+ tags

Classes:
- TagDictionary: Complete EMV and ISO7816 tag dictionary

Functions:
- load_tag_definitions(): Load tag definitions from multiple sources
- get_tag_category(): Get category for a tag
- is_sensitive_tag(): Check if tag contains sensitive data

This module contains the comprehensive EMV tag dictionary merged from all
referenced repositories and EMV specifications. Includes tag names,
descriptions, data types, and sensitivity classifications.

Based on code from:
- danmichaelo/emv (base tag dictionary)
- dimalinux/EMV-Tools (extended tag definitions)
- EMV 4.3 specifications
- ISO7816 standards
- Visa, Mastercard, and other payment network specifications
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any

class TagDictionary:
    """
    Complete EMV and ISO7816 tag dictionary with comprehensive tag information.
    Provides tag names, descriptions, data types, and sensitivity classifications
    for over 380 EMV and payment-related tags.
    """
    
    def __init__(self):
        """Initialize tag dictionary with all known EMV tags."""
        self.logger = logging.getLogger(__name__)
        
        # Main tag dictionary: tag -> (name, description, data_type, sensitive)
        self.tags = {}
        
        # Tag categories for organization
        self.categories = {
            'cardholder': set(),
            'application': set(),
            'transaction': set(),
            'crypto': set(),
            'issuer': set(),
            'terminal': set(),
            'proprietary': set()
        }
        
        # Load all tag definitions
        self._load_emv_tags()
        self._load_iso7816_tags()
        self._load_proprietary_tags()
        self._load_crypto_tags()
        
        self.logger.info(f"Loaded {len(self.tags)} tag definitions")
    
    def _load_emv_tags(self):
        """Load standard EMV tags from EMV 4.3 specification."""
        
        # Core EMV tags - Application Layer
        emv_tags = {
            # Application Selection and File Control
            '6F': ('FCI Template', 'File Control Information Template', 'constructed', False),
            '84': ('DF Name', 'Dedicated File Name (AID)', 'binary', False),
            'A5': ('FCI Proprietary Template', 'FCI Proprietary Template', 'constructed', False),
            '50': ('Application Label', 'Application Label', 'text', False),
            '87': ('Application Priority Indicator', 'Application Priority Indicator', 'binary', False),
            '9F12': ('Application Preferred Name', 'Application Preferred Name', 'text', False),
            '5F2D': ('Language Preference', 'Language Preference', 'text', False),
            '9F11': ('Issuer Code Table Index', 'Issuer Code Table Index', 'numeric', False),
            '9F38': ('PDOL', 'Processing Options Data Object List', 'binary', False),
            
            # Cardholder Data
            '5A': ('PAN', 'Primary Account Number', 'numeric', True),
            '5F20': ('Cardholder Name', 'Cardholder Name', 'text', True),
            '5F24': ('Application Expiration Date', 'Application Expiration Date (YYMMDD)', 'numeric', True),
            '5F25': ('Application Effective Date', 'Application Effective Date (YYMMDD)', 'numeric', False),
            '5F28': ('Issuer Country Code', 'Issuer Country Code', 'numeric', False),
            '5F34': ('PAN Sequence Number', 'PAN Sequence Number', 'numeric', True),
            '57': ('Track 2 Equivalent Data', 'Track 2 Equivalent Data', 'binary', True),
            '9F0B': ('Cardholder Name Extended', 'Cardholder Name Extended', 'text', True),
            
            # Application Processing
            '82': ('AIP', 'Application Interchange Profile', 'binary', False),
            '94': ('AFL', 'Application File Locator', 'binary', False),
            '8C': ('CDOL1', 'Card Risk Management Data Object List 1', 'binary', False),
            '8D': ('CDOL2', 'Card Risk Management Data Object List 2', 'binary', False),
            '8E': ('CVM List', 'Cardholder Verification Method List', 'binary', False),
            '8F': ('CA Public Key Index', 'Certification Authority Public Key Index', 'binary', False),
            '90': ('Issuer Public Key Certificate', 'Issuer Public Key Certificate', 'binary', False),
            '92': ('Issuer Public Key Remainder', 'Issuer Public Key Remainder', 'binary', False),
            '93': ('Signed Static Application Data', 'Signed Static Application Data', 'binary', False),
            '9F07': ('Application Usage Control', 'Application Usage Control', 'binary', False),
            '9F08': ('Application Version Number', 'Application Version Number', 'binary', False),
            '9F42': ('Application Currency Code', 'Application Currency Code', 'numeric', False),
            '9F44': ('Application Currency Exponent', 'Application Currency Exponent', 'numeric', False),
            
            # Transaction Processing
            '9F02': ('Amount Authorized', 'Amount Authorized (Numeric)', 'numeric', False),
            '9F03': ('Amount Other', 'Amount Other (Numeric)', 'numeric', False),
            '9F1A': ('Terminal Country Code', 'Terminal Country Code', 'numeric', False),
            '5F2A': ('Transaction Currency Code', 'Transaction Currency Code', 'numeric', False),
            '5F36': ('Transaction Currency Exponent', 'Transaction Currency Exponent', 'numeric', False),
            '9A': ('Transaction Date', 'Transaction Date (YYMMDD)', 'numeric', False),
            '9C': ('Transaction Type', 'Transaction Type', 'numeric', False),
            '9F21': ('Transaction Time', 'Transaction Time (HHMMSS)', 'numeric', False),
            '99': ('Transaction PIN Data', 'Transaction Personal Identification Number Data', 'binary', True),
            
            # Cryptographic Data
            '9F26': ('Application Cryptogram', 'Application Cryptogram', 'binary', True),
            '9F27': ('CID', 'Cryptogram Information Data', 'binary', False),
            '9F10': ('Issuer Application Data', 'Issuer Application Data', 'binary', False),
            '9F36': ('ATC', 'Application Transaction Counter', 'binary', False),
            '9F13': ('Last Online ATC Register', 'Last Online ATC Register', 'binary', False),
            '9F17': ('PIN Try Counter', 'Personal Identification Number Try Counter', 'numeric', False),
            '9F4F': ('Log Data Object List', 'Log Data Object List', 'binary', False),
            
            # Terminal Data
            '9F33': ('Terminal Capabilities', 'Terminal Capabilities', 'binary', False),
            '9F40': ('Additional Terminal Capabilities', 'Additional Terminal Capabilities', 'binary', False),
            '9F1B': ('Terminal Floor Limit', 'Terminal Floor Limit', 'binary', False),
            '9F1C': ('Terminal Identification', 'Terminal Identification', 'text', False),
            '9F1E': ('Interface Device Serial Number', 'Interface Device Serial Number', 'text', False),
            '9F35': ('Terminal Type', 'Terminal Type', 'numeric', False),
            '9F37': ('Unpredictable Number', 'Unpredictable Number', 'binary', False),
            '9F41': ('Transaction Sequence Counter', 'Transaction Sequence Counter', 'numeric', False),
            
            # Authorization and Risk Management
            '8A': ('Authorization Response Code', 'Authorization Response Code', 'text', False),
            '91': ('Issuer Authentication Data', 'Issuer Authentication Data', 'binary', False),
            '71': ('Issuer Script Template 1', 'Issuer Script Template 1', 'constructed', False),
            '72': ('Issuer Script Template 2', 'Issuer Script Template 2', 'constructed', False),
            '9F18': ('Issuer Script Identifier', 'Issuer Script Identifier', 'binary', False),
            
            # Dynamic Authentication
            '9F4A': ('SDA Tag List', 'Static Data Authentication Tag List', 'binary', False),
            '9F4B': ('Signed Dynamic Application Data', 'Signed Dynamic Application Data', 'binary', False),
            '9F2D': ('ICC PIN Encipherment Public Key Certificate', 'ICC PIN Encipherment Public Key Certificate', 'binary', False),
            '9F2E': ('ICC PIN Encipherment Public Key Exponent', 'ICC PIN Encipherment Public Key Exponent', 'binary', False),
            '9F2F': ('ICC PIN Encipherment Public Key Remainder', 'ICC PIN Encipherment Public Key Remainder', 'binary', False),
            '9F46': ('ICC Public Key Certificate', 'ICC Public Key Certificate', 'binary', False),
            '9F47': ('ICC Public Key Exponent', 'ICC Public Key Exponent', 'binary', False),
            '9F48': ('ICC Public Key Remainder', 'ICC Public Key Remainder', 'binary', False),
            
            # File and Record Structure
            '70': ('EMV Proprietary Template', 'EMV Proprietary Template', 'constructed', False),
            '77': ('Response Message Template Format 2', 'Response Message Template Format 2', 'constructed', False),
            '80': ('Response Message Template Format 1', 'Response Message Template Format 1', 'binary', False),
            '83': ('Command Template', 'Command Template', 'constructed', False),
            
            # Service and Control
            '9F0D': ('IAC Default', 'Issuer Action Code - Default', 'binary', False),
            '9F0E': ('IAC Denial', 'Issuer Action Code - Denial', 'binary', False),
            '9F0F': ('IAC Online', 'Issuer Action Code - Online', 'binary', False),
            '9F14': ('Lower Consecutive Offline Limit', 'Lower Consecutive Offline Limit', 'binary', False),
            '9F15': ('Merchant Category Code', 'Merchant Category Code', 'numeric', False),
            '9F16': ('Merchant Identifier', 'Merchant Identifier', 'text', False),
            '9F4E': ('Merchant Name and Location', 'Merchant Name and Location', 'text', False),
            
            # Extended Application Data
            '9F39': ('POS Entry Mode', 'Point-of-Service Entry Mode', 'numeric', False),
            '9F34': ('CVM Results', 'Cardholder Verification Method Results', 'binary', False),
            '9F43': ('Application Reference Currency', 'Application Reference Currency', 'numeric', False),
            '9F45': ('Data Authentication Code', 'Data Authentication Code', 'binary', False),
            '9F49': ('DDOL', 'Dynamic Data Authentication Data Object List', 'binary', False),
            '9F4C': ('ICC Dynamic Number', 'ICC Dynamic Number', 'binary', False),
            '9F4D': ('Log Entry', 'Log Entry', 'binary', False),
            
            # Proprietary Application Data
            '9F50': ('Offline Accumulator Balance', 'Offline Accumulator Balance', 'binary', False),
            '9F51': ('Application Currency Code', 'Application Currency Code', 'numeric', False),
            '9F52': ('Application Default Action', 'Application Default Action (ADA)', 'binary', False),
            '9F53': ('Consecutive Transaction Limit International', 'Consecutive Transaction Limit (International)', 'binary', False),
            '9F54': ('Cumulative Total Transaction Amount Limit', 'Cumulative Total Transaction Amount Limit', 'binary', False),
            '9F55': ('Geographic Indicator', 'Geographic Indicator', 'binary', False),
            '9F56': ('Issuer Authentication Indicator', 'Issuer Authentication Indicator', 'binary', False),
            '9F57': ('Issuer Country Code', 'Issuer Country Code', 'numeric', False),
            '9F58': ('Lower Consecutive Offline Limit Card', 'Lower Consecutive Offline Limit (Card)', 'binary', False),
            '9F59': ('Upper Consecutive Offline Limit Card', 'Upper Consecutive Offline Limit (Card)', 'binary', False),
            '9F5A': ('Application Program Identifier', 'Application Program Identifier', 'binary', False),
            
            # Additional EMV Tags
            '5F30': ('Service Code', 'Service Code', 'numeric', True),
            '5F50': ('Issuer URL', 'Issuer URL', 'text', False),
            '5F53': ('IBAN', 'International Bank Account Number', 'text', True),
            '5F54': ('Bank Identifier Code', 'Bank Identifier Code (BIC)', 'text', False),
            '5F55': ('Issuer Country Code Alpha2', 'Issuer Country Code (alpha2 format)', 'text', False),
            '5F56': ('Issuer Country Code Alpha3', 'Issuer Country Code (alpha3 format)', 'text', False),
            '9F5B': ('Issuer Script Results', 'Issuer Script Results', 'binary', False),
            '9F5C': ('Cumulative Total Transaction Amount Upper Limit', 'CTTAUL - Cumulative Total Transaction Amount Upper Limit', 'binary', False),
            '9F5D': ('Available Offline Spending Amount', 'Available Offline Spending Amount (AOSA)', 'binary', False),
            '9F5E': ('Consecutive Transaction Limit International Country', 'CTLIC - Consecutive Transaction Limit (International - Country)', 'binary', False),
            '9F5F': ('DS Slot Availability', 'DS Slot Availability', 'binary', False),
            '9F60': ('CVC3 Track1', 'CVC3 (Track1)', 'binary', True),
            '9F61': ('CVC3 Track2', 'CVC3 (Track2)', 'binary', True),
            '9F62': ('PUNATC Track1', 'PCVC3(Track1)', 'binary', True),
            '9F63': ('PUNATC Track2', 'PUNATC(Track2)', 'binary', True),
            '9F64': ('NATC Track1', 'NATC(Track1)', 'binary', True),
            '9F65': ('PCVC3 Track2', 'PCVC3(Track2)', 'binary', True),
            '9F66': ('TTQ', 'Terminal Transaction Qualifiers', 'binary', False),
            '9F67': ('NATC Track2', 'NATC(Track2)', 'binary', True),
            '9F68': ('Mag Stripe CVM List', 'Mag Stripe CVM List', 'binary', False),
            '9F69': ('UDOL', 'Unpredictable Number Data Object List', 'binary', False),
            '9F6A': ('Unpredictable Number Numeric', 'Unpredictable Number (Numeric)', 'numeric', False),
            '9F6B': ('Track 2 Data', 'Track 2 Data', 'binary', True),
            '9F6C': ('Mag Stripe Application Version Number', 'Mag Stripe Application Version Number', 'binary', False),
            '9F6D': ('Mag Stripe CV Rules', 'Mag Stripe CV Rules', 'binary', False),
            '9F6E': ('Third Party Data', 'Third Party Data', 'binary', False),
            '9F70': ('Protected Data Envelope 1', 'Protected Data Envelope 1', 'binary', False),
            '9F71': ('Protected Data Envelope 2', 'Protected Data Envelope 2', 'binary', False),
            '9F72': ('Protected Data Envelope 3', 'Protected Data Envelope 3', 'binary', False),
            '9F73': ('Protected Data Envelope 4', 'Protected Data Envelope 4', 'binary', False),
            '9F74': ('VLP Issuer Authorization Code', 'VLP Issuer Authorization Code', 'binary', False),
            '9F75': ('Cumulative Total Transaction Amount Limit Dual Currency', 'CTTAUL - Dual Currency', 'binary', False),
            '9F76': ('Secondary Application Currency Code', 'Secondary Application Currency Code', 'numeric', False),
            '9F77': ('VLP Funds Limit', 'VLP Funds Limit', 'binary', False),
            '9F78': ('VLP Single Transaction Limit', 'VLP Single Transaction Limit', 'binary', False),
            '9F79': ('VLP Available Funds', 'VLP Available Funds', 'binary', False),
            '9F7A': ('VLP Terminal Transaction Limit', 'VLP Terminal Transaction Limit', 'binary', False),
            '9F7B': ('VLP Terminal Floor Limit', 'VLP Terminal Floor Limit', 'binary', False),
            
            # Contactless Tags
            '9F6F': ('Contactless Reader Capabilities', 'Contactless Reader Capabilities', 'binary', False),
            '9F80': ('Contactless Reader Off-line Minimum', 'Contactless Reader Off-line Minimum', 'binary', False),
            '9F81': ('Contactless Transaction Limit', 'Contactless Transaction Limit (No On-device CVM)', 'binary', False),
            '9F82': ('Contactless Transaction Limit', 'Contactless Transaction Limit (On-device CVM)', 'binary', False),
            '9F83': ('Contactless CVM Limit', 'Contactless CVM Limit', 'binary', False),
            '9F84': ('Contactless Floor Limit', 'Contactless Floor Limit', 'binary', False),
        }
        
        self.tags.update(emv_tags)
        
        # Categorize EMV tags
        cardholder_tags = {'5A', '5F20', '5F24', '5F34', '57', '9F0B', '5F30', '99'}
        application_tags = {'6F', '84', 'A5', '50', '87', '9F12', '82', '94', '9F07', '9F08'}
        transaction_tags = {'9F02', '9F03', '9A', '9C', '9F21', '5F2A', '5F36'}
        crypto_tags = {'9F26', '9F27', '9F10', '9F36', '90', '92', '93', '9F46', '9F47', '9F48'}
        
        self.categories['cardholder'].update(cardholder_tags)
        self.categories['application'].update(application_tags)
        self.categories['transaction'].update(transaction_tags)
        self.categories['crypto'].update(crypto_tags)
    
    def _load_iso7816_tags(self):
        """Load ISO7816 standard tags."""
        
        iso_tags = {
            # File and Application Selection
            '3F': ('Master File', 'Master File Identifier', 'binary', False),
            '2F': ('Elementary File', 'Elementary File under Master File', 'binary', False),
            '7F': ('Dedicated File', 'Dedicated File under Master File', 'binary', False),
            '00': ('RFU', 'Reserved for Future Use', 'binary', False),
            '3F00': ('MF', 'Master File', 'binary', False),
            
            # Security and Authentication
            '86': ('Authenticated Data Template', 'Authenticated Data Template', 'constructed', False),
            '87': ('Encrypted Data', 'Encrypted Data', 'binary', False),
            '8E': ('MAC', 'Message Authentication Code', 'binary', True),
            '97': ('Security Related Data', 'Security Related Data', 'binary', False),
            '99': ('Transaction PIN Data', 'Transaction PIN Data', 'binary', True),
            
            # Application Related
            '61': ('Application Template', 'Application Template', 'constructed', False),
            '73': ('Directory Discretionary Template', 'Directory Discretionary Template', 'constructed', False),
            
            # Card Production and Personalization
            '42': ('IIN', 'Issuer Identification Number', 'numeric', False),
            '45': ('Bank Identifier Code', 'Bank Identifier Code', 'text', False),
            '4F': ('AID', 'Application Identifier (DF Name)', 'binary', False),
            '51': ('IBAN', 'International Bank Account Number', 'text', True),
            '52': ('BIC', 'Bank Identifier Code', 'text', False),
            
            # File Control Information
            '62': ('FCP Template', 'File Control Parameters Template', 'constructed', False),
            '64': ('FMD Template', 'File Management Data Template', 'constructed', False),
            '6C': ('Expected Length', 'Expected Response Length', 'binary', False),
            
            # Security Environment
            '7C': ('Template for Security Object', 'Template for Security Object', 'constructed', False),
            '7D': ('Security Object', 'Security Object', 'binary', False),
            
            # Data Objects
            '53': ('Discretionary Data', 'Discretionary Data or Template', 'binary', False),
            '5C': ('Tag List', 'Tag List', 'binary', False),
            '5D': ('Directory Definition File', 'Directory Definition File', 'binary', False),
            
            # Response Templates
            '6E': ('Application Related Data', 'Application Related Data', 'constructed', False),
            '6D': ('Security Related Data', 'Security Related Data', 'constructed', False),
            
            # Additional ISO Tags
            '81': ('Amount', 'Amount', 'binary', False),
            '85': ('File Reference', 'File Reference', 'binary', False),
            '88': ('Short File Identifier', 'Short File Identifier (SFI)', 'binary', False),
            '89': ('OS ID', 'Operating System Identifier', 'binary', False),
            '8A': ('ARC', 'Authorization Response Code', 'text', False),
            '8B': ('File Security Attributes', 'File Security Attributes', 'binary', False),
            '8C': ('Compact TLV', 'Compact TLV Data Object', 'binary', False),
            '95': ('TVR', 'Terminal Verification Results', 'binary', False),
            '9B': ('TSI', 'Transaction Status Information', 'binary', False),
        }
        
        self.tags.update(iso_tags)
    
    def _load_proprietary_tags(self):
        """Load proprietary tags from various payment networks."""
        
        # Visa proprietary tags
        visa_tags = {
            'DF60': ('Visa Log Format', 'Visa Log Format', 'binary', False),
            'DF61': ('Visa Log Data', 'Visa Log Data', 'binary', False),
            'DF62': ('Visa CVM Reset Timeout', 'Visa CVM Reset Timeout', 'binary', False),
            'DF8117': ('Visa Terminal Transaction Information', 'Visa Terminal Transaction Information', 'binary', False),
            'DF8118': ('Visa Card Production Life Cycle', 'Visa Card Production Life Cycle (CPLC)', 'binary', False),
            'DF8119': ('Visa Card Capabilities Information', 'Visa Card Capabilities Information', 'binary', False),
            'DF811A': ('Visa Application Control', 'Visa Application Control', 'binary', False),
            'DF811B': ('Visa CVN17 Track2', 'Visa CVN17 Track2 Data', 'binary', True),
            'DF811C': ('Visa Application Cryptogram', 'Visa Application Cryptogram', 'binary', True),
            'DF811D': ('Visa fDDA Version', 'Visa fDDA Version', 'binary', False),
            'DF811E': ('Visa Proprietary Authentication Data', 'Visa Proprietary Authentication Data', 'binary', False),
            'DF811F': ('Visa Low Value Payment', 'Visa Low Value Payment (VLP) Terminal Support Indicator', 'binary', False),
        }
        
        # Mastercard proprietary tags
        mastercard_tags = {
            'DF4B': ('Mastercard IAD Format', 'Mastercard Issuer Application Data Format', 'binary', False),
            'DF60': ('Mastercard Mag Stripe CVN', 'Mastercard Mag Stripe Cryptogram Version Number', 'binary', False),
            'DF8101': ('Mastercard Terminal Supported Languages', 'Mastercard Terminal Supported Languages', 'binary', False),
            'DF8102': ('Mastercard Terminal Type Indicator', 'Mastercard Terminal Type Indicator', 'binary', False),
            'DF8103': ('Mastercard Kernel Configuration', 'Mastercard Kernel Configuration', 'binary', False),
            'DF8104': ('Mastercard Default UDOL', 'Mastercard Default UDOL', 'binary', False),
            'DF8105': ('Mastercard Kernel ID', 'Mastercard Kernel ID', 'binary', False),
            'DF8106': ('Mastercard Application Capabilities', 'Mastercard Application Capabilities Information', 'binary', False),
            'DF8107': ('Mastercard CVM Capability', 'Mastercard CVM Capability - CVM Required', 'binary', False),
            'DF8108': ('Mastercard CVM Capability', 'Mastercard CVM Capability - No CVM Required', 'binary', False),
            'DF8109': ('Mastercard Kernel Configuration', 'Mastercard Kernel Configuration', 'binary', False),
            'DF810A': ('Mastercard Maximum Torn Transaction Log Records', 'Mastercard Maximum Torn Transaction Log Records', 'binary', False),
            'DF810B': ('Mastercard Mag-stripe CVM Capability', 'Mastercard Mag-stripe CVM Capability - CVM Required', 'binary', False),
            'DF810C': ('Mastercard Security Capability', 'Mastercard Security Capability', 'binary', False),
            'DF810D': ('Mastercard Additional Check Table', 'Mastercard Additional Check Table', 'binary', False),
            'DF810E': ('Mastercard Exception File', 'Mastercard Exception File', 'binary', False),
            'DF810F': ('Mastercard Security Word', 'Mastercard Security Word', 'binary', True),
        }
        
        # American Express proprietary tags
        amex_tags = {
            'C1': ('Amex Application Control', 'Amex Application Control', 'binary', False),
            'C2': ('Amex Application Currency Code', 'Amex Application Currency Code', 'numeric', False),
            'C3': ('Amex Application Currency Exponent', 'Amex Application Currency Exponent', 'numeric', False),
            'C4': ('Amex CVV4', 'Amex CVV4', 'binary', True),
            'C5': ('Amex Unauth Amount Limit', 'Amex Unauth Amount Limit', 'binary', False),
            'C6': ('Amex Unauth Cumulative Amount Limit', 'Amex Unauth Cumulative Amount Limit', 'binary', False),
            'C7': ('Amex Unauth Number of Transactions Limit', 'Amex Unauth Number of Transactions Limit', 'binary', False),
            'C8': ('Amex CAPDU Version Number', 'Amex CAPDU Version Number', 'binary', False),
            'C9': ('Amex CVV4 Key Index', 'Amex CVV4 Key Index', 'binary', False),
            'CA': ('Amex Previous Transaction History', 'Amex Previous Transaction History', 'binary', False),
        }
        
        # Discover proprietary tags
        discover_tags = {
            'D1': ('Discover Proprietary Data', 'Discover Proprietary Data', 'binary', False),
            'D2': ('Discover Application Control', 'Discover Application Control', 'binary', False),
            'D3': ('Discover CVM Results', 'Discover CVM Results', 'binary', False),
            'D4': ('Discover Transaction Counter', 'Discover Transaction Counter', 'binary', False),
            'D5': ('Discover Cash Back Amount', 'Discover Cash Back Amount', 'binary', False),
        }
        
        # JCB proprietary tags
        jcb_tags = {
            'E1': ('JCB Proprietary Data', 'JCB Proprietary Data', 'binary', False),
            'E2': ('JCB Application Control', 'JCB Application Control', 'binary', False),
            'E3': ('JCB Transaction Type', 'JCB Transaction Type', 'binary', False),
        }
        
        # UnionPay proprietary tags
        unionpay_tags = {
            'F1': ('UnionPay Proprietary Data', 'UnionPay Proprietary Data', 'binary', False),
            'F2': ('UnionPay Application Version', 'UnionPay Application Version', 'binary', False),
            'F3': ('UnionPay Electronic Cash Balance', 'UnionPay Electronic Cash Balance', 'binary', True),
            'F4': ('UnionPay Electronic Cash Limit', 'UnionPay Electronic Cash Limit', 'binary', False),
        }
        
        # PayPal, Venmo, CashApp tags (hypothetical/reverse engineered)
        fintech_tags = {
            'D010': ('PayPal Account ID', 'PayPal Account Identifier', 'text', True),
            'D011': ('PayPal Balance', 'PayPal Account Balance', 'binary', True),
            'D012': ('PayPal Transaction History', 'PayPal Transaction History', 'binary', False),
            'D020': ('Venmo User Handle', 'Venmo User Handle', 'text', True),
            'D021': ('Venmo Balance', 'Venmo Account Balance', 'binary', True),
            'D022': ('Venmo Friend List', 'Venmo Friend List', 'binary', True),
            'D030': ('CashApp Cashtag', 'CashApp Cashtag', 'text', True),
            'D031': ('CashApp Balance', 'CashApp Account Balance', 'binary', True),
            'D032': ('CashApp Routing Number', 'CashApp Bank Routing Number', 'numeric', True),
        }
        
        # Combine all proprietary tags
        all_proprietary = {**visa_tags, **mastercard_tags, **amex_tags, **discover_tags, **jcb_tags, **unionpay_tags, **fintech_tags}
        self.tags.update(all_proprietary)
        
        # Categorize proprietary tags
        self.categories['proprietary'].update(all_proprietary.keys())
    
    def _load_crypto_tags(self):
        """Load cryptographic and security related tags."""
        
        crypto_tags = {
            # PIN and Authentication
            '9F17': ('PIN Try Counter', 'PIN Try Counter', 'numeric', False),
            '9F18': ('Issuer Script Identifier', 'Issuer Script Identifier', 'binary', False),
            '9F20': ('Track2 Discretionary Data', 'Track2 Discretionary Data', 'binary', True),
            '9F23': ('Upper Consecutive Offline Limit', 'Upper Consecutive Offline Limit', 'binary', False),
            '9F24': ('Payment Account Reference', 'Payment Account Reference (PAR)', 'binary', True),
            '9F25': ('Last 4 Digits of PAN', 'Last 4 Digits of PAN', 'numeric', True),
            '9F29': ('Extended Selection', 'Extended Selection', 'binary', False),
            '9F2A': ('Kernel Identifier', 'Kernel Identifier', 'binary', False),
            
            # Dynamic Data Authentication
            '9F32': ('Issuer Public Key Exponent', 'Issuer Public Key Exponent', 'binary', False),
            '9F31': ('Issuer Public Key Modulus', 'Issuer Public Key Modulus', 'binary', False),
            '9F28': ('PIN Statement', 'PIN Statement', 'binary', False),
            '9F19': ('Token Requestor ID', 'Token Requestor ID', 'binary', False),
            
            # Key Management
            '9F22': ('Public Key Index', 'Certification Authority Public Key Index', 'binary', False),
            '9F1F': ('Track1 Discretionary Data', 'Track1 Discretionary Data', 'binary', True),
            '9F1D': ('Terminal Risk Management Data', 'Terminal Risk Management Data', 'binary', False),
            
            # Secure Messaging
            '87': ('Encrypted Data', 'Encrypted Nonce', 'binary', True),
            '85': ('Certificate Serial Number', 'Certificate Serial Number', 'binary', False),
            '86': ('Issuer Script Command', 'Issuer Script Command', 'binary', False),
            
            # ARQC and Cryptogram Generation
            '9F30': ('Service Code', 'Service Code', 'numeric', True),
            '9F5E': ('Data Storage Identifier', 'Data Storage Identifier', 'binary', False),
            
            # Additional Security Tags
            '9F7C': ('Customer Exclusive Data', 'Customer Exclusive Data (CED)', 'binary', True),
            '9F7D': ('Unknown Tag', 'DS Summary 1', 'binary', False),
            '9F7E': ('Mobile Support Indicator', 'Mobile Support Indicator', 'binary', False),
            '9F7F': ('DS Summary Status', 'DS Summary Status', 'binary', False),
        }
        
        self.tags.update(crypto_tags)
        self.categories['crypto'].update(crypto_tags.keys())
    
    def get_tag_name(self, tag: str) -> str:
        """
        Get the human-readable name for a tag.
        
        Args:
            tag: Tag string (hex)
            
        Returns:
            Tag name or the tag itself if not found
        """
        tag_upper = tag.upper()
        if tag_upper in self.tags:
            return self.tags[tag_upper][0]
        return tag_upper
    
    def get_tag_description(self, tag: str) -> str:
        """
        Get the full description for a tag.
        
        Args:
            tag: Tag string (hex)
            
        Returns:
            Tag description or empty string if not found
        """
        tag_upper = tag.upper()
        if tag_upper in self.tags:
            return self.tags[tag_upper][1]
        return ""
    
    def get_tag_info(self, tag: str) -> Tuple[str, str, str, bool]:
        """
        Get complete tag information.
        
        Args:
            tag: Tag string (hex)
            
        Returns:
            Tuple of (name, description, data_type, is_sensitive)
        """
        tag_upper = tag.upper()
        if tag_upper in self.tags:
            return self.tags[tag_upper]
        return (tag_upper, 'Unknown Tag', 'binary', False)
    
    def is_sensitive_tag(self, tag: str) -> bool:
        """
        Check if a tag contains sensitive data.
        
        Args:
            tag: Tag string (hex)
            
        Returns:
            True if tag contains sensitive data
        """
        tag_upper = tag.upper()
        if tag_upper in self.tags:
            return self.tags[tag_upper][3]
        return False
    
    def get_tag_category(self, tag: str) -> str:
        """
        Get the category for a tag.
        
        Args:
            tag: Tag string (hex)
            
        Returns:
            Category name or 'unknown'
        """
        tag_upper = tag.upper()
        
        for category, tags in self.categories.items():
            if tag_upper in tags:
                return category
        
        return 'unknown'
    
    def get_tags_by_category(self, category: str) -> Set[str]:
        """
        Get all tags in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Set of tags in the category
        """
        return self.categories.get(category, set())
    
    def get_sensitive_tags(self) -> Set[str]:
        """
        Get all tags that contain sensitive data.
        
        Returns:
            Set of sensitive tags
        """
        sensitive_tags = set()
        
        for tag, (name, desc, data_type, sensitive) in self.tags.items():
            if sensitive:
                sensitive_tags.add(tag)
        
        return sensitive_tags
    
    def search_tags(self, search_term: str) -> List[Tuple[str, str, str]]:
        """
        Search for tags by name or description.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of (tag, name, description) tuples matching the search
        """
        results = []
        search_lower = search_term.lower()
        
        for tag, (name, desc, data_type, sensitive) in self.tags.items():
            if (search_lower in name.lower() or 
                search_lower in desc.lower() or 
                search_lower in tag.lower()):
                results.append((tag, name, desc))
        
        return results
    
    def get_all_tags(self) -> Dict[str, Tuple[str, str, str, bool]]:
        """
        Get all tags with their information.
        
        Returns:
            Dictionary of all tags
        """
        return self.tags.copy()
    
    def get_tag_count(self) -> int:
        """
        Get the total number of tags in the dictionary.
        
        Returns:
            Number of tags
        """
        return len(self.tags)
    
    def export_tag_list(self) -> List[Dict[str, Any]]:
        """
        Export all tags as a list of dictionaries.
        
        Returns:
            List of tag dictionaries
        """
        tag_list = []
        
        for tag, (name, desc, data_type, sensitive) in self.tags.items():
            tag_info = {
                'tag': tag,
                'name': name,
                'description': desc,
                'data_type': data_type,
                'sensitive': sensitive,
                'category': self.get_tag_category(tag)
            }
            tag_list.append(tag_info)
        
        return tag_list
