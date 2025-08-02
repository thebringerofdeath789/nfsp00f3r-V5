# nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion

**Author:** Gregory King  
**Author Homepage:** https://r00t3d.net  
**GitHub:** https://github.com/thebringerofdeath789  

---

## Overview

nfsp00f3r is a full-featured, multi-protocol EMV terminal and smart card companion application designed for research, education, and private use. It supports comprehensive EMV/NFC smart card parsing, cryptography, magstripe emulation, Bluetooth phone synchronization, relay/replay attacks, PIN management, multi-card handling, and much more.

The project ports and integrates core logic from best-in-class open-source EMV, NFC, and cryptography libraries to deliver a robust desktop solution for Windows and Linux.

---

## Features

### Card Reading & Parsing
- Full support for EMV smart cards via PC/SC and PN532 NFC readers.
- Automatic multi-application parsing from PPSE (Payment System Environment) and AIDs.
- GPO/PDOL/AFL flow handling for accurate transaction data extraction.
- TLV tree parsing with support for nested structures.
- Robust PAN extraction from EMV tags and magstripe equivalent data.
- Cardholder data extraction: name, expiry, CVV, ZIP/postal code.
- Transaction history parsing and display.
- EMV cryptographic key extraction.

### Magstripe / MSD Emulation
- Extracts magnetic stripe tracks from card TLVs.
- Parses and normalizes track 1 and track 2 data.
- Computes LRC checksums for track validation.
- Exports tracks in JSON, binary, and TLV formats.
- Replay simulation of ARQC/ARPC cryptograms using EMV crypto or fallback MAC.

### Transaction & PIN Management
- Runs full transaction flows using embedded EMV crypto logic.
- Offline PIN verification and PIN retry counter management.

### Bluetooth Phone Companion
- Syncs card profiles to/from Android companion app over BLE.
- Remote relay attacks via Bluetooth relay functionality.

### User Interface
- PyQt5-based GUI with:
  - Card selector and detailed card info view.
  - Expandable TLV tree view.
  - APDU command/response log.
  - Control buttons for all main operations.
  - Debug window for live log output.
  - Dark/light mode toggle.
  - Comprehensive menus for quick access.

### Advanced
- Support for replay attacks and relaying of card transactions.
- Transaction cryptogram replay and analysis.
- Multi-card management and profile import/export.
- Easily extendable modular architecture.

---

## Installation

### Requirements

- Python 3.9+
- PyQt5
- pyscard (for PC/SC reader support)
- Required dependencies from `requirements.txt`

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/thebringerofdeath789/nfsp00f3r.git
   cd nfsp00f3r
