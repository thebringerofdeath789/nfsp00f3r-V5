#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: tlv.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Robust recursive TLV parser for EMV and ISO7816 data

Classes:
- TLVParser: Main TLV parsing engine with EMV and ISO7816 support
- TLVTag: Individual TLV tag representation
- TLVParseError: Custom exception for TLV parsing errors

Functions:
- is_constructed(): Check if tag is constructed
- parse_tag(): Parse tag from byte stream
- parse_length(): Parse length from byte stream
- decode_tag_to_string(): Convert tag bytes to string representation

This module provides comprehensive TLV parsing capabilities covering all EMV
and ISO7816 quirks, with support for constructed tags, indefinite length
encoding, and proper handling of all tag classes.

Based on code from:
- danmichaelo/emv (TLV parsing core)
- dimalinux/EMV-Tools (TLV structure handling)
- ISO7816 and EMV specifications
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from tag_dictionary import TagDictionary

class TLVParseError(Exception):
    """Custom exception for TLV parsing errors."""
    pass

class TLVTag:
    """
    Represents a single TLV tag with its components.
    Handles both primitive and constructed tags with proper class identification.
    """
    
    def __init__(self, tag_bytes: bytes, tag_class: int = 0, constructed: bool = False, tag_number: int = 0):
        """
        Initialize TLV tag.
        
        Args:
            tag_bytes: Raw tag bytes
            tag_class: Tag class (0=universal, 1=application, 2=context, 3=private)
            constructed: True if tag is constructed
            tag_number: Tag number within class
        """
        self.tag_bytes = tag_bytes
        self.tag_class = tag_class
        self.constructed = constructed
        self.tag_number = tag_number
        self.tag_string = tag_bytes.hex().upper()
    
    def __str__(self):
        return self.tag_string
    
    def __repr__(self):
        return f"TLVTag({self.tag_string}, class={self.tag_class}, constructed={self.constructed})"

class TLVParser:
    """
    Robust recursive TLV parser supporting EMV and ISO7816 standards.
    Handles all tag classes, constructed tags, indefinite length encoding,
    and provides human-readable tag descriptions.
    """
    
    def __init__(self):
        """Initialize TLV parser with tag dictionary."""
        self.logger = logging.getLogger(__name__)
        self.tag_dict = TagDictionary()
        self.parsed_data = {}
        self.parse_errors = []
    
    def parse(self, data: bytes) -> Dict[str, Any]:
        """
        Parse TLV data and return structured dictionary.
        
        Args:
            data: Raw TLV data to parse
            
        Returns:
            Dictionary containing parsed TLV structure
        """
        try:
            self.parsed_data = {}
            self.parse_errors = []
            
            if not data:
                return {}
            
            result = self._parse_tlv_data(data, 0, len(data))
            
            if self.parse_errors:
                self.logger.warning(f"TLV parsing completed with {len(self.parse_errors)} errors")
                for error in self.parse_errors:
                    self.logger.warning(f"Parse error: {error}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Critical TLV parsing error: {e}")
            raise TLVParseError(f"Failed to parse TLV data: {e}")
    
    def _parse_tlv_data(self, data: bytes, offset: int, end_offset: int) -> Dict[str, Any]:
        """
        Recursively parse TLV data from byte array.
        
        Args:
            data: Raw data bytes
            offset: Starting offset
            end_offset: Ending offset
            
        Returns:
            Parsed TLV dictionary
        """
        result = {}
        current_offset = offset
        
        while current_offset < end_offset:
            try:
                # Parse tag
                tag_info, tag_end = self._parse_tag(data, current_offset)
                if not tag_info:
                    break
                
                current_offset = tag_end
                
                # Parse length
                length, length_end = self._parse_length(data, current_offset)
                if length is None:
                    break
                
                current_offset = length_end
                
                # Handle indefinite length (length = -1)
                if length == -1:
                    # Find end-of-contents octets (00 00)
                    value_data, value_end = self._parse_indefinite_value(data, current_offset)
                else:
                    # Definite length
                    if current_offset + length > end_offset:
                        # Handle truncated data gracefully
                        available_length = end_offset - current_offset
                        if available_length > 0:
                            # Use available data and warn about truncation
                            self.parse_errors.append(f"Tag {tag_info.tag_string}: expects {length} bytes but only {available_length} available (data may be truncated)")
                            value_data = data[current_offset:end_offset]
                            value_end = end_offset
                        else:
                            self.parse_errors.append(f"Tag {tag_info.tag_string}: no data available for expected length {length}")
                            break
                    else:
                        # Normal case - full data available
                        value_data = data[current_offset:current_offset + length]
                        value_end = current_offset + length
                
                # Process value based on tag type
                if tag_info.constructed:
                    # Recursively parse constructed tag
                    parsed_value = self._parse_tlv_data(value_data, 0, len(value_data))
                else:
                    # Primitive tag - store raw value
                    parsed_value = value_data
                
                # Store in result
                tag_string = tag_info.tag_string
                
                # Handle multiple instances of same tag
                if tag_string in result:
                    if not isinstance(result[tag_string], list):
                        result[tag_string] = [result[tag_string]]
                    result[tag_string].append(parsed_value)
                else:
                    result[tag_string] = parsed_value
                
                current_offset = value_end
                
            except Exception as e:
                self.parse_errors.append(f"Error at offset {current_offset}: {e}")
                # Try to recover by skipping one byte
                current_offset += 1
                if current_offset >= end_offset:
                    break
        
        return result
    
    def _parse_tag(self, data: bytes, offset: int) -> Tuple[Optional[TLVTag], int]:
        """
        Parse tag from data starting at offset.
        
        Args:
            data: Raw data
            offset: Starting offset
            
        Returns:
            Tuple of (TLVTag, next_offset) or (None, offset) if parsing fails
        """
        try:
            if offset >= len(data):
                return None, offset
            
            first_byte = data[offset]
            tag_bytes = bytes([first_byte])
            current_offset = offset + 1
            
            # Extract tag class and constructed bit
            tag_class = (first_byte >> 6) & 0x03
            constructed = bool(first_byte & 0x20)
            tag_number = first_byte & 0x1F
            
            # Check for multi-byte tag (tag number = 31)
            if tag_number == 0x1F:
                # Subsequent bytes contain the tag number
                tag_number = 0
                while current_offset < len(data):
                    byte = data[current_offset]
                    tag_bytes += bytes([byte])
                    current_offset += 1
                    
                    tag_number = (tag_number << 7) | (byte & 0x7F)
                    
                    # Check if this is the last byte (bit 7 = 0)
                    if not (byte & 0x80):
                        break
                    
                    # Prevent infinite loops
                    if len(tag_bytes) > 4:
                        raise TLVParseError("Tag too long")
            
            tag_info = TLVTag(tag_bytes, tag_class, constructed, tag_number)
            return tag_info, current_offset
            
        except Exception as e:
            self.logger.debug(f"Error parsing tag at offset {offset}: {e}")
            return None, offset
    
    def _parse_length(self, data: bytes, offset: int) -> Tuple[Optional[int], int]:
        """
        Parse length field from data.
        
        Args:
            data: Raw data
            offset: Starting offset
            
        Returns:
            Tuple of (length, next_offset) or (None, offset) if parsing fails
            Returns (-1, next_offset) for indefinite length
        """
        try:
            if offset >= len(data):
                return None, offset
            
            first_byte = data[offset]
            
            # Short form (bit 7 = 0)
            if not (first_byte & 0x80):
                return first_byte, offset + 1
            
            # Long form (bit 7 = 1)
            length_bytes_count = first_byte & 0x7F
            
            # Indefinite form (length = 0x80)
            if length_bytes_count == 0:
                return -1, offset + 1
            
            # Definite long form
            if offset + 1 + length_bytes_count > len(data):
                raise TLVParseError("Length field extends beyond data")
            
            if length_bytes_count > 4:
                raise TLVParseError("Length field too long")
            
            length = 0
            for i in range(length_bytes_count):
                length = (length << 8) | data[offset + 1 + i]
            
            return length, offset + 1 + length_bytes_count
            
        except Exception as e:
            self.logger.debug(f"Error parsing length at offset {offset}: {e}")
            return None, offset
    
    def _parse_indefinite_value(self, data: bytes, offset: int) -> Tuple[bytes, int]:
        """
        Parse value with indefinite length encoding.
        
        Args:
            data: Raw data
            offset: Starting offset
            
        Returns:
            Tuple of (value_data, next_offset)
        """
        try:
            current_offset = offset
            
            # Find end-of-contents octets (00 00)
            while current_offset < len(data) - 1:
                if data[current_offset] == 0x00 and data[current_offset + 1] == 0x00:
                    # Found end-of-contents
                    value_data = data[offset:current_offset]
                    return value_data, current_offset + 2
                current_offset += 1
            
            # End-of-contents not found, take all remaining data
            self.parse_errors.append("End-of-contents octets not found for indefinite length")
            value_data = data[offset:]
            return value_data, len(data)
            
        except Exception as e:
            self.logger.debug(f"Error parsing indefinite value at offset {offset}: {e}")
            return data[offset:], len(data)
    
    def get_tag_description(self, tag: str) -> str:
        """
        Get human-readable description for a tag.
        
        Args:
            tag: Tag string (hex)
            
        Returns:
            Tag description or tag string if not found
        """
        return self.tag_dict.get_tag_name(tag)
    
    def get_parsed_data(self) -> Dict[str, Any]:
        """Get the most recently parsed data with descriptions."""
        return self.parsed_data
    
    def format_tlv_tree(self, tlv_data: Dict[str, Any], indent: int = 0) -> str:
        """
        Format TLV data as a readable tree structure.
        
        Args:
            tlv_data: Parsed TLV data
            indent: Indentation level
            
        Returns:
            Formatted string representation
        """
        result = []
        indent_str = "  " * indent
        
        for tag, value in tlv_data.items():
            tag_desc = self.get_tag_description(tag)
            
            if isinstance(value, dict):
                # Constructed tag
                result.append(f"{indent_str}{tag} ({tag_desc}) [CONSTRUCTED]")
                result.append(self.format_tlv_tree(value, indent + 1))
            
            elif isinstance(value, list):
                # Multiple instances
                result.append(f"{indent_str}{tag} ({tag_desc}) [MULTIPLE]")
                for i, item in enumerate(value):
                    result.append(f"{indent_str}  [{i}]")
                    if isinstance(item, dict):
                        result.append(self.format_tlv_tree(item, indent + 2))
                    else:
                        result.append(f"{indent_str}    {self._format_value(item, tag)}")
            
            else:
                # Primitive tag
                formatted_value = self._format_value(value, tag)
                result.append(f"{indent_str}{tag} ({tag_desc}): {formatted_value}")
        
        return "\n".join(result)
    
    def _format_value(self, value: bytes, tag: str) -> str:
        """
        Format a primitive value for display.
        
        Args:
            value: Raw value bytes
            tag: Tag string for context
            
        Returns:
            Formatted value string
        """
        if not value:
            return "[EMPTY]"
        
        # Try to decode as text for certain tags
        text_tags = ['50', '5F20', '5F24', '5F25', '5F28', '5F2D', '9F12', '9F4E']
        
        if tag in text_tags:
            try:
                text = value.decode('utf-8', errors='ignore').strip()
                if text and all(c.isprintable() for c in text):
                    return f'"{text}"'
            except:
                pass
        
        # Default hex representation
        hex_str = value.hex().upper()
        
        # Add ASCII representation if printable
        try:
            ascii_str = value.decode('ascii', errors='ignore')
            if ascii_str and all(c.isprintable() for c in ascii_str):
                return f"{hex_str} ('{ascii_str}')"
        except:
            pass
        
        return hex_str
    
    def extract_specific_tag(self, tlv_data: Dict[str, Any], target_tag: str) -> Optional[Any]:
        """
        Extract a specific tag from TLV data recursively.
        
        Args:
            tlv_data: Parsed TLV data
            target_tag: Tag to search for
            
        Returns:
            Tag value if found, None otherwise
        """
        if target_tag in tlv_data:
            return tlv_data[target_tag]
        
        # Search recursively in constructed tags
        for tag, value in tlv_data.items():
            if isinstance(value, dict):
                result = self.extract_specific_tag(value, target_tag)
                if result is not None:
                    return result
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        result = self.extract_specific_tag(item, target_tag)
                        if result is not None:
                            return result
        
        return None
    
    def validate_tlv_structure(self, data: bytes) -> Tuple[bool, List[str]]:
        """
        Validate TLV data structure and return any issues found.
        
        Args:
            data: Raw TLV data to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Attempt to parse
            parsed = self.parse(data)
            
            # Check for parse errors
            if self.parse_errors:
                issues.extend(self.parse_errors)
            
            # Additional validation checks
            if not parsed:
                issues.append("No valid TLV data found")
            
            # Check for common EMV required tags in appropriate contexts
            self._validate_emv_structure(parsed, issues)
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Critical parsing error: {e}")
            return False, issues
    
    def _validate_emv_structure(self, tlv_data: Dict[str, Any], issues: List[str]):
        """Validate EMV-specific TLV structure requirements (adapted from danmichaelo/emv, dimalinux/EMV-Tools, atzedevs/emv-crypto)."""
        # FCI template (6F) and proprietary (A5)
        if '6F' in tlv_data:
            fci = tlv_data['6F']
            if not isinstance(fci, dict):
                issues.append("FCI template (6F) should be constructed")
            elif 'A5' not in fci:
                issues.append("FCI Proprietary Template (A5) missing from FCI")
        # PDOL (9F38) format: tag-length pairs
        if '9F38' in tlv_data:
            pdol = tlv_data['9F38']
            if isinstance(pdol, bytes) and len(pdol) % 2 != 0:
                issues.append("PDOL length should be even (tag-length pairs)")
        # AFL (94) format: 4 bytes per entry (SFI, first rec, last rec, num recs)
        if '94' in tlv_data:
            afl = tlv_data['94']
            if isinstance(afl, bytes):
                if len(afl) % 4 != 0:
                    issues.append("AFL length should be multiple of 4")
                # Check SFI and record numbers
                for i in range(0, len(afl), 4):
                    sfi = (afl[i] >> 3) & 0x1F
                    first_rec = afl[i+1]
                    last_rec = afl[i+2]
                    if sfi == 0 or first_rec == 0 or last_rec == 0:
                        issues.append(f"AFL entry {i//4}: SFI/record numbers invalid")
        # CDOL1/2 (8C/8D) and UDOL (9F69) format: tag-length pairs
        for tag in ['8C', '8D', '9F69']:
            if tag in tlv_data:
                data = tlv_data[tag]
                if isinstance(data, bytes) and len(data) % 2 != 0:
                    issues.append(f"{tag} length should be even (tag-length pairs)")
        # SFI (88) should be 1 byte
        if '88' in tlv_data:
            sfi = tlv_data['88']
            if not (isinstance(sfi, bytes) and len(sfi) == 1):
                issues.append("SFI (88) should be 1 byte")
        # Track2 equivalent (57) and PAN (5A) should be valid
        if '57' in tlv_data:
            track2 = tlv_data['57']
            if not (isinstance(track2, bytes) and 10 <= len(track2) <= 19):
                issues.append("Track2 (57) length unusual")
        if '5A' in tlv_data:
            pan = tlv_data['5A']
            if not (isinstance(pan, bytes) and 6 <= len(pan) <= 10):
                issues.append("PAN (5A) length unusual")
        # Luhn check for PAN if possible
        try:
            if '5A' in tlv_data:
                pan = tlv_data['5A'].hex().upper().rstrip('F')
                if not self._luhn_check(pan):
                    issues.append("PAN (5A) failed Luhn check")
        except Exception:
            pass
    def _luhn_check(self, pan: str) -> bool:
        if not pan or not pan.isdigit() or len(pan) < 13 or len(pan) > 19:
            return False
        total = 0
        reverse_digits = pan[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n = n // 10 + n % 10
            total += n
        return total % 10 == 0

def is_constructed(tag_bytes: bytes) -> bool:
    """
    Check if a tag is constructed.
    
    Args:
        tag_bytes: Tag bytes
        
    Returns:
        True if constructed, False if primitive
    """
    if not tag_bytes:
        return False
    return bool(tag_bytes[0] & 0x20)

def parse_tag(data: bytes, offset: int) -> Tuple[bytes, int]:
    """
    Parse tag bytes from data.
    
    Args:
        data: Raw data
        offset: Starting offset
        
    Returns:
        Tuple of (tag_bytes, next_offset)
    """
    if offset >= len(data):
        raise TLVParseError("Offset beyond data length")
    
    first_byte = data[offset]
    tag_bytes = bytes([first_byte])
    current_offset = offset + 1
    
    # Check for multi-byte tag
    if (first_byte & 0x1F) == 0x1F:
        while current_offset < len(data):
            byte = data[current_offset]
            tag_bytes += bytes([byte])
            current_offset += 1
            
            if not (byte & 0x80):
                break
                
            if len(tag_bytes) > 4:
                raise TLVParseError("Tag too long")
    
    return tag_bytes, current_offset

def parse_length(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Parse length field from data.
    
    Args:
        data: Raw data
        offset: Starting offset
        
    Returns:
        Tuple of (length, next_offset)
        Returns (-1, next_offset) for indefinite length
    """
    if offset >= len(data):
        raise TLVParseError("Offset beyond data length")
    
    first_byte = data[offset]
    
    # Short form
    if not (first_byte & 0x80):
        return first_byte, offset + 1
    
    # Long form
    length_bytes_count = first_byte & 0x7F
    
    # Indefinite form
    if length_bytes_count == 0:
        return -1, offset + 1
    
    # Definite long form
    if offset + 1 + length_bytes_count > len(data):
        raise TLVParseError("Length field extends beyond data")
    
    length = 0
    for i in range(length_bytes_count):
        length = (length << 8) | data[offset + 1 + i]
    
    return length, offset + 1 + length_bytes_count

def decode_tag_to_string(tag_bytes: bytes) -> str:
    """
    Convert tag bytes to string representation.
    
    Args:
        tag_bytes: Tag bytes
        
    Returns:
        Tag string in uppercase hex
    """
    return tag_bytes.hex().upper()
