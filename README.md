
---

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
