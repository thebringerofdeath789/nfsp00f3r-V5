package com.nf_sp00f.app.hardware

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbDeviceConnection
import android.hardware.usb.UsbEndpoint
import android.hardware.usb.UsbInterface
import android.hardware.usb.UsbManager
import android.hardware.usb.UsbConstants
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class Pn532UsbAdapter(private val context: Context) {
    private val usbManager = context.getSystemService(Context.USB_SERVICE) as UsbManager
    private var usbDevice: UsbDevice? = null
    private var usbConnection: UsbDeviceConnection? = null
    private var usbInterface: UsbInterface? = null
    private var inEndpoint: UsbEndpoint? = null
    private var outEndpoint: UsbEndpoint? = null
    
    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected
    
    private val _deviceInfo = MutableStateFlow("PN532 USB - Disconnected")
    val deviceInfo: StateFlow<String> = _deviceInfo
    
    private val _apduLog = MutableStateFlow<List<String>>(emptyList())
    val apduLog: StateFlow<List<String>> = _apduLog
    
    companion object {
        private const val ACTION_USB_PERMISSION = "com.nf_sp00f.app.USB_PERMISSION"
        private const val PN532_VENDOR_ID = 0x072F
        private const val PN532_PRODUCT_ID = 0x2200
    }
    
    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                ACTION_USB_PERMISSION -> {
                    synchronized(this) {
                        val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
                        if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                            device?.apply {
                                connectToDevice(this)
                            }
                        }
                    }
                }
                UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                    val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)
                    if (device == usbDevice) {
                        disconnect()
                    }
                }
            }
        }
    }
    
    init {
        val filter = IntentFilter().apply {
            addAction(ACTION_USB_PERMISSION)
            addAction(UsbManager.ACTION_USB_DEVICE_DETACHED)
        }
        context.registerReceiver(usbReceiver, filter)
    }
    
    fun scanForDevices(): List<String> {
        val devices = mutableListOf<String>()
        for (device in usbManager.deviceList.values) {
            if (device.vendorId == PN532_VENDOR_ID || device.productName?.contains("PN532", true) == true) {
                devices.add("PN532 USB (${device.productName ?: "Unknown"})")
            }
        }
        return devices
    }
    
    fun connect(): Boolean {
        val device = findPn532Device()
        return if (device != null) {
            requestPermissionAndConnect(device)
            true
        } else {
            addToLog("No PN532 USB device found")
            false
        }
    }
    
    private fun findPn532Device(): UsbDevice? {
        for (device in usbManager.deviceList.values) {
            if (device.vendorId == PN532_VENDOR_ID || device.productName?.contains("PN532", true) == true) {
                return device
            }
        }
        return null
    }
    
    private fun requestPermissionAndConnect(device: UsbDevice) {
        val permissionIntent = PendingIntent.getBroadcast(
            context, 0, Intent(ACTION_USB_PERMISSION), 
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        usbManager.requestPermission(device, permissionIntent)
    }
    
    private fun connectToDevice(device: UsbDevice) {
        usbDevice = device
        usbConnection = usbManager.openDevice(device)
        
        if (usbConnection == null) {
            addToLog("Failed to open USB connection")
            return
        }
        
        val intf = device.getInterface(0)
        usbInterface = intf
        
        if (!usbConnection!!.claimInterface(intf, true)) {
            addToLog("Failed to claim USB interface")
            return
        }
        
        for (i in 0 until intf.endpointCount) {
            val endpoint = intf.getEndpoint(i)
            if (endpoint.type == UsbConstants.USB_ENDPOINT_XFER_BULK) {
                if (endpoint.direction == UsbConstants.USB_DIR_IN) {
                    inEndpoint = endpoint
                } else {
                    outEndpoint = endpoint
                }
            }
        }
        
        if (inEndpoint != null && outEndpoint != null) {
            _isConnected.value = true
            _deviceInfo.value = "PN532 USB - Connected (${device.productName ?: "Unknown"})"
            addToLog("PN532 USB adapter connected successfully")
            initializeDevice()
        } else {
            addToLog("Failed to find USB endpoints")
            disconnect()
        }
    }
    
    private fun initializeDevice() {
        addToLog("Initializing PN532 USB adapter...")
        
        val getFirmwareCmd = byteArrayOf(0x00, 0x00, 0xFF.toByte(), 0x02, 0xFE.toByte(), 0xD4.toByte(), 0x02, 0x2A.toByte(), 0x00)
        sendCommand(getFirmwareCmd, "Get firmware version")
        
        val getGeneralStatusCmd = byteArrayOf(0x00, 0x00, 0xFF.toByte(), 0x02, 0xFE.toByte(), 0xD4.toByte(), 0x04, 0x28.toByte(), 0x00)
        sendCommand(getGeneralStatusCmd, "Get general status")
        
        val samConfigCmd = byteArrayOf(0x00, 0x00, 0xFF.toByte(), 0x04, 0xFC.toByte(), 0xD4.toByte(), 0x14, 0x01, 0x00, 0x16.toByte(), 0x00)
        sendCommand(samConfigCmd, "SAM configuration")
    }
    
    private fun sendCommand(command: ByteArray, description: String) {
        val connection = usbConnection
        val endpoint = outEndpoint
        
        if (connection != null && endpoint != null) {
            val result = connection.bulkTransfer(endpoint, command, command.size, 1000)
            if (result >= 0) {
                addToLog("TX ($description): ${command.joinToString(" ") { "%02X".format(it) }}")
                
                val response = ByteArray(256)
                val inResult = connection.bulkTransfer(inEndpoint, response, response.size, 1000)
                if (inResult > 0) {
                    val actualResponse = response.copyOf(inResult)
                    addToLog("RX ($description): ${actualResponse.joinToString(" ") { "%02X".format(it) }}")
                }
            } else {
                addToLog("Failed to send command: $description")
            }
        }
    }
    
    fun sendApdu(apdu: ByteArray): ByteArray? {
        val connection = usbConnection
        val endpoint = outEndpoint
        
        if (connection != null && endpoint != null && _isConnected.value) {
            val pn532Frame = buildPn532Frame(apdu)
            val result = connection.bulkTransfer(endpoint, pn532Frame, pn532Frame.size, 5000)
            
            if (result >= 0) {
                addToLog("TX APDU: ${apdu.joinToString(" ") { "%02X".format(it) }}")
                
                val response = ByteArray(512)
                val inResult = connection.bulkTransfer(inEndpoint, response, response.size, 5000)
                if (inResult > 0) {
                    val actualResponse = extractApduFromFrame(response, inResult)
                    if (actualResponse != null) {
                        addToLog("RX APDU: ${actualResponse.joinToString(" ") { "%02X".format(it) }}")
                        return actualResponse
                    }
                }
            }
        }
        return null
    }
    
    private fun buildPn532Frame(apdu: ByteArray): ByteArray {
        val dataLength = apdu.size + 1
        val frame = ByteArray(6 + dataLength + 1)
        
        frame[0] = 0x00
        frame[1] = 0x00
        frame[2] = 0xFF.toByte()
        frame[3] = dataLength.toByte()
        frame[4] = (0x100 - dataLength).toByte()
        frame[5] = 0xD4.toByte()
        
        System.arraycopy(apdu, 0, frame, 6, apdu.size)
        
        var checksum = 0xD4
        for (b in apdu) {
            checksum += b.toInt() and 0xFF
        }
        frame[frame.size - 2] = (0x100 - (checksum and 0xFF)).toByte()
        frame[frame.size - 1] = 0x00
        
        return frame
    }
    
    private fun extractApduFromFrame(buffer: ByteArray, length: Int): ByteArray? {
        if (length < 6) return null
        
        var offset = 0
        while (offset < length - 2) {
            if (buffer[offset] == 0x00.toByte() && buffer[offset + 1] == 0x00.toByte() && buffer[offset + 2] == 0xFF.toByte()) {
                val dataLength = buffer[offset + 3].toInt() and 0xFF
                if (offset + 6 + dataLength <= length) {
                    return buffer.copyOfRange(offset + 6, offset + 5 + dataLength)
                }
            }
            offset++
        }
        return null
    }
    
    fun disconnect() {
        usbConnection?.releaseInterface(usbInterface)
        usbConnection?.close()
        usbConnection = null
        usbDevice = null
        usbInterface = null
        inEndpoint = null
        outEndpoint = null
        
        _isConnected.value = false
        _deviceInfo.value = "PN532 USB - Disconnected"
        addToLog("PN532 USB adapter disconnected")
    }
    
    private fun addToLog(message: String) {
        val currentLog = _apduLog.value.toMutableList()
        currentLog.add("[${System.currentTimeMillis()}] $message")
        if (currentLog.size > 100) {
            currentLog.removeAt(0)
        }
        _apduLog.value = currentLog
    }
    
    fun cleanup() {
        disconnect()
        try {
            context.unregisterReceiver(usbReceiver)
        } catch (e: Exception) {
            // Receiver may not be registered
        }
    }
}
