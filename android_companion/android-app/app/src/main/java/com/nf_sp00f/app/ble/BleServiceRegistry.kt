package com.nf_sp00f.app.ble

import org.json.JSONArray
import org.json.JSONObject
import android.util.Log

object BleServiceRegistry {
    private const val TAG = "BleServiceRegistry"
    private var bleManager: BleConnectionManager? = null

    fun register(manager: BleConnectionManager) {
        bleManager = manager
        Log.i(TAG, "BLE manager registered")
    }

    fun unregister(manager: BleConnectionManager) {
        if (bleManager === manager) {
            bleManager = null
            Log.i(TAG, "BLE manager unregistered")
        }
    }

    fun hasManager(): Boolean = bleManager != null

    fun sendApduTrace(commandHex: String, responseHex: String, sw1Hex: String, sw2Hex: String, description: String? = null) {
        try {
            val traceEntry = JSONObject()
            traceEntry.put("timestamp", System.currentTimeMillis())
            traceEntry.put("command", commandHex)
            traceEntry.put("response", responseHex)
            traceEntry.put("sw1", sw1Hex)
            traceEntry.put("sw2", sw2Hex)
            if (description != null) traceEntry.put("description", description)

            val traceArray = JSONArray()
            traceArray.put(traceEntry)

            val payload = JSONObject()
            payload.put("trace", traceArray)
            payload.put("count", 1)
            payload.put("timestamp", System.currentTimeMillis())

            bleManager?.let {
                it.sendMessage(BLEMessageType.APDU_TRACE, payload.toString().toByteArray(Charsets.UTF_8))
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to send APDU trace via BLE: ${e.message}")
        }
    }
}
