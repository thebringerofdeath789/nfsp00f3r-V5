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
import android.content.Context
import java.io.File
import org.json.JSONObject
import androidx.compose.runtime.LaunchedEffect

@Composable
fun emulationScreen(context: Context) {
    var selectedCard by remember { mutableStateOf<VirtualCard?>(null) }
    var selectedAttack by remember { mutableStateOf("Standard Emulation") }
    var isEmulating by remember { mutableStateOf(false) }
    var hceStatus by remember { mutableStateOf("HCE Service Ready") }

    val attackProfiles = listOf(
        "Standard Emulation", "PPSE Poisoning", "AIP Force Offline",
        "Track2 Spoofing", "Cryptogram Downgrade", "CVM Bypass"
    )

    var realCards by remember { mutableStateOf(listOf<VirtualCard>()) }

    // Scan app files directory for card data files and parse them
    LaunchedEffect(Unit) {
        val cardList = mutableListOf<VirtualCard>()
        val filesDir = context.filesDir
        filesDir?.listFiles()?.forEach { file ->
            if (file.name.endsWith(".json")) {
                try {
                    val json = JSONObject(file.readText())
                    val cardholderName = json.optString("cardholder_name", "Unknown")
                    val pan = json.optString("pan", "****")
                    val expiry = json.optString("expiry_date", "")
                    val apduCount = json.optJSONArray("apdu_log")?.length() ?: 0
                    val cardType = json.optString("card_type", "Unknown")
                    cardList.add(VirtualCard(cardholderName, pan, expiry, apduCount, cardType))
                } catch (_: Exception) {}
            }
        }
        realCards = cardList
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
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
                    if (selectedCard != null) {
                        isEmulating = !isEmulating
                        hceStatus = if (isEmulating)
                            "Emulating ${selectedCard!!.cardType} - ${selectedAttack}"
                        else "HCE Service Ready"
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
    }
}
