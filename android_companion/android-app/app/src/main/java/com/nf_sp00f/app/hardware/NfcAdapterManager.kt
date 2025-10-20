package com.nf_sp00f.app.hardware

import com.nf_sp00f.app.data.DeviceState

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.nfc.NfcAdapter
import android.nfc.tech.IsoDep
import android.content.pm.PackageManager
import android.nfc.NfcManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID

data class NfcAdapterInfo(
    val id: String,
    val name: String,
    val type: AdapterType,
    val status: AdapterStatus,
    val macAddress: String? = null
)

enum class AdapterType {
    INTERNAL_NFC,
    PN532_BLUETOOTH
}

enum class AdapterStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR,
    NOT_AVAILABLE
}

class NfcAdapterManager(private val context: Context) {
    
    // PN532 Bluetooth configuration
    companion object {
        private const val PN532_DEVICE_NAME = "PN532"
        private const val PN532_MAC_ADDRESS = "00:14:03:05:5C:CB"
        private const val PN532_PIN = "1234"
        private val PN532_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB") // SPP UUID
    }
    
    private val _availableAdapters = MutableStateFlow<List<NfcAdapterInfo>>(emptyList())
    val availableAdapters: StateFlow<List<NfcAdapterInfo>> = _availableAdapters.asStateFlow()
    
    private val _selectedAdapter = MutableStateFlow<NfcAdapterInfo?>(null)
    val selectedAdapter: StateFlow<NfcAdapterInfo?> = _selectedAdapter.asStateFlow()
    
    private val _connectionStatus = MutableStateFlow("")
    val connectionStatus: StateFlow<String> = _connectionStatus.asStateFlow()

    // Expose a generic device state for simple UI bindings (compatibility helper)
    private val _deviceState = MutableStateFlow(DeviceState.NOT_SELECTED)
    val deviceState: StateFlow<DeviceState> = _deviceState.asStateFlow()
    
    // Android internal NFC
    private var nfcAdapter: NfcAdapter? = null
    
    // PN532 Bluetooth
    private var bluetoothAdapter: BluetoothAdapter? = null
    private var pn532UsbAdapter: Pn532UsbAdapter? = null
    private var bluetoothSocket: BluetoothSocket? = null
    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null
    
    init {
        initializeAdapters()
    }
    
    private fun initializeAdapters() {
        val adapters = mutableListOf<NfcAdapterInfo>()
        
        // Initialize internal NFC adapter
        val nfcManager = context.getSystemService(Context.NFC_SERVICE) as? NfcManager
        nfcAdapter = nfcManager?.defaultAdapter
        
        if (nfcAdapter != null) {
            val status = when {
                nfcAdapter?.isEnabled == true -> AdapterStatus.CONNECTED
                nfcAdapter != null -> AdapterStatus.DISCONNECTED
                else -> AdapterStatus.NOT_AVAILABLE
            }
            
            adapters.add(
                NfcAdapterInfo(
                    id = "internal_nfc",
                    name = "Android Internal NFC",
                    type = AdapterType.INTERNAL_NFC,
                    status = status
                )
            )
            // Update friendly device state
            _deviceState.value = if (nfcAdapter?.isEnabled == true) DeviceState.CONNECTED else DeviceState.NOT_SELECTED
        }
        
        // Initialize Bluetooth adapter for PN532
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        if (bluetoothAdapter != null) {
            val pn532Device = findPn532Device()
            val status = if (pn532Device != null) {
                AdapterStatus.DISCONNECTED
            } else {
                AdapterStatus.NOT_AVAILABLE
            }
            
            adapters.add(
                NfcAdapterInfo(
                    id = "pn532_bluetooth",
                    name = "PN532 Bluetooth Adapter",
                    type = AdapterType.PN532_BLUETOOTH,
                    status = status,
                    macAddress = PN532_MAC_ADDRESS
                )
            )
        }
        
        _availableAdapters.value = adapters
        _connectionStatus.value = "Adapters initialized: ${adapters.size} found"
    }
    
    private fun findPn532Device(): BluetoothDevice? {
        return try {
            bluetoothAdapter?.bondedDevices?.find { device ->
                device.name == PN532_DEVICE_NAME || device.address == PN532_MAC_ADDRESS
            }
        } catch (e: SecurityException) {
            null
        }
    }
    
    suspend fun connectToAdapter(adapterId: String): Boolean {
        val adapter = _availableAdapters.value.find { it.id == adapterId } ?: return false
        
        return when (adapter.type) {
            AdapterType.INTERNAL_NFC -> connectInternalNfc()
            AdapterType.PN532_BLUETOOTH -> connectPn532Bluetooth()
        }
    }
    
    private fun connectInternalNfc(): Boolean {
        return try {
            if (nfcAdapter?.isEnabled == true) {
                _selectedAdapter.value = _availableAdapters.value.find { it.type == AdapterType.INTERNAL_NFC }
                updateAdapterStatus("internal_nfc", AdapterStatus.CONNECTED)
                _connectionStatus.value = "Internal NFC adapter connected"
                _deviceState.value = DeviceState.CONNECTED
                true
            } else {
                updateAdapterStatus("internal_nfc", AdapterStatus.ERROR)
                _connectionStatus.value = "Internal NFC adapter not enabled"
                _deviceState.value = DeviceState.ERROR
                false
            }
        } catch (e: Exception) {
            updateAdapterStatus("internal_nfc", AdapterStatus.ERROR)
            _connectionStatus.value = "Internal NFC connection error: ${e.message}"
            _deviceState.value = DeviceState.ERROR
            false
        }
    }
    
    private suspend fun connectPn532Bluetooth(): Boolean {
        return try {
            updateAdapterStatus("pn532_bluetooth", AdapterStatus.CONNECTING)
            _connectionStatus.value = "Connecting to PN532 via Bluetooth..."
            
            val pn532Device = findPn532Device()
            if (pn532Device == null) {
                // Try to find by MAC address directly
                val deviceByMac = bluetoothAdapter?.getRemoteDevice(PN532_MAC_ADDRESS)
                if (deviceByMac == null) {
                    updateAdapterStatus("pn532_bluetooth", AdapterStatus.ERROR)
                    _connectionStatus.value = "PN532 device not found (MAC: $PN532_MAC_ADDRESS)"
                    return false
                }
            }
            
            val device = pn532Device ?: bluetoothAdapter?.getRemoteDevice(PN532_MAC_ADDRESS)
            bluetoothSocket = device?.createRfcommSocketToServiceRecord(PN532_UUID)
            
            bluetoothSocket?.connect()
            inputStream = bluetoothSocket?.inputStream
            outputStream = bluetoothSocket?.outputStream
            
            if (inputStream != null && outputStream != null) {
                _selectedAdapter.value = _availableAdapters.value.find { it.type == AdapterType.PN532_BLUETOOTH }
                updateAdapterStatus("pn532_bluetooth", AdapterStatus.CONNECTED)
                _connectionStatus.value = "PN532 Bluetooth adapter connected"
                
                // Send initialization command to PN532
                initializePn532()
                true
            } else {
                throw IOException("Failed to establish streams")
            }
        } catch (e: Exception) {
            updateAdapterStatus("pn532_bluetooth", AdapterStatus.ERROR)
            _connectionStatus.value = "PN532 connection error: ${e.message}"
            disconnectPn532()
            _deviceState.value = DeviceState.ERROR
            false
        }
    }
    
    private fun initializePn532() {
        try {
            // Send GetFirmwareVersion command to PN532
            val getFirmwareCmd = byteArrayOf(0x00, 0x00, 0xFF.toByte(), 0x02, 0xFE.toByte(), 0xD4.toByte(), 0x02, 0x2A, 0x00)
            outputStream?.write(getFirmwareCmd)
            outputStream?.flush()
            
            // Read response
            val buffer = ByteArray(32)
            val bytesRead = inputStream?.read(buffer) ?: 0
            
            if (bytesRead > 0) {
                _connectionStatus.value = "PN532 initialized successfully"
            }
        } catch (e: IOException) {
            _connectionStatus.value = "PN532 initialization warning: ${e.message}"
        }
    }
    
    fun disconnectAdapter() {
        _selectedAdapter.value?.let { adapter ->
            when (adapter.type) {
                AdapterType.INTERNAL_NFC -> {
                    updateAdapterStatus("internal_nfc", AdapterStatus.DISCONNECTED)
                    _connectionStatus.value = "Internal NFC adapter disconnected"
                    _deviceState.value = DeviceState.NOT_SELECTED
                }
                AdapterType.PN532_BLUETOOTH -> {
                    disconnectPn532()
                    _deviceState.value = DeviceState.NOT_SELECTED
                }
            }
        }
        _selectedAdapter.value = null
    }

    // Compatibility helper used by legacy UI code
    fun isNfcEnabled(): Boolean {
        return nfcAdapter?.isEnabled == true
    }
    
    private fun disconnectPn532() {
        try {
            bluetoothSocket?.close()
            inputStream?.close()
            outputStream?.close()
        } catch (e: IOException) {
            // Ignore close errors
        } finally {
            bluetoothSocket = null
            inputStream = null
            outputStream = null
            updateAdapterStatus("pn532_bluetooth", AdapterStatus.DISCONNECTED)
            _connectionStatus.value = "PN532 Bluetooth adapter disconnected"
        }
    }
    
    private fun updateAdapterStatus(adapterId: String, status: AdapterStatus) {
        val updatedList = _availableAdapters.value.map { adapter ->
            if (adapter.id == adapterId) {
                adapter.copy(status = status)
            } else {
                adapter
            }
        }
        _availableAdapters.value = updatedList
    }
    
    /**
     * Send an APDU command over the currently-selected adapter. If an
     * IsoDep instance is provided and the selected adapter is the internal
     * Android NFC adapter, the APDU will be sent directly to the IsoDep
     * transport (useful for UI-driven reader-mode flows that provide the
     * Tag/IsoDep). When no IsoDep is provided for internal NFC the method
     * will instruct consumers to use IsoDep directly.
     */
    fun sendApduCommand(command: ByteArray, isoDep: IsoDep? = null): ByteArray? {
        return when (_selectedAdapter.value?.type) {
            AdapterType.INTERNAL_NFC -> {
                if (isoDep != null) {
                    sendApduToIsoDep(isoDep, command)
                } else {
                    // Backwards-compatible behavior: caller should supply IsoDep
                    _connectionStatus.value = "Use IsoDep for internal NFC APDU commands (provide IsoDep)"
                    null
                }
            }
            AdapterType.PN532_BLUETOOTH -> sendPn532ApduCommand(command)
            null -> {
                _connectionStatus.value = "No adapter connected"
                null
            }
        }
    }

    /**
     * Send an APDU directly to an IsoDep instance. This helper owns the
     * connect/transceive lifecycle and will attempt to close the connection
     * if it opened it.
     */
    fun sendApduToIsoDep(isoDep: IsoDep, command: ByteArray): ByteArray? {
        return try {
            val wasConnected = isoDep.isConnected
            if (!wasConnected) isoDep.connect()
            val resp = isoDep.transceive(command)
            if (!wasConnected) {
                try { isoDep.close() } catch (_: Exception) {}
            }
            resp
        } catch (e: Exception) {
            _connectionStatus.value = "IsoDep APDU error: ${e.message}"
            try { if (isoDep.isConnected) isoDep.close() } catch (_: Exception) {}
            null
        }
    }
    
    private fun sendPn532ApduCommand(command: ByteArray): ByteArray? {
        return try {
            if (outputStream == null || inputStream == null) {
                _connectionStatus.value = "PN532 not connected"
                return null
            }
            
            // Wrap APDU in PN532 InDataExchange frame
            val pn532Command = buildPn532DataExchangeFrame(command)
            outputStream?.write(pn532Command)
            outputStream?.flush()
            
            // Read response
            val buffer = ByteArray(512)
            val bytesRead = inputStream?.read(buffer) ?: 0
            
            if (bytesRead > 0) {
                // Extract APDU response from PN532 frame
                extractApduFromPn532Response(buffer, bytesRead)
            } else {
                null
            }
        } catch (e: IOException) {
            _connectionStatus.value = "PN532 APDU error: ${e.message}"
            null
        }
    }
    
    private fun buildPn532DataExchangeFrame(apdu: ByteArray): ByteArray {
        // PN532 InDataExchange frame format
        val dataLength = apdu.size + 2
        val frame = ByteArray(6 + apdu.size + 1)
        
        frame[0] = 0x00 // Preamble
        frame[1] = 0x00 // Start Code
        frame[2] = 0xFF.toByte() // Start Code
        frame[3] = dataLength.toByte() // Length
        frame[4] = (0x100 - dataLength).toByte() // Length Checksum
        frame[5] = 0xD4.toByte() // TFI (Host to PN532)
        frame[6] = 0x40 // InDataExchange command
        frame[7] = 0x01 // Target number
        
        // Copy APDU
        apdu.copyInto(frame, 8)
        
        // Calculate DCS (Data Checksum)
        var dcs = 0xD4 + 0x40 + 0x01
        for (b in apdu) {
            dcs += b.toInt() and 0xFF
        }
        frame[frame.size - 1] = (0x100 - (dcs and 0xFF)).toByte()
        
        return frame
    }
    
    private fun extractApduFromPn532Response(buffer: ByteArray, length: Int): ByteArray? {
        // PN532 response format: [Preamble][Start][LEN][LCS][TFI][Status][Data...][DCS]
        if (length < 8) return null
        
        // Find start of response data (after status byte)
        val dataStart = 7 // Skip preamble, start codes, length, checksum, TFI, status
        val dataEnd = length - 1 // Before DCS
        
        if (dataStart >= dataEnd) return null
        
        return buffer.copyOfRange(dataStart, dataEnd)
    }
    
    fun refreshAdapters() {
        initializeAdapters()
    }
    
    fun cleanup() {
        disconnectAdapter()
    }
}
