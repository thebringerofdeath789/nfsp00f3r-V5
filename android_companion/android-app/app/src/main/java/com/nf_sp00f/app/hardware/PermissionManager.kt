package com.nf_sp00f.app.hardware

import android.Manifest
import android.app.Activity
import android.bluetooth.BluetoothAdapter
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.nfc.NfcAdapter
import android.os.Build
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class PermissionStatus(
    val permission: String,
    val isGranted: Boolean,
    val shouldShowRationale: Boolean = false
)

class PermissionManager(private val context: Context) {
    
    companion object {
        const val NFC_PERMISSION_REQUEST = 1001
        const val BLUETOOTH_PERMISSION_REQUEST = 1002
        const val LOCATION_PERMISSION_REQUEST = 1003
        
        val REQUIRED_PERMISSIONS = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.NFC,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        } else {
            arrayOf(
                Manifest.permission.NFC,
                Manifest.permission.BLUETOOTH,
                Manifest.permission.BLUETOOTH_ADMIN,
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        }
    }
    
    private val _permissionStatus = MutableStateFlow<List<PermissionStatus>>(emptyList())
    val permissionStatus: StateFlow<List<PermissionStatus>> = _permissionStatus.asStateFlow()
    
    private val _allPermissionsGranted = MutableStateFlow(false)
    val allPermissionsGranted: StateFlow<Boolean> = _allPermissionsGranted.asStateFlow()
    
    private val _statusMessage = MutableStateFlow("")
    val statusMessage: StateFlow<String> = _statusMessage.asStateFlow()
    
    init {
        checkAllPermissions()
    }
    
    fun checkAllPermissions() {
        val statusList = REQUIRED_PERMISSIONS.map { permission ->
            val isGranted = ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
            val shouldShowRationale = if (context is Activity) {
                ActivityCompat.shouldShowRequestPermissionRationale(context, permission)
            } else false
            
            PermissionStatus(permission, isGranted, shouldShowRationale)
        }
        
        _permissionStatus.value = statusList
        _allPermissionsGranted.value = statusList.all { it.isGranted }
        
        updateStatusMessage(statusList)
    }
    
    private fun updateStatusMessage(statusList: List<PermissionStatus>) {
        val deniedPermissions = statusList.filter { !it.isGranted }
        
        _statusMessage.value = when {
            deniedPermissions.isEmpty() -> "All permissions granted"
            deniedPermissions.size == 1 -> "Missing permission: ${getPermissionDisplayName(deniedPermissions[0].permission)}"
            else -> "Missing ${deniedPermissions.size} permissions"
        }
    }
    
    fun requestMissingPermissions(activity: Activity) {
        val missingPermissions = _permissionStatus.value
            .filter { !it.isGranted }
            .map { it.permission }
            .toTypedArray()
        
        if (missingPermissions.isNotEmpty()) {
            _statusMessage.value = "Requesting permissions..."
            ActivityCompat.requestPermissions(activity, missingPermissions, NFC_PERMISSION_REQUEST)
        }
    }
    
    fun onPermissionResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        when (requestCode) {
            NFC_PERMISSION_REQUEST, BLUETOOTH_PERMISSION_REQUEST, LOCATION_PERMISSION_REQUEST -> {
                checkAllPermissions()
            }
        }
    }
    
    fun isNfcEnabled(): Boolean {
        val nfcAdapter = NfcAdapter.getDefaultAdapter(context)
        return nfcAdapter?.isEnabled == true
    }
    
    fun isBluetoothEnabled(): Boolean {
        val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        return bluetoothAdapter?.isEnabled == true
    }
    
    fun requestEnableNfc(activity: Activity) {
        val intent = Intent(Settings.ACTION_NFC_SETTINGS)
        activity.startActivity(intent)
        _statusMessage.value = "Please enable NFC in settings"
    }
    
    fun requestEnableBluetooth(activity: Activity) {
        val intent = Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
        activity.startActivity(intent)
        _statusMessage.value = "Please enable Bluetooth"
    }
    
    fun getPermissionDisplayName(permission: String): String {
        return when (permission) {
            Manifest.permission.NFC -> "NFC"
            Manifest.permission.BLUETOOTH -> "Bluetooth"
            Manifest.permission.BLUETOOTH_ADMIN -> "Bluetooth Admin"
            Manifest.permission.BLUETOOTH_CONNECT -> "Bluetooth Connect"
            Manifest.permission.BLUETOOTH_SCAN -> "Bluetooth Scan"
            Manifest.permission.ACCESS_FINE_LOCATION -> "Fine Location"
            Manifest.permission.ACCESS_COARSE_LOCATION -> "Coarse Location"
            else -> permission.substringAfterLast(".")
        }
    }
    
    fun getDetailedPermissionInfo(): String {
        val sb = StringBuilder()
        
        sb.appendLine("=== PERMISSION STATUS ===")
        _permissionStatus.value.forEach { status ->
            val statusText = if (status.isGranted) "✓ GRANTED" else "✗ DENIED"
            sb.appendLine("${getPermissionDisplayName(status.permission)}: $statusText")
        }
        
        sb.appendLine("\n=== HARDWARE STATUS ===")
        sb.appendLine("NFC Enabled: ${if (isNfcEnabled()) "✓ YES" else "✗ NO"}")
        sb.appendLine("Bluetooth Enabled: ${if (isBluetoothEnabled()) "✓ YES" else "✗ NO"}")
        
        val nfcAdapter = NfcAdapter.getDefaultAdapter(context)
        sb.appendLine("NFC Hardware: ${if (nfcAdapter != null) "✓ AVAILABLE" else "✗ NOT AVAILABLE"}")
        
        val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        sb.appendLine("Bluetooth Hardware: ${if (bluetoothAdapter != null) "✓ AVAILABLE" else "✗ NOT AVAILABLE"}")
        
        return sb.toString()
    }
    
    fun checkSystemReady(): SystemReadyStatus {
        val nfcReady = isNfcEnabled() && _permissionStatus.value.any { 
            it.permission == Manifest.permission.NFC && it.isGranted 
        }
        
        val bluetoothReady = isBluetoothEnabled() && _permissionStatus.value.any {
            (it.permission == Manifest.permission.BLUETOOTH || 
             it.permission == Manifest.permission.BLUETOOTH_CONNECT) && it.isGranted
        }
        
        val locationReady = _permissionStatus.value.any {
            it.permission == Manifest.permission.ACCESS_FINE_LOCATION && it.isGranted
        }
        
        return SystemReadyStatus(
            nfcReady = nfcReady,
            bluetoothReady = bluetoothReady,
            locationReady = locationReady,
            allReady = nfcReady && bluetoothReady && locationReady
        )
    }
}

data class SystemReadyStatus(
    val nfcReady: Boolean,
    val bluetoothReady: Boolean,
    val locationReady: Boolean,
    val allReady: Boolean
)
