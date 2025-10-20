package com.nf_sp00f.app.ui.screens
import com.nf_sp00f.app.R

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.nf_sp00f.app.data.VirtualCard
import com.nf_sp00f.app.data.ApduLogEntry
import androidx.compose.ui.platform.LocalContext
import java.io.File
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import com.nf_sp00f.app.data.CardProfileManager
import com.nf_sp00f.app.ble.BleConnectionManager
import com.nf_sp00f.app.ble.BLEMessageType
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
import java.util.Locale

@Composable
fun emulationScreen(permissionManager: com.nf_sp00f.app.hardware.PermissionManager, activity: androidx.activity.ComponentActivity) {
    val context = LocalContext.current
    var selectedCard by remember { mutableStateOf<VirtualCard?>(null) }
    var selectedAttack by remember { mutableStateOf("Standard Emulation") }
    var isEmulating by remember { mutableStateOf(false) }
    var hceStatus by remember { mutableStateOf("HCE Service Ready") }

    val attackProfiles = listOf(
        "Standard Emulation", "PPSE Poisoning", "AIP Force Offline",
        "Track2 Spoofing", "Cryptogram Downgrade", "CVM Bypass"
    )

    var realCards by remember { mutableStateOf(listOf<VirtualCard>()) }

    // Use CardProfileManager to list persisted profiles (on-disk JSON) so we
    // preserve profile IDs and ensure consistent exports.
    // Load persisted profiles and refresh when CardProfileManager signals updates
    val profileUpdateCount by CardProfileManager.updates.collectAsState(initial = 0)
    LaunchedEffect(profileUpdateCount) {
        realCards = CardProfileManager.listProfiles(context)
    }

    // BLE manager (peripheral) for exporting profiles and receiving commands
    val bleManager = remember { BleConnectionManager(context) }
    // Register the BLE manager so other services (HCE) can notify the central
    DisposableEffect(bleManager) {
        com.nf_sp00f.app.ble.BleServiceRegistry.register(bleManager)
        onDispose {
            try { com.nf_sp00f.app.ble.BleServiceRegistry.unregister(bleManager) } catch (_: Exception) {}
        }
    }
    var isAdvertising by remember { mutableStateOf(false) }
    var bleStatus by remember { mutableStateOf("Not Advertising") }
    var showApduDialog by remember { mutableStateOf(false) }
    var apduEntries by remember { mutableStateOf(listOf<String>()) }
    val allPermissionsGranted by permissionManager.allPermissionsGranted.collectAsState(initial = false)
    val detailedPerms by remember { mutableStateOf(permissionManager.getDetailedPermissionInfo()) }

    // Wire BLE incoming messages to allow desktop -> Android profile pushes
    LaunchedEffect(bleManager) {
        bleManager.onMessageReceived = { type, payload ->
            try {
                if (type == BLEMessageType.SESSION_DATA) {
                    try {
                        val sessionJson = JSONObject(String(payload, Charsets.UTF_8))
                        // Map the exported/session JSON shape to the flat on-disk
                        // profile structure expected by CardProfileManager.
                        val profileJson = com.nf_sp00f.app.data.SessionDataMapper.mapSessionToProfile(sessionJson)
                        val id = CardProfileManager.saveProfile(context, profileJson)
                        Handler(Looper.getMainLooper()).post {
                            bleStatus = "Received SESSION_DATA, mapped and saved profile: $id"
                        }
                    } catch (e: Exception) {
                        Handler(Looper.getMainLooper()).post {
                            bleStatus = "Failed to parse or save incoming session: ${e.message}"
                        }
                    }
                } else if (type == BLEMessageType.APDU_TRACE) {
                    // Persist incoming APDU trace to exports and annotate active profile
                    val traceJson = String(payload, Charsets.UTF_8)
                    val ts = System.currentTimeMillis()
                    val outDir = java.io.File(context.filesDir, "exports")
                    if (!outDir.exists()) outDir.mkdirs()
                    val outFile = java.io.File(outDir, "apdu_trace_$ts.json")
                    try {
                        outFile.writeText(traceJson)
                        // If an active profile exists, annotate its apdu_log
                        val active = CardProfileManager.getActiveProfile(context)
                        if (active != null) {
                            val apduArr = active.optJSONArray("apdu_log") ?: org.json.JSONArray()
                            apduArr.put("APDU_TRACE_SAVED:${outFile.name}")
                            active.put("apdu_log", apduArr)
                            CardProfileManager.saveProfile(context, active, active.optString("card_id", null))
                        }
                        Handler(Looper.getMainLooper()).post {
                            bleStatus = "Received APDU_TRACE, saved: ${outFile.absolutePath}"
                        }
                    } catch (e: Exception) {
                        Handler(Looper.getMainLooper()).post {
                            bleStatus = "Failed to save APDU_TRACE: ${e.message}"
                        }
                    }
                } else {
                    Handler(Looper.getMainLooper()).post {
                        bleStatus = "Received message: $type"
                    }
                }
            } catch (e: Exception) {
                Handler(Looper.getMainLooper()).post {
                    bleStatus = "Error handling BLE message: ${e.message}"
                }
            }
        }

        bleManager.onDeviceConnected = { device ->
            Handler(Looper.getMainLooper()).post { bleStatus = "Device connected: ${device.address}" }
        }
        bleManager.onDeviceDisconnected = { device ->
            Handler(Looper.getMainLooper()).post { bleStatus = "Device disconnected: ${device.address}" }
        }
    }

    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(scrollState).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Saved profiles (persisted on disk) — allow selection for emulation
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
            shape = RoundedCornerShape(8.dp)
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Text("Saved Profiles", color = Color(0xFF4CAF50), fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
                if (realCards.isEmpty()) {
                    Text("No saved profiles found", color = Color.Gray)
                } else {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(realCards) { card ->
                            Card(
                                modifier = Modifier
                                    .width(220.dp)
                                    .clickable { selectedCard = card }
                                    .padding(4.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = if (selectedCard?.profileId == card.profileId) Color(0xFF4CAF50).copy(alpha = 0.2f) else Color(0xFF2A2A2A)
                                ),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Column(modifier = Modifier.padding(8.dp)) {
                                    // Normalize and sanitize display values to avoid misspellings
                                    fun normalizeName(input: String): String {
                                        val t = input.trim()
                                        if (t.isEmpty()) return "Unknown"
                                        val low = t.lowercase(Locale.getDefault())
                                        if (low.contains("unkn") || low.contains("unkniwn") || low.contains("unkown")) return "Unknown"
                                        return t
                                    }

                                    fun maskPan(pan: String): String {
                                        val digits = pan.filter { it.isDigit() }
                                        return when {
                                            digits.length >= 10 -> digits.take(6) + "..." + digits.takeLast(4)
                                            digits.length >= 4 -> "**** **** **** " + digits.takeLast(4)
                                            pan.isNotBlank() -> pan
                                            else -> "PAN: N/A"
                                        }
                                    }

                                    val displayName = normalizeName(card.cardholderName)
                                    Text(displayName, color = Color.White, fontWeight = FontWeight.Bold)
                                    Spacer(modifier = Modifier.height(4.dp))
                                    val maskedPan = maskPan(card.pan)
                                    Text(maskedPan, color = Color(0xFFCCCCCC))
                                    Spacer(modifier = Modifier.height(6.dp))
                                    val expiryStr = if (card.expiry.isBlank()) "N/A" else card.expiry
                                    Text("Exp: $expiryStr", color = Color(0xFFAAAAAA), fontSize = MaterialTheme.typography.labelSmall.fontSize)
                                }
                            }
                        }
                    }
                }
            }
        }
        // HCE Status Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
            shape = RoundedCornerShape(8.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Box(modifier = Modifier.fillMaxWidth()) {
                Image(
                    painter = painterResource(id = R.drawable.nfspoof_logo),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxWidth().height(120.dp),
                    alpha = 0.1f
                )

                Column(
                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "EMV HCE EmULaToR",
                        style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Bold),
                        color = Color(0xFF4CAF50),
                        textAlign = TextAlign.Center
                    )
                    Text(
                        "Card Attack Profiles",
                        style = MaterialTheme.typography.titleMedium.copy(
                            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline
                        ),
                        color = Color(0xFFFFFFFF),
                        textAlign = TextAlign.Center
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        hceStatus,
                        style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                        color = if (isEmulating) Color(0xFF4CAF50) else Color(0xFFFF9800),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        // Attack Profile Selection
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
            shape = RoundedCornerShape(8.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    "Attack Profile",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.Bold,
                        textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline
                    ),
                    color = Color(0xFF4CAF50),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Attack profile grid - 2 columns
                attackProfiles.chunked(2).forEach { rowProfiles ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        rowProfiles.forEach { profile ->
                            Card(
                                modifier = Modifier.weight(1f).clickable { selectedAttack = profile },
                                colors = CardDefaults.cardColors(
                                    containerColor = if (selectedAttack == profile) 
                                        Color(0xFF4CAF50).copy(alpha = 0.3f) 
                                    else Color(0xFF2A2A2A)
                                ),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Text(
                                    profile,
                                    style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
                                    color = if (selectedAttack == profile) Color(0xFFFFFFFF) else Color(0xFF4CAF50),
                                    textAlign = TextAlign.Center,
                                    modifier = Modifier.padding(8.dp).fillMaxWidth(),
                                    maxLines = 2
                                )
                            }
                        }
                        if (rowProfiles.size == 1) {
                            Spacer(modifier = Modifier.weight(1f))
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }

        // Control Buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Button(
                onClick = {
                    val card = selectedCard
                    if (card != null) {
                        isEmulating = !isEmulating
                        if (isEmulating) {
                            // Activate the selected profile so HCE services can load it
                            CardProfileManager.setActiveProfile(context, card.profileId)
                            hceStatus = "Emulating ${card.cardType} - ${selectedAttack}"
                        } else {
                            // Clear active profile on stop
                            CardProfileManager.setActiveProfile(context, null)
                            hceStatus = "HCE Service Ready"
                        }
                    }
                },
                enabled = selectedCard != null,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isEmulating) Color(0xFFCF1B33) else Color(0xFF4CAF50),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) {
                if (isEmulating) {
                    Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                }
                Text(if (isEmulating) "Stop Emulation" else "Start Emulation")
            }

            Button(
                onClick = {
                    selectedCard = null
                    selectedAttack = "Standard Emulation"
                    isEmulating = false
                    hceStatus = "HCE Service Ready"
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF444444),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) { Text("Reset") }
        }

            // BLE Controls: Start/Stop advertising and export selected profile
            Button(
                onClick = {
                    if (!isAdvertising) {
                        // Ensure runtime permissions are available before attempting to advertise
                        if (!allPermissionsGranted) {
                            bleStatus = "Missing permissions - requesting..."
                            permissionManager.requestMissingPermissions(activity)
                            return@Button
                        }

                        if (!permissionManager.isBluetoothEnabled()) {
                            permissionManager.requestEnableBluetooth(activity)
                            bleStatus = "Please enable Bluetooth"
                            return@Button
                        }

                        val ok = bleManager.startAdvertising()
                        isAdvertising = ok
                        bleStatus = if (ok) "Advertising" else "Advertising Failed"
                    } else {
                        bleManager.stopAdvertising()
                        isAdvertising = false
                        bleStatus = "Not Advertising"
                    }
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isAdvertising) Color(0xFFCF1B33) else Color(0xFF4CAF50),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) {
                Text(if (isAdvertising) "Stop Advertising" else "Start Advertising")
            }

            Button(
                onClick = {
                    val card = selectedCard
                    if (card?.profileId != null) {
                        val profileJson = CardProfileManager.readProfile(context, card.profileId!!)
                        if (profileJson != null) {
                            val payload = profileJson.toString().toByteArray(Charsets.UTF_8)
                            val sent = bleManager.sendMessage(BLEMessageType.SESSION_DATA, payload)
                            bleStatus = if (sent) "Profile exported" else "Export failed"
                        } else {
                            bleStatus = "Profile not found"
                        }
                    } else {
                        bleStatus = "No profile selected"
                    }
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF444444),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) { Text("Export Profile") }

            Button(
                onClick = {
                    val card = selectedCard
                    if (card?.profileId != null) {
                        val outFile = CardProfileManager.exportProfile(context, card.profileId!!)
                        bleStatus = if (outFile != null) "Saved export: ${outFile.absolutePath}" else "Export save failed"
                    } else {
                        bleStatus = "No profile selected"
                    }
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF444444),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) { Text("Save Export") }

            Button(
                onClick = {
                    // View APDU log for the selected profile (or active profile)
                    val targetId = selectedCard?.profileId ?: CardProfileManager.getActiveProfile(context)?.optString("card_id")
                    if (targetId == null) {
                        bleStatus = "No profile selected or active"
                        return@Button
                    }
                    val profile = CardProfileManager.readProfile(context, targetId)
                    if (profile == null) {
                        bleStatus = "Profile not found"
                        return@Button
                    }
                    val arr = profile.optJSONArray("apdu_log") ?: org.json.JSONArray()
                    val list = mutableListOf<String>()
                    for (i in 0 until arr.length()) {
                        list.add(arr.optString(i))
                    }
                    apduEntries = list
                    showApduDialog = true
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF444444),
                    contentColor = Color.White
                ),
                modifier = Modifier.weight(1f)
            ) { Text("View APDU Log") }
    }

        // BLE status display and permission summary
        Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                bleStatus,
                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                color = Color(0xFFCCCCCC),
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Permissions: ${if (allPermissionsGranted) "All Granted" else "Missing"}",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFFAAAAAA)
            )
        }

        if (showApduDialog) {
            AlertDialog(
                onDismissRequest = { showApduDialog = false },
                title = { Text("APDU Log") },
                text = {
                    if (apduEntries.isEmpty()) {
                        Text("No APDU entries found", color = Color.Gray)
                    } else {
                        LazyColumn(modifier = Modifier.height(280.dp)) {
                            items(apduEntries) { entry ->
                                Text(entry, fontSize = MaterialTheme.typography.bodySmall.fontSize, color = Color.White)
                                Divider(color = Color(0xFF2A2A2A))
                            }
                        }
                    }
                },
                confirmButton = {
                    TextButton(onClick = { showApduDialog = false }) { Text("Close") }
                }
            )
        }

        // Ensure BLE advertising is stopped when leaving this screen
        DisposableEffect(key1 = bleManager) {
            onDispose {
                try { if (isAdvertising) bleManager.stopAdvertising() } catch (_: Exception) {}
            }
        }
}
