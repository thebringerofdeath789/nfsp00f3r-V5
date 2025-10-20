package com.nf_sp00f.app.emulation

import android.nfc.cardemulation.HostApduService
import android.os.Bundle
import com.nf_sp00f.app.data.CardProfileManager
import com.nf_sp00f.app.data.HceEmulator
import com.nf_sp00f.app.ble.BleServiceRegistry
import com.nf_sp00f.app.data.EmvTlvParser

class EnhancedHceService : HostApduService() {

    override fun processCommandApdu(commandApdu: ByteArray?, extras: Bundle?): ByteArray {
        // Delegate to pure, testable emulation engine which uses the on-disk profile
        val profile = CardProfileManager.getActiveProfile(this)
        return try {
            val response = HceEmulator.handleApdu(profile, commandApdu)

            // Send APDU_TRACE to any registered BLE central so desktop can log APDUs
            try {
                if (commandApdu != null && response != null && BleServiceRegistry.hasManager()) {
                    val cmdHex = EmvTlvParser.toHex(commandApdu)
                    val respHex = EmvTlvParser.toHex(response)
                    val sw1 = if (response.size >= 2) String.format("%02X", response[response.size - 2]) else ""
                    val sw2 = if (response.size >= 1) String.format("%02X", response[response.size - 1]) else ""
                    BleServiceRegistry.sendApduTrace(cmdHex, respHex, sw1, sw2, null)
                }
            } catch (_: Exception) {}

            // Also append this exchange to the active profile's APDU log (keep a bounded log)
            try {
                val active = CardProfileManager.getActiveProfile(this)
                if (active != null) {
                    val apduLog = active.optJSONArray("apdu_log") ?: org.json.JSONArray()
                    val cmdHex = if (commandApdu != null) EmvTlvParser.toHex(commandApdu) else ""
                    val respHex = if (response != null) EmvTlvParser.toHex(response) else ""
                    val sw = if (response != null && response.size >= 2) String.format("%04X", ((response[response.size - 2].toInt() and 0xFF) shl 8) or (response[response.size - 1].toInt() and 0xFF)) else ""
                    val entry = "APDU: CMD=${cmdHex} RESP=${respHex} SW=${sw}"
                    apduLog.put(entry)

                    // Trim log to last 500 entries
                    val maxEntries = 500
                    if (apduLog.length() > maxEntries) {
                        val newArr = org.json.JSONArray()
                        val start = apduLog.length() - maxEntries
                        for (i in start until apduLog.length()) newArr.put(apduLog.get(i))
                        active.put("apdu_log", newArr)
                    } else {
                        active.put("apdu_log", apduLog)
                    }

                    // Persist updated profile
                    val profileId = active.optString("card_id", null)
                    CardProfileManager.saveProfile(this, active, if (profileId.isNullOrEmpty()) null else profileId)
                }
            } catch (_: Exception) {}

            response
        } catch (e: Exception) {
            // Ensure we always return a valid status word
            byteArrayOf(0x6F.toByte(), 0x00.toByte())
        }
    }

    override fun onDeactivated(reason: Int) {
        // Handle HCE deactivation if any cleanup is required
    }
}
