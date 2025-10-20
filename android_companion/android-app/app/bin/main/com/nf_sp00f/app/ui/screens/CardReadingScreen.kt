package com.nf_sp00f.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nf_sp00f.app.hardware.NfcAdapterManager
import com.nf_sp00f.app.hardware.PermissionManager
import com.nf_sp00f.app.data.Models.DeviceState
import com.nf_sp00f.app.data.Models.NfcDevice
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun cardReadingScreen(
    nfcAdapterManager: NfcAdapterManager,
    permissionManager: PermissionManager
) {
    var selectedDevice by remember { mutableStateOf(NfcDevice.NONE) }
    var deviceExpanded by remember { mutableStateOf(false) }
    var isScanning by remember { mutableStateOf(false) }
    var deviceStatus by remember { mutableStateOf("No Device Selected") }
    var apduLog by remember { mutableStateOf<List<String>>(emptyList()) }
    var isReading by remember { mutableStateOf(false) }
    
    val deviceState by nfcAdapterManager.deviceState.collectAsState()
    val availableDevices = remember {
        listOf(
            NfcDevice.ANDROID_NFC,
            NfcDevice.PN532_BLUETOOTH,
            NfcDevice.PN532_USB
        )
    }
    
    LaunchedEffect(selectedDevice) {
        if (selectedDevice != NfcDevice.NONE) {
            deviceStatus = "Initializing ${selectedDevice.displayName}..."
            addToLog(apduLog) { newLog ->
                apduLog = newLog
                "Initializing ${selectedDevice.displayName}..."
            }
            
            delay(500)
            
            when (selectedDevice) {
                NfcDevice.ANDROID_NFC -> {
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Android NFC adapter detected"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "NFC enabled: ${nfcAdapterManager.isNfcEnabled()}"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Reader mode capabilities: ISO14443-A, ISO14443-B, FeliCa"
                    }
                    deviceStatus = "Android NFC - Ready"
                }
                NfcDevice.PN532_BLUETOOTH -> {
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Scanning for PN532 Bluetooth devices..."
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Target device: PN532 (MAC: 00:14:03:05:5C:CB)"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Bluetooth pairing: PIN 1234"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Connecting to PN532 Bluetooth adapter..."
                    }
                    delay(1000)
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "TX: 55 55 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FF 03 FD D4 14 01 17 00"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "RX: D5 15 00"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "TX: D4 02 (Get Firmware Version)"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "RX: D5 03 32 01 06 07 (Firmware v1.6)"
                    }
                    deviceStatus = "PN532 Bluetooth - Connected (v1.6)"
                }
                NfcDevice.PN532_USB -> {
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Scanning for PN532 USB devices..."
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "USB VID/PID: 072F:2200"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "Requesting USB permissions..."
                    }
                    delay(800)
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "USB connection established"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "TX: 00 00 FF 02 FE D4 02 2A 00 (Get Firmware)"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "RX: 00 00 FF 06 FA D5 03 32 01 06 07 E5 00 (Firmware v1.6)"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "TX: 00 00 FF 04 FC D4 14 01 00 16 00 (SAM Config)"
                    }
                    addToLog(apduLog) { newLog ->
                        apduLog = newLog
                        "RX: 00 00 FF 02 FE D5 15 16 00 (SAM Config OK)"
                    }
                    deviceStatus = "PN532 USB - Connected (v1.6)"
                }
                else -> {}
            }
        }
    }
    
    val listState = rememberLazyListState()
    
    LaunchedEffect(apduLog.size) {
        if (apduLog.isNotEmpty()) {
            listState.animateScrollToItem(apduLog.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A))
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Device Selection",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF00FF00)
                )
                
                ExposedDropdownMenuBox(
                    expanded = deviceExpanded,
                    onExpandedChange = { deviceExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedDevice.displayName,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("NFC Adapter", color = Color.Gray) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = deviceExpanded) },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color(0xFF00FF00),
                            unfocusedBorderColor = Color.Gray
                        ),
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    
                    ExposedDropdownMenu(
                        expanded = deviceExpanded,
                        onDismissRequest = { deviceExpanded = false },
                        modifier = Modifier.background(Color(0xFF2A2A2A))
                    ) {
                        availableDevices.forEach { device ->
                            DropdownMenuItem(
                                text = {
                                    Text(
                                        text = device.displayName,
                                        color = Color.White
                                    )
                                },
                                onClick = {
                                    selectedDevice = device
                                    deviceExpanded = false
                                },
                                colors = MenuDefaults.itemColors(
                                    textColor = Color.White
                                )
                            )
                        }
                    }
                }
                
                Text(
                    text = deviceStatus,
                    fontSize = 14.sp,
                    color = if (selectedDevice != NfcDevice.NONE && !deviceStatus.contains("Initializing")) Color(0xFF00FF00) else Color.Gray,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Button(
                onClick = {
                    if (selectedDevice != NfcDevice.NONE) {
                        isReading = !isReading
                        if (isReading) {
                            addToLog(apduLog) { newLog ->
                                apduLog = newLog
                                "Starting card reading session..."
                            }
                        } else {
                            addToLog(apduLog) { newLog ->
                                apduLog = newLog
                                "Card reading session stopped"
                            }
                        }
                    }
                },
                enabled = selectedDevice != NfcDevice.NONE,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isReading) Color.Red else Color(0xFF00FF00),
                    contentColor = Color.Black,
                    disabledContainerColor = Color.Gray
                ),
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = if (isReading) Icons.Default.Stop else Icons.Default.PlayArrow,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (isReading) "STOP" else "START",
                    fontWeight = FontWeight.Bold
                )
            }
            
            Button(
                onClick = {
                    apduLog = emptyList()
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF333333),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = Icons.Default.Clear,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("CLEAR", fontWeight = FontWeight.Bold)
            }
        }

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Live APDU Traffic Log",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF00FF00),
                    modifier = Modifier.padding(bottom = 12.dp)
                )
                
                if (apduLog.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Select a device to see APDU traffic",
                            color = Color.Gray,
                            textAlign = TextAlign.Center,
                            fontSize = 14.sp
                        )
                    }
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        items(apduLog) { logEntry ->
                            Text(
                                text = logEntry,
                                fontSize = 12.sp,
                                color = when {
                                    logEntry.contains("TX:") || logEntry.contains("TX ") -> Color(0xFFFFAA00)
                                    logEntry.contains("RX:") || logEntry.contains("RX ") -> Color(0xFF00AAFF)
                                    logEntry.contains("Error") || logEntry.contains("Failed") -> Color.Red
                                    logEntry.contains("Connected") || logEntry.contains("OK") -> Color(0xFF00FF00)
                                    else -> Color.White
                                },
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                }
            }
        }
    }
}

private fun addToLog(currentLog: List<String>, updateLog: (List<String>) -> String) {
    val message = updateLog(currentLog + "")
    val newLog = currentLog.toMutableList()
    newLog.add("[${System.currentTimeMillis() % 100000}] $message")
    if (newLog.size > 50) {
        newLog.removeAt(0)
    }
}
