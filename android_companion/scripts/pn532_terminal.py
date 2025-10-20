#!/usr/bin/env python3
"""
PN532 Terminal Emulator for nfsp00f3r-V5 EMV Testing
Provides rapid EMV workflow testing with Android HCE integration.
"""

import serial
import bluetooth
import time
import sys
from typing import Optional, List, Dict, Tuple
import json
from datetime import datetime
from pathlib import Path

class PN532Terminal:
    """PN532 Bluetooth/USB terminal for EMV workflow testing."""

    def __init__(self, connection_type: str = "bluetooth", device_path: str = "/dev/rfcomm0"):
        self.connection_type = connection_type
        self.device_path = device_path
        self.connection = None
        self.apdu_log = []

    def connect(self) -> bool:
        """Establish connection to PN532 device."""
        try:
            if self.connection_type == "bluetooth":
                return self.connect_bluetooth()
            elif self.connection_type == "usb":
                return self.connect_usb()
            else:
                print(f"❌ Unsupported connection type: {self.connection_type}")
                return False
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False

    def connect_bluetooth(self) -> bool:
        """Connect via Bluetooth HC-06/HC-05."""
        try:
            self.connection = serial.Serial(self.device_path, 9600, timeout=2)
            time.sleep(1)  # Allow connection to stabilize

            # Test connection with PN532 version command
            if self.send_pn532_command("02"):  # GetFirmwareVersion
                print("✅ Bluetooth connection established")
                return True
            else:
                print("❌ PN532 not responding via Bluetooth")
                return False

        except Exception as e:
            print(f"❌ Bluetooth connection failed: {str(e)}")
            return False

    def connect_usb(self) -> bool:
        """Connect via USB serial."""
        try:
            self.connection = serial.Serial(self.device_path, 115200, timeout=2)
            time.sleep(1)

            if self.send_pn532_command("02"):
                print("✅ USB connection established")
                return True
            else:
                print("❌ PN532 not responding via USB")
                return False

        except Exception as e:
            print(f"❌ USB connection failed: {str(e)}")
            return False

    def send_pn532_command(self, command_hex: str) -> Optional[str]:
        """Send PN532 command and return response."""
        if not self.connection:
            return None

        try:
            # Convert hex string to bytes
            command_bytes = bytes.fromhex(command_hex.replace(" ", ""))

            # Send command
            self.connection.write(command_bytes)
            time.sleep(0.1)

            # Read response
            response = self.connection.read(256)
            if response:
                return response.hex().upper()
            return None

        except Exception as e:
            print(f"❌ Command failed: {str(e)}")
            return None

    def send_apdu(self, apdu_hex: str) -> Tuple[Optional[str], float]:
        """Send APDU command and measure execution time."""
        start_time = time.time()

        # Wrap APDU in PN532 InDataExchange command (0x40)
        pn532_command = "40" + "01" + apdu_hex  # 0x40 = InDataExchange, 0x01 = target

        response = self.send_pn532_command(pn532_command)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        if response and len(response) > 4:
            # Extract APDU response (skip PN532 wrapper)
            apdu_response = response[6:]  # Skip status bytes

            # Log the exchange
            self.apdu_log.append({
                "timestamp": datetime.now().isoformat(),
                "command": apdu_hex,
                "response": apdu_response,
                "execution_time_ms": round(execution_time, 2)
            })

            return apdu_response, execution_time

        return None, execution_time

    def run_emv_workflow(self, workflow_type: str = "visa_msd") -> Dict:
        """Execute complete EMV workflow."""
        print(f"🔄 Running EMV workflow: {workflow_type}")
        start_time = time.time()

        workflow_results = {
            "workflow_type": workflow_type,
            "start_time": datetime.now().isoformat(),
            "commands": [],
            "success": False,
            "total_time_ms": 0
        }

        if workflow_type == "visa_msd":
            commands = [
                ("SELECT PPSE", "00A404000E325041592E5359532E444446303100"),
                ("SELECT VISA", "00A4040007A000000003101000"),
                ("GET PROCESSING OPTIONS", "80A80000238321000000000000000000000000000000000000000840000000000000000000000000"),
                ("READ RECORD SFI 1", "00B2010C00"),
                ("READ RECORD SFI 2", "00B2021400")
            ]
        else:
            print(f"❌ Unknown workflow type: {workflow_type}")
            return workflow_results

        # Execute each command in sequence
        for cmd_name, apdu in commands:
            print(f"📤 {cmd_name}")
            response, exec_time = self.send_apdu(apdu)

            command_result = {
                "name": cmd_name,
                "apdu": apdu,
                "response": response,
                "execution_time_ms": exec_time,
                "success": response is not None and response.endswith("9000")
            }

            workflow_results["commands"].append(command_result)

            if response:
                print(f"📥 Response: {response}")
                if not response.endswith("9000"):
                    print(f"⚠️  Status: {response[-4:]} (not success)")
            else:
                print("❌ No response received")
                break

            time.sleep(0.1)  # Brief delay between commands

        # Calculate total execution time
        total_time = (time.time() - start_time) * 1000
        workflow_results["total_time_ms"] = round(total_time, 2)
        workflow_results["success"] = all(cmd["success"] for cmd in workflow_results["commands"])

        print(f"✅ Workflow completed in {total_time:.2f}ms")
        return workflow_results

    def test_android_hce(self) -> Dict:
        """Test Android HCE emulation detection and interaction."""
        print("🤖 Testing Android HCE integration...")

        # Enable reader mode (PN532 specific)
        reader_config = "32050114A106"  # Configure for Type A cards
        config_response = self.send_pn532_command(reader_config)

        if not config_response:
            return {"success": False, "error": "Failed to configure reader mode"}

        # Attempt card detection
        detect_command = "4A0100"  # InListPassiveTarget
        detect_response = self.send_pn532_command(detect_command)

        if detect_response and "01" in detect_response[:4]:  # Card detected
            print("📱 Android HCE device detected!")

            # Run EMV workflow against Android HCE
            hce_results = self.run_emv_workflow("visa_msd")
            hce_results["hce_detected"] = True
            return hce_results
        else:
            print("📱 No HCE device detected")
            return {"success": False, "hce_detected": False}

    def save_log(self, filename: str):
        """Save APDU log to file."""
        log_path = Path(filename)

        log_data = {
            "session_info": {
                "timestamp": datetime.now().isoformat(),
                "connection_type": self.connection_type,
                "device_path": self.device_path,
                "total_commands": len(self.apdu_log)
            },
            "apdu_exchanges": self.apdu_log
        }

        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"📄 Log saved to {log_path}")

    def disconnect(self):
        """Close connection."""
        if self.connection:
            self.connection.close()
            print("🔌 Connection closed")

def main():
    """Main entry point for PN532 terminal testing."""
    print("🏴‍☠️ PN532 Terminal Emulator - nfsp00f3r-V5 EMV Testing")
    print("="*60)

    # Parse command line arguments
    connection_type = "bluetooth"
    device_path = "/dev/rfcomm0"

    if len(sys.argv) > 1:
        connection_type = sys.argv[1]
    if len(sys.argv) > 2:
        device_path = sys.argv[2]

    terminal = PN532Terminal(connection_type, device_path)

    try:
        # Connect to PN532
        if not terminal.connect():
            print("❌ Failed to establish connection")
            sys.exit(1)

        # Run EMV workflow test
        print("\n🔄 Running EMV workflow test...")
        workflow_results = terminal.run_emv_workflow("visa_msd")

        # Test Android HCE integration
        print("\n🤖 Testing Android HCE integration...")
        hce_results = terminal.test_android_hce()

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        terminal.save_log(f"pn532_test_{timestamp}.json")

        # Print summary
        print("\n📊 Test Summary:")
        print(f"  EMV Workflow Success: {workflow_results['success']}")
        if 'hce_detected' in hce_results:
            print(f"  HCE Detection: {hce_results['hce_detected']}")
        print(f"  Total Execution Time: {workflow_results.get('total_time_ms', 0):.2f}ms")

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)
    finally:
        terminal.disconnect()

if __name__ == "__main__":
    main()
