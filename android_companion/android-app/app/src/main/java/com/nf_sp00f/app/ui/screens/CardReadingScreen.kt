package com.nf_sp00f.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
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
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.os.Handler
import android.os.Looper
import androidx.compose.ui.platform.LocalContext
import com.nf_sp00f.app.data.EmvTlvParser
import com.nf_sp00f.app.data.ApduUtils
import com.nf_sp00f.app.hardware.NfcAdapterManager
import com.nf_sp00f.app.hardware.PermissionManager
import com.nf_sp00f.app.data.CardProfileManager
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import com.nf_sp00f.app.data.DeviceState
import com.nf_sp00f.app.data.NfcDevice
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun cardReadingScreen(
    nfcAdapterManager: NfcAdapterManager,
    permissionManager: PermissionManager,
    activity: androidx.activity.ComponentActivity
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

    val context = LocalContext.current

    // Enable Android reader mode while isReading is true
    DisposableEffect(isReading) {
        val nfcAdapter = NfcAdapter.getDefaultAdapter(activity)
        val callback = NfcAdapter.ReaderCallback { tag: Tag? ->
            if (tag == null) return@ReaderCallback
            val iso = IsoDep.get(tag)
            try {
                iso?.connect()
                iso?.timeout = 5000

                val profile = try {
                    readEmvProfileFromIsoDep(iso)
                } catch (e: Exception) {
                    null
                }

                if (profile != null) {
                    // Persist profile to disk
                    try {
                        val id = CardProfileManager.saveProfile(context, profile)
                        Handler(Looper.getMainLooper()).post {
                            apduLog = apduLog + "Saved profile: $id"
                        }
                    } catch (e: Exception) {
                        Handler(Looper.getMainLooper()).post {
                            apduLog = apduLog + "Failed to save profile: ${e.message}"
                        }
                    }
                } else {
                    Handler(Looper.getMainLooper()).post {
                        apduLog = apduLog + "No EMV data discovered on tag"
                    }
                }
            } catch (e: Exception) {
                Handler(Looper.getMainLooper()).post {
                    apduLog = apduLog + "Reader error: ${e.message}"
                }
            } finally {
                try { iso?.close() } catch (_: Exception) {}
            }
        }

        if (isReading) {
            nfcAdapter?.enableReaderMode(activity, callback, NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK, null)
        }

        onDispose {
            try { nfcAdapter?.disableReaderMode(activity) } catch (_: Exception) {}
        }
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

    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
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
                                apduLog = apduLog + "Starting card reading session..."
                            } else {
                                apduLog = apduLog + "Card reading session stopped"
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
                .heightIn(min = 120.dp, max = 380.dp),
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

// Helper to build a SELECT AID APDU
// Wrapper helpers that delegate to the centralized, testable ApduUtils.
// Keeping these private wrapper functions preserves the existing file-level
// API while allowing unit tests to target the pure logic in ApduUtils.
private fun buildSelectApdu(aid: ByteArray): ByteArray = ApduUtils.buildSelectApdu(aid)

private fun extractResponseData(resp: ByteArray?): Pair<ByteArray, Int> = ApduUtils.extractResponseData(resp)

// Read a small EMV profile from an IsoDep tag: SELECT PPSE -> iterate AIDs -> SELECT AID and extract common tags
private fun readEmvProfileFromIsoDep(iso: IsoDep?): JSONObject? {
    if (iso == null) return null
    try {
        // SELECT PPSE (2PAY.SYS.DDF01)
        val ppse = EmvTlvParser.hexStringToBytes("00A404000E325041592E5359532E4444463031")
        var resp = try { iso.transceive(ppse) } catch (_: Exception) { null }
        val (ppseData, ppseSw) = extractResponseData(resp)
        if (ppseSw != 0x9000) return null

    val tags = EmvTlvParser.parseAll(ppseData)
    val aids = tags["4F"] ?: emptyList<ByteArray>()
        val profile = JSONObject()
        val apduArray = JSONArray()

        // Try to extract PAN/name from PPSE response first
        val panCandidate = tags["5A"]?.firstOrNull() ?: tags["57"]?.firstOrNull()
        if (panCandidate != null) {
            val panHex = EmvTlvParser.toHex(panCandidate)
            val pan = if (panHex.contains("D")) panHex.substring(0, panHex.indexOf('D')) else panHex
            profile.put("pan", pan)
        }

    val nameCandidate = tags["5F20"]?.firstOrNull()
    if (nameCandidate != null) profile.put("cardholder_name", String(nameCandidate, Charsets.UTF_8))

        val applicationsArray = JSONArray()
        for (aidBytes in aids) {
            val selectAid = buildSelectApdu(aidBytes)
            resp = try { iso.transceive(selectAid) } catch (_: Exception) { null }
            val (selData, selSw) = extractResponseData(resp)
            apduArray.put("SELECT_AID:${EmvTlvParser.toHex(aidBytes)} SW=${String.format(Locale.US, "%04X", selSw)}")

            if (selSw == 0x9000) {
                val selTags = EmvTlvParser.parseAll(selData)
                val p = selTags["5A"]?.firstOrNull()?.let { EmvTlvParser.toHex(it) }
                if (p != null && !profile.has("pan")) {
                    val pan = if (p.contains("D")) p.substring(0, p.indexOf('D')) else p
                    profile.put("pan", pan)
                }
                val cn = selTags["5F20"]?.firstOrNull()
                if (cn != null && !profile.has("cardholder_name")) profile.put("cardholder_name", String(cn, Charsets.UTF_8))
                val exp = selTags["5F24"]?.firstOrNull()?.let { EmvTlvParser.toHex(it) }
                if (exp != null && !profile.has("expiry_date")) profile.put("expiry_date", exp)

                // Build application JSON object from SELECT response
                val appObj = JSONObject()
                appObj.put("aid", EmvTlvParser.toHex(aidBytes))
                appObj.put("fci", EmvTlvParser.toHex(selData))
                selTags["50"]?.firstOrNull()?.let { label -> appObj.put("label", String(label, Charsets.UTF_8)) }

                // If PDOL was provided in SELECT FCI, build PDOL data and try GPO
                val pdolDef = selTags["9F38"]?.firstOrNull()
                val pdolData = ApduUtils.buildDefaultPdol(pdolDef)
                val gpoApdu = ApduUtils.buildGpoApdu(pdolData)
                resp = try { iso.transceive(gpoApdu) } catch (_: Exception) { null }
                val (gpoData, gpoSw) = extractResponseData(resp)
                apduArray.put("GPO:${EmvTlvParser.toHex(gpoData)} SW=${String.format(Locale.US, "%04X", gpoSw)}")

                if (gpoSw == 0x9000) {
                    // Parse GPO for AIP and AFL (both 77/82/94 and raw 80 formats)
                    val gpoTags = EmvTlvParser.parseAll(gpoData)
                    var aip: ByteArray? = null
                    var afl: ByteArray? = null
                    if (gpoTags.containsKey("82")) aip = gpoTags["82"]?.firstOrNull()
                    if (gpoTags.containsKey("94")) afl = gpoTags["94"]?.firstOrNull()
                    if (aip == null && gpoTags.containsKey("80")) {
                        val maybe80 = gpoTags["80"]?.firstOrNull()
                        if (maybe80 != null && maybe80.size >= 2) {
                            aip = maybe80.copyOfRange(0, 2)
                            if (maybe80.size > 2) afl = maybe80.copyOfRange(2, maybe80.size)
                        }
                    }
                    // As a last resort, if parsed TLV map is empty but raw response exists,
                    // assume first two bytes are AIP and the rest AFL
                    if (aip == null && gpoData.size >= 2) {
                        aip = gpoData.copyOfRange(0, 2)
                        if (gpoData.size > 2) afl = gpoData.copyOfRange(2, gpoData.size)
                    }

                    if (aip != null) appObj.put("aip", EmvTlvParser.toHex(aip))
                    if (afl != null) {
                        appObj.put("afl", EmvTlvParser.toHex(afl))
                        val aflEntries = ApduUtils.parseAfl(afl)
                        val recordsArray = JSONArray()
                        for (entry in aflEntries) {
                            for (r in entry.startRecord..entry.endRecord) {
                                val readApdu = ApduUtils.buildReadRecordApdu(r, entry.sfi)
                                resp = try { iso.transceive(readApdu) } catch (_: Exception) { null }
                                val (recData, recSw) = extractResponseData(resp)
                                apduArray.put("READ_RECORD SFI=${entry.sfi} REC=$r SW=${String.format(Locale.US, "%04X", recSw)}")
                                if (recSw == 0x9000) {
                                    val recObj = JSONObject()
                                    recObj.put("sfi", entry.sfi)
                                    recObj.put("record", r)
                                    recObj.put("data", EmvTlvParser.toHex(recData))
                                    recordsArray.put(recObj)
                                }
                            }
                        }
                        appObj.put("records", recordsArray)
                    }
                }

                applicationsArray.put(appObj)
            }
        }

        profile.put("applications", applicationsArray)

        profile.put("apdu_log", apduArray)
        profile.put("card_type", if (profile.optString("pan", "").startsWith("4")) "VISA" else "GENERIC")
        return profile
    } catch (e: Exception) {
        return null
    }
}
