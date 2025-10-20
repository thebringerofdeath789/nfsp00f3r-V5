package com.nf_sp00f.app.ble

import android.bluetooth.*
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.content.Context
import android.os.ParcelUuid
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import android.util.Log
import java.util.*

/**
 * Lightweight peripheral-mode BLE connection manager. This class starts a
 * BluetoothGattServer advertising a Nordic-UART-like service and provides
 * send/receive primitives that are protocol-compatible with the desktop
 * bluetooth_manager_ble.BLEMessage framing.
 *
 * Note: This class performs real Android BLE operations and therefore will
 * only be exercised end-to-end on an Android device. The fragmentation
 * and reassembly logic is pure-JVM and unit-tested separately.
 */
class BleConnectionManager(private val context: Context) {
    companion object {
        private const val TAG = "BleConnectionManager"
        // Nordic UART Service / characteristics used by the desktop code
        val SERVICE_UUID: UUID = UUID.fromString("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        val RX_CHAR_UUID: UUID = UUID.fromString("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
        val TX_CHAR_UUID: UUID = UUID.fromString("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
    }

    private val bluetoothManager: BluetoothManager? = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager?
    private val adapter: BluetoothAdapter? = bluetoothManager?.adapter
    private var advertiser: BluetoothLeAdvertiser? = null
    private var gattServer: BluetoothGattServer? = null
    private val connectedDevices: MutableSet<BluetoothDevice> = mutableSetOf()
    private val fragmentManager = MessageFragmentManager(mtu = 20)

    // Callbacks
    var onMessageReceived: ((BLEMessageType, ByteArray) -> Unit)? = null
    var onDeviceConnected: ((BluetoothDevice) -> Unit)? = null
    var onDeviceDisconnected: ((BluetoothDevice) -> Unit)? = null

    private val gattCallback = object : BluetoothGattServerCallback() {
        override fun onConnectionStateChange(device: BluetoothDevice?, status: Int, newState: Int) {
            super.onConnectionStateChange(device, status, newState)
            device ?: return
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                connectedDevices.add(device)
                onDeviceConnected?.invoke(device)
                Log.i(TAG, "Device connected: ${device.address}")
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                connectedDevices.remove(device)
                onDeviceDisconnected?.invoke(device)
                Log.i(TAG, "Device disconnected: ${device.address}")
            }
        }

        override fun onCharacteristicWriteRequest(
            device: BluetoothDevice?,
            requestId: Int,
            characteristic: BluetoothGattCharacteristic?,
            preparedWrite: Boolean,
            responseNeeded: Boolean,
            offset: Int,
            value: ByteArray?
        ) {
            super.onCharacteristicWriteRequest(device, requestId, characteristic, preparedWrite, responseNeeded, offset, value)
            try {
                if (value != null) {
                    val completed = fragmentManager.onReceiveFragment(value)
                    if (completed != null) {
                        onMessageReceived?.invoke(completed.first, completed.second)
                    }
                }
            } catch (ex: Exception) {
                Log.e(TAG, "Error handling write request: ${ex.message}")
            } finally {
                if (responseNeeded && device != null && gattServer != null && characteristic != null) {
                    gattServer?.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, 0, null)
                }
            }
        }

        override fun onNotificationSent(device: BluetoothDevice?, status: Int) {
            super.onNotificationSent(device, status)
            Log.d(TAG, "Notification sent to ${device?.address} status=$status")
        }
    }

    /**
     * Start advertising a peripheral service and open a GATT server to accept
     * connections from the desktop central (python Bleak client).
     */
    fun startAdvertising(localName: String = "NFSP00F3R"): Boolean {
        try {
            // Basic runtime permission checks to avoid IllegalState/ SecurityException
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val hasAdvertise = ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_ADVERTISE) == PackageManager.PERMISSION_GRANTED
                val hasConnect = ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
                if (!hasAdvertise || !hasConnect) {
                    Log.w(TAG, "Missing BLUETOOTH_ADVERTISE/CONNECT permission")
                    return false
                }
            } else {
                // Pre-Android 12, make sure Bluetooth or Location permission exists
                val hasBluetooth = ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH) == PackageManager.PERMISSION_GRANTED
                val hasLocation = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                if (!hasBluetooth && !hasLocation) {
                    Log.w(TAG, "Missing legacy Bluetooth or Location permission")
                    return false
                }
            }
            if (adapter == null || !adapter.isEnabled) {
                Log.w(TAG, "Bluetooth adapter not available or disabled")
                return false
            }

            advertiser = adapter.bluetoothLeAdvertiser
            if (advertiser == null) {
                Log.w(TAG, "Device does not support BLE advertising")
                return false
            }

            // Build GATT server and service
            gattServer = bluetoothManager?.openGattServer(context, gattCallback)
            val service = BluetoothGattService(SERVICE_UUID, BluetoothGattService.SERVICE_TYPE_PRIMARY)
            val txChar = BluetoothGattCharacteristic(
                TX_CHAR_UUID,
                BluetoothGattCharacteristic.PROPERTY_NOTIFY,
                BluetoothGattCharacteristic.PERMISSION_READ
            )
            val rxChar = BluetoothGattCharacteristic(
                RX_CHAR_UUID,
                BluetoothGattCharacteristic.PROPERTY_WRITE,
                BluetoothGattCharacteristic.PERMISSION_WRITE
            )
            service.addCharacteristic(rxChar)
            service.addCharacteristic(txChar)
            gattServer?.addService(service)

            val settings = AdvertiseSettings.Builder()
                .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
                .setConnectable(true)
                .setTimeout(0)
                .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
                .build()

            val data = AdvertiseData.Builder()
                .setIncludeDeviceName(true)
                .addServiceUuid(ParcelUuid(SERVICE_UUID))
                .build()

            advertiser?.startAdvertising(settings, data, advertiseCallback)
            Log.i(TAG, "Started advertising: $localName, service=$SERVICE_UUID")
            return true
        } catch (ex: Exception) {
            Log.e(TAG, "Failed to start advertising: ${ex.message}")
            return false
        }
    }

    fun stopAdvertising() {
        try {
            advertiser?.stopAdvertising(advertiseCallback)
        } catch (_: Exception) {}
        try {
            gattServer?.close()
        } catch (_: Exception) {}
        connectedDevices.clear()
    }

    private val advertiseCallback = object : AdvertiseCallback() {
        override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
            super.onStartSuccess(settingsInEffect)
            Log.i(TAG, "Advertise started: $settingsInEffect")
        }

        override fun onStartFailure(errorCode: Int) {
            super.onStartFailure(errorCode)
            Log.e(TAG, "Advertise failed: $errorCode")
        }
    }

    /**
     * Send a high-level message to connected central(s). Message will be
     * fragmented according to the project's rules and pushed as characteristic
     * notifications to currently connected devices.
     */
    fun sendMessage(messageType: BLEMessageType, payload: ByteArray): Boolean {
        try {
            val txChar = gattServer?.getService(SERVICE_UUID)?.getCharacteristic(TX_CHAR_UUID) ?: run {
                Log.w(TAG, "TX characteristic not initialized")
                return false
            }

            val fragments = fragmentManager.fragmentMessage(messageType, payload)
            for (frag in fragments) {
                for (device in connectedDevices) {
                    txChar.value = frag
                    gattServer?.notifyCharacteristicChanged(device, txChar, false)
                }
            }
            return true
        } catch (ex: Exception) {
            Log.e(TAG, "Failed to send message: ${ex.message}")
            return false
        }
    }
}
