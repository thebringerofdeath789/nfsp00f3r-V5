# nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion

**Author:** Gregory King  
**Project Homepage:** https://r00t3d.net  
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

### Magstripe & Emulation
- Extracts and decodes magnetic stripe tracks from cards.
- Magstripe track normalization and LRC calculation.
- Emulates magstripe data for MSR readers.
- ARQC/ARPC cryptogram simulation for replay and testing.
- Batch replay support of saved track data.

### Cryptography
- Full EMV cryptography support (ARQC, DDA, SDA, AC, MAC, KDF, issuer scripts).
- Integration with emv-crypto library for cryptogram generation and verification.
- Extraction and display of card crypto keys.

### Bluetooth Phone Companion
- Sync card profiles and transaction data to/from a Bluetooth-enabled phone.
- Real-time relay of NFC/APDU traffic to phone for advanced analysis or MITM.
- Relay start/stop control from UI.

### User Interface
- PyQt5 desktop UI with card list, detail view, TLV tree, and APDU log.
- Support for multi-card management and quick switching.
- Dark/light theme toggle.
- Debug window with color-coded APDU logging.
- Import/export card profiles in JSON format.
- Transaction simulation and PIN management.

### Additional Features
- Transaction replay and relay.
- Randomize PAN feature for testing.
- Offline PIN verification support.
- Multi-threaded card reader monitoring for PCSC and PN532.
- Robust error handling and logging.
- Support for multiple AIDs and complex EMV app structures.

---

## Installation

### Requirements
- Python 3.9 or higher
- PyQt5
- pyscard (for PCSC reader support)
- Additional dependencies as listed in `requirements.txt`

### Setup
1. Clone the repository:

git clone https://github.com/thebringerofdeath789/nfsp00f3r.git
cd nfsp00f3r

2. Install dependencies:
pip install -r requirements.txt

## Copy
3. Connect your PCSC or PN532 reader.
4. Run the application:

## Usage

- Use the UI dropdown to select a detected card.
- Click **Read Card** to parse card data.
- View card details, TLV tree, and APDU log on the main window.
- Use **Emulate Magstripe** to simulate magstripe output.
- Use **Replay Magstripe** to simulate cryptogram replay.
- Use the **Transaction** button to run transaction flows.
- Sync profiles to/from phone via Bluetooth companion.
- Import and export card profiles using JSON files.
- Toggle dark/light theme from the View menu or UI button.
- Access debug window for detailed logs and troubleshooting.
- Start and stop NFC relay attacks via the UI.

---

## Code Structure

- `main.py`: Application entry point, UI setup, and event handling.
- `ui_mainwindow.py`: PyQt5 UI builder and widget management.
- `emvcard.py`: EMV card parsing, TLV extraction, data handling.
- `magstripe.py`: Magnetic stripe track extraction, decoding, emulation, replay.
- `emv_crypto.py`: Cryptographic operations for EMV cards.
- `cardmanager.py`: Card list, selection, and state management.
- `cardreader_pcsc.py`: PCSC reader thread and card event monitoring.
- `cardreader_pn532.py`: PN532 NFC reader support.
- `cardreader_bluetooth.py`: Bluetooth companion server and message handling.
- `relay.py`: Relay attack management and traffic forwarding.
- `pin_manager.py`: Offline PIN verification and PIN counter management.
- `theme.py`: Dark/light UI theme management.
- `logger.py`: Centralized logging with event signals.
- `export_import.py`: Card profile import/export utilities.
- `settings.py`: User settings persistence.

---

## License & Usage

This software is private and for educational/research purposes only. Distribution or commercial use without permission is prohibited.

Use responsibly and only on cards and devices you own or have explicit authorization to test.

---

## Contributing

Contributions and suggestions are welcome via GitHub issues and pull requests.

---

## Contact

Gregory King  
Email: github username @ gmail  
GitHub: https://github.com/thebringerofdeath789

---

Looking for devs!
