package com.nf_sp00f.app.data

data class VirtualCard(
    val cardholderName: String,
    val pan: String,
    val expiry: String,
    val apduCount: Int,
    val cardType: String,
    val profileId: String? = null
)

data class DatabaseCard(
    val cardholderName: String,
    val pan: String,
    val expiry: String,
    val apduCount: Int,
    val cardType: String,
    val category: String,
    val isEncrypted: Boolean,
    val lastUsed: String,
    val profileId: String? = null
)

data class AnalysisResult(
    val title: String,
    val cardNumber: String,
    val status: String,
    val score: Int,
    val timestamp: String
)

data class AnalysisTool(
    val title: String,
    val description: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val enabled: Boolean = true
)

data class ApduLogEntry(
    val timestamp: String,
    val direction: String, // "→" or "←"
    val command: String,
    val data: String,
    val statusWord: String = "",
    val parsed: String = ""
)

enum class DeviceState {
    NOT_SELECTED,
    CONNECTING,
    CONNECTED,
    ERROR
}

enum class NfcDevice(val displayName: String) {
    NONE("No Device Selected"),
    ANDROID_NFC("Android Internal NFC"),
    PN532_BLUETOOTH("PN532 Bluetooth Adapter"),
    PN532_USB("PN532 USB Adapter"),
}

data class NfcDeviceInfo(
    val device: NfcDevice,
    val displayName: String,
    val connectionStatus: DeviceState,
    val details: String = "",
    val macAddress: String? = null
)
