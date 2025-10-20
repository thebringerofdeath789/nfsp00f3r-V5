# nfsp00f3r V5.0 - EMV Terminal & Card Manager with Companion

**Author:** Gregory King & Matthew Braunschweig 
**GitHub:** https://github.com/thebringerofdeath789  

---

## Overview

nfsp00f3r is a full-featured, multi-protocol EMV terminal and smart card application designed for research, education, and private use. This repository contains two primary components:

- A Python desktop application (PyQt5) that implements EMV parsing, card profile management, transaction simulation, developer tooling, and test utilities.
- An Android companion application (located at `android_companion/android-app`) that provides HCE emulation, BLE session synchronization, session import/export, and on-device card profile storage.

The Android companion is integrated to interoperate directly with the desktop application: the desktop `SessionExporter` produces JSON session payloads that the Android app can receive (BLE/GATT or file import). Incoming session payloads are mapped into the Android card profile JSON format and persisted as pretty-printed JSON files under `filesDir/card_profiles/*.json` (NO Room). APDU traces and exported session artifacts are saved under `filesDir/exports/` for audit.

Emulation flows are exposed from the Android `EmulationScreen`, which is the primary entry point for HCE workflows. The project re-uses proven EMV/NFC/crypto components to provide a research-quality toolset for Windows and Linux.

Acceptance criteria (portable verification)
 - Card profiles persist directly on disk: `filesDir/card_profiles/<id>.json` — NO Room database usage.
 - `EmulationScreen` is the default/primary entry for HCE emulation workflows on Android.
 - A debug APK can be produced via `assembleDebug` and is available at `android_companion/android-app/app/build/outputs/apk/debug/app-debug.apk` on successful builds.
 - Desktop ↔ Android interoperability for session export/import, BLE framing and APDU trace parity is covered by host-runnable tests (pytest for desktop, Robolectric/JUnit for Android).
 - Documentation evidence for any verified claim is recorded in `docs/ANDROID_COMPANION_AUDIT.md` with relative artifact paths and an ISO8601 UTC timestamp.

Developer & interoperability details

Session export schema (desktop -> android)
- The desktop helper `SessionExporter.export_session(session)` produces a compact JSON payload used by the Android companion. Key top-level fields:
	- `session_id` (string)
	- `timestamp` (ISO8601 string)
	- `version` (string)
	- `card_data` (object) — contains `pan`, `expiry` / `expiry_date`, `cardholder_name`, plus `fci` / `afl` when available
	- `transaction_data` (object)
	- `apdu_trace` (array) — list of APDU command/response objects (timestamp, command, response, sw1, sw2, description)
	- `security_data` (object) — cryptograms, UNs, issuer data when present

Example (trimmed):

```
{
	"session_id": "b6a9...",
	"timestamp": "2025-10-19T12:00:00",
	"version": "5.0",
	"card_data": { "pan": "401234...", "expiry": "2028-12", "cardholder_name": "J DOE" },
	"apdu_trace": [{ "timestamp": "...", "command": "00A40400...", "response": "9000" }]
}
```

BLE wire format and fragmentation
- Transport uses a small framing layer (`BLEMessage`) that supports fragmentation for long JSON payloads. The on-wire layout is:
	1. 2-byte little-endian payload length (unsigned short, `<H`).
	2. Header: `<BBHH` (message_type (1 byte), sequence_id (1 byte), total_fragments (2 bytes), fragment_index (2 bytes)).
	3. Payload bytes (UTF-8 encoded JSON for `SESSION_DATA` or `APDU_TRACE`).

- Message types are defined in `bluetooth_manager_ble.py` (e.g. `SESSION_DATA`, `APDU_TRACE`, `CARD_DATA`, `ACK`). Refer to that file for exact enum values when implementing interop.

Android on-disk profile format (overview)
- Android persists card profiles as pretty-printed JSON under `filesDir/card_profiles/<profileId>.json`. Each profile is a simple JSON object containing at minimum:
	- `pan`, `expiry_date`, `cardholder_name` (when available),
	- `apdu_log`: an array of short human-readable APDU trace entries for UI display,
	- `fci_data` / `afl_data` when present,
	- `security_data` when available.

 - Active profile is mirrored to `filesDir/active_profile.json` and session/APDU exports are written to `filesDir/exports/` for audit and for desktop retrieval.

 - Session payloads received from the desktop are normalized by `SessionDataMapper` (`android_companion/android-app/.../data/SessionDataMapper.kt`) into the on-disk profile shape used by `CardProfileManager`.

APDU trace export & retrieval
- APDU traces and exported session artifacts live in `filesDir/exports/` on the device. To pull an export from a device or emulator you can use adb (example):

	- adb exec-out run-as <package.name> cat files/exports/<filename>.json > ./exports/<filename>.json

 - Tests include verification that inbound `SESSION_DATA` and `APDU_TRACE` payloads are persisted to `exports/` and to the profile `apdu_log` where appropriate.

Repository hygiene (large files & Gradle wrapper)
- Do NOT commit vendorized Gradle distributions or large zip artifacts into the repository (e.g., `android-app/gradle-dist/` or `android-app/gradle-*.zip`). These files exceed GitHub's file limits and prevent pushes.
- If you encounter an existing repository history containing large blobs, the recommended recovery is to re-clone the cleaned remote or use a dedicated history-rewrite tool (`git filter-repo` or BFG) — both are destructive to local clones and require coordination. When in doubt, re-clone the cleaned remote.

Quick reference — useful commands
- Desktop (PowerShell example):
	- python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
	- pytest tests/ -q
- Android (PowerShell example):
	- cd android_companion\android-app
	- .\gradlew.bat :app:testDebugUnitTest
	- .\gradlew.bat assembleDebug
	- APK path: `app/build/outputs/apk/debug/app-debug.apk`
- Re-sync local clone to a cleaned remote (WARNING: destructive):
	- git fetch origin; git reset --hard origin/master
	- Or simply re-clone: git clone https://github.com/thebringerofdeath789/nfsp00f3r.git


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
- Real-time relay of NFC/APDU traffic to phone for advanced analysis.
- Relay start/stop control from the UI.

### Android Companion (android_companion/android-app)
- HCE emulation using the `EmulationScreen` as the primary entry for emulation workflows.
- Card profiles are persisted directly to device storage as pretty-printed JSON files in `filesDir/card_profiles/` (NO Room database).
- Session import/export and APDU trace capture are supported; APDU traces are saved to `filesDir/exports/` for desktop audit.
- BLE framing and session fragmentation are supported for interoperability with the desktop `SessionExporter`/BLE framing code.
- Unit tests use Robolectric/JUnit so Android JVM tests can run on the host where appropriate.

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

Desktop (Python)
1. Clone the repository:

 - git clone https://github.com/thebringerofdeath789/nfsp00f3r.git
 - cd nfsp00f3r

2. Create and activate a virtual environment and install dependencies (PowerShell example):

 - python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt

3. Run the desktop app:

 - python main.py

Android companion (build from Windows PowerShell)
1. Prerequisites: Java JDK 17+, Android SDK (API 34), and a working Android toolchain. The project uses a Gradle wrapper; prefer using the included wrapper when present.

2. Build and run Android unit tests (Windows PowerShell):

 - cd android_companion\android-app
 - .\gradlew.bat :app:testDebugUnitTest --tests "*CardProfileManagerTest*"

3. Assemble a debug APK (PowerShell):

 - .\gradlew.bat assembleDebug

4. Debug APK path (after a successful assemble):

 - android_companion/android-app/app/build/outputs/apk/debug/app-debug.apk

If the Gradle wrapper is missing on your machine, you can generate a wrapper locally (or use a full re-clone of the repository that contains the wrapper). CI jobs in this repo expect the wrapper to be available.

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

## Code structure (high level)

- `main.py` — Desktop application entry point and application lifecycle.
- `ui_mainwindow.py` — PyQt5 main window and widget wiring for the desktop UI.
- `emv_card.py` — EMV parsing, application selection, and TLV extraction helpers.
- `tlv.py` — TLV parsing utilities used throughout the parser.
- `card_manager.py` — Desktop card profile list, import/export helpers, and local persistence.
- `readers.py`, `proxmark_bt.py`, `proxmark_usb.py` — Reader and device integration helpers (PC/SC, PN532, Proxmark interfaces).
- `bluetooth_manager.py`, `bluetooth_manager_ble.py` — Bluetooth companion transport and BLE framing logic.
- `crypto.py` — EMV/cryptographic utilities used for key derivation and cryptogram handling.
- `transaction.py` — Transaction flow simulation and helpers.
- `attack_manager.py`, `attack_modules.py`, `attack_panel.py` — Attack/replay orchestration and UI panels used for testing research flows.
- `hardware_emulation.py` — Hardware-level emulation helpers used by some features.
- `tests/` — Pytest-based desktop tests and fixtures; the Android app contains Robolectric/JUnit tests under `android_companion/android-app`.
- `android_companion/` — Android companion app port and related documentation; see `android_companion/android-app` for source, tests, and Gradle build files.
- `docs/` — Canonical design, audit, and evidence files (update `docs/ANDROID_COMPANION_AUDIT.md` when making Android changes).

---

## Tests & CI

- Desktop tests: run `pytest tests/ -q` from the repository root after installing `tests/requirements-test.txt` in your virtual environment.
- Android JVM tests: use the Gradle wrapper to run Robolectric unit tests in `android_companion/android-app` (example above). The CI workflow also runs these tests and assembles debug artifacts.

## License & Usage

This software is private and for educational/research purposes only. Distribution or commercial use without written permission is prohibited.

Use responsibly and only on cards and devices you own or have explicit authorization to test.

---

## Contributing

Contributions and suggestions are welcome via GitHub issues and pull requests. When changing Android companion behavior (storage format, API keys, BLE framing, or card profile JSON keys), update `docs/ANDROID_COMPANION_AUDIT.md` and the corresponding tests under `android_companion/android-app` so desktop/Android interop remains verifiable.

---

## Contact


Email: github username @ gmail  
GitHub: https://github.com/thebringerofdeath789
IRC: irc.rizon.net #nf-sp00f3r
---


