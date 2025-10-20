package com.nf_sp00f.app.ui.screens
import com.nf_sp00f.app.R

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.nf_sp00f.app.data.AnalysisResult
import com.nf_sp00f.app.data.AnalysisTool

@Composable
fun analysisScreen() {
    var selectedAnalysisTab by remember { mutableIntStateOf(0) }
    var tlvInput by remember { mutableStateOf("") }
    var fuzzerRunning by remember { mutableStateOf(false) }

    // Sample analysis data
    val recentAnalysis = listOf(
        AnalysisResult("VISA Track2 Analysis", "4154****3556", "PASSED", 95, "2m ago"),
        AnalysisResult("Cryptogram Validation", "5555****4444", "WARNING", 72, "5m ago"),
        AnalysisResult("TTQ Workflow Test", "3782****1007", "FAILED", 34, "1h ago"),
        AnalysisResult("APDU Flow Analysis", "4000****0002", "PASSED", 88, "3h ago")
    )

    val analysisTools = listOf(
        AnalysisTool("TLV Browser", "Interactive EMV tag exploration", Icons.Default.Code, true),
        AnalysisTool("Cryptogram Lab", "ARQC/TC/AAC validation suite", Icons.Default.Security, true),
        AnalysisTool("Workflow Analyzer", "TTQ/TVR/TSI deep analysis", Icons.Default.Timeline, false),
        AnalysisTool("APDU Dissector", "Transaction flow inspection", Icons.Default.Analytics, true),
        AnalysisTool("Fuzzer Engine", "Attack vector generation", Icons.Default.BugReport, false),
        AnalysisTool("BER-TLV Parser", "Raw data decoding utilities", Icons.Default.DataObject, true)
    )

    Column(
        modifier = Modifier.fillMaxSize()
            .background(Brush.verticalGradient(colors = listOf(Color(0xFF0F0F0F), Color(0xFF1A1A1A), Color(0xFF0F0F0F))))
            .padding(16.dp)
    ) {
        // Header Card
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
                    modifier = Modifier.fillMaxWidth().height(80.dp),
                    alpha = 0.1f
                )

                Column(
                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "EMV ANALYSIS LAB",
                        style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Bold),
                        color = Color(0xFF4CAF50),
                        textAlign = TextAlign.Center
                    )
                    Text(
                        "Security Research & Forensic Tools",
                        style = MaterialTheme.typography.titleMedium.copy(
                            textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline
                        ),
                        color = Color(0xFFFFFFFF),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Analysis Tools Grid
        Text(
            "Analysis Tools",
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            color = Color(0xFF4CAF50),
            modifier = Modifier.padding(bottom = 8.dp)
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.height(200.dp)
        ) {
            items(analysisTools) { tool ->
                AnalysisToolCard(tool = tool, onClick = { /* Handle tool selection */ })
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Tab Navigation for Analysis Sections
        ScrollableTabRow(
            selectedTabIndex = selectedAnalysisTab,
            containerColor = Color.Transparent,
            contentColor = Color(0xFF4CAF50),
            indicator = { tabPositions ->
                TabRowDefaults.Indicator(
                    modifier = Modifier.tabIndicatorOffset(tabPositions[selectedAnalysisTab]),
                    color = Color(0xFF4CAF50)
                )
            }
        ) {
            val tabs = listOf("TLV Parser", "Cryptogram", "APDU Flow", "Live Monitor")
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedAnalysisTab == index,
                    onClick = { selectedAnalysisTab = index },
                    text = {
                        Text(
                            title,
                            color = if (selectedAnalysisTab == index) Color(0xFF4CAF50) else Color(0xFFAAAAAA)
                        )
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Tab Content
        when (selectedAnalysisTab) {
            0 -> TlvParserContent(tlvInput) { tlvInput = it }
            1 -> CryptogramAnalysisContent()
            2 -> ApduFlowContent(recentAnalysis)
            3 -> LiveMonitorContent(fuzzerRunning) { fuzzerRunning = it }
        }
    }
}

@Composable
fun AnalysisToolCard(tool: AnalysisTool, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().height(80.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (tool.enabled) Color(0xFF121717) else Color(0xFF0A0A0A)
        ),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = if (tool.enabled) 4.dp else 1.dp)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Image(
                painter = painterResource(id = R.drawable.nfspoof_logo),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
                alpha = 0.05f
            )

            Column(
                modifier = Modifier.padding(8.dp).fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    tool.icon,
                    contentDescription = null,
                    tint = if (tool.enabled) Color(0xFF4CAF50) else Color(0xFF666666),
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    tool.title,
                    style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
                    color = if (tool.enabled) Color.White else Color(0xFF666666),
                    textAlign = TextAlign.Center,
                    maxLines = 1
                )
                if (!tool.enabled) {
                    Text(
                        "Coming Soon",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color(0xFF666666)
                    )
                }
            }
        }
    }
}

@Composable
fun TlvParserContent(tlvInput: String, onTlvInputChange: (String) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "BER-TLV Parser",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = Color(0xFF4CAF50)
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = tlvInput,
                onValueChange = onTlvInputChange,
                label = { Text("Enter TLV hex data...", color = Color(0xFF4CAF50)) },
                placeholder = { Text("e.g., 5A084154904674973556", color = Color(0xFFAAAAAA)) },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF4CAF50),
                    unfocusedBorderColor = Color(0xFF4CAF50).copy(alpha = 0.5f),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                ),
                singleLine = false,
                minLines = 3
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { /* Parse TLV */ },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50)),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Parse", color = Color.Black)
                }

                OutlinedButton(
                    onClick = { onTlvInputChange("") },
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF4CAF50))
                ) { Text("Clear") }
            }

            // Sample parsed output
            if (tlvInput.isNotEmpty()) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    "Parsed Tags:",
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color(0xFF4CAF50)
                )

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A))
                ) {
                    Column(modifier = Modifier.padding(8.dp)) {
                        Text(
                            "5A (Application PAN): 4154904674973556",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White,
                            fontFamily = FontFamily.Monospace
                        )
                        Text(
                            "5F24 (Application Expiry): 251201",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White,
                            fontFamily = FontFamily.Monospace
                        )
                        Text(
                            "57 (Track 2 Data): 4154904674973556D25121010000000000F",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun CryptogramAnalysisContent() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "Cryptogram Analysis Lab",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = Color(0xFF4CAF50)
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                CryptogramMetricCard("ARQC", "12", Color(0xFF2196F3), Modifier.weight(1f))
                CryptogramMetricCard("TC", "8", Color(0xFF4CAF50), Modifier.weight(1f))
                CryptogramMetricCard("AAC", "3", Color(0xFFFF5722), Modifier.weight(1f))
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                "Recent Cryptogram Analysis:",
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = Color.White
            )

            Spacer(modifier = Modifier.height(8.dp))

            LazyColumn(
                modifier = Modifier.height(120.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                items(5) { index ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "ARQC #${index + 1}: AB12CD34EF567890",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF4CAF50),
                            fontFamily = FontFamily.Monospace
                        )
                        Text(
                            "VALID",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color(0xFF4CAF50)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ApduFlowContent(recentAnalysis: List<AnalysisResult>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "APDU Flow Analysis",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = Color(0xFF4CAF50)
            )

            Spacer(modifier = Modifier.height(12.dp))

            LazyColumn(
                modifier = Modifier.height(200.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(recentAnalysis) { analysis ->
                    AnalysisResultCard(analysis)
                }
            }
        }
    }
}

@Composable
fun LiveMonitorContent(fuzzerRunning: Boolean, onFuzzerToggle: (Boolean) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "Live Security Monitor",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color(0xFF4CAF50)
                )

                Switch(
                    checked = fuzzerRunning,
                    onCheckedChange = onFuzzerToggle,
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color(0xFF4CAF50),
                        checkedTrackColor = Color(0xFF4CAF50).copy(alpha = 0.5f)
                    )
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            if (fuzzerRunning) {
                Column {
                    Text(
                        "🔍 Scanning for vulnerabilities...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color(0xFF4CAF50)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth(),
                        color = Color(0xFF4CAF50),
                        trackColor = Color(0xFF4CAF50).copy(alpha = 0.3f)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        "• Testing PPSE poisoning vectors\n• Analyzing AIP bypass methods\n• Fuzzing cryptogram validation\n• Monitoring CVM bypass attempts",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFFAAAAAA)
                    )
                }
            } else {
                Text(
                    "Enable live monitoring to start real-time security analysis",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color(0xFFAAAAAA)
                )
            }
        }
    }
}

@Composable
fun CryptogramMetricCard(type: String, count: String, color: Color, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                count,
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
                color = color
            )
            Text(type, style = MaterialTheme.typography.bodySmall, color = Color(0xFFAAAAAA))
        }
    }
}

@Composable
fun AnalysisResultCard(analysis: AnalysisResult) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0A0A)),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    analysis.title,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color.White
                )
                Text(
                    analysis.cardNumber,
                    style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                    color = Color(0xFFAAAAAA)
                )
            }

            Column(horizontalAlignment = Alignment.End) {
                val statusColor = when (analysis.status) {
                    "PASSED" -> Color(0xFF4CAF50)
                    "WARNING" -> Color(0xFFFF9800)
                    "FAILED" -> Color(0xFFFF5722)
                    else -> Color(0xFFAAAAAA)
                }

                Text(
                    analysis.status,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = statusColor
                )
                Text(
                    "${analysis.score}%",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFFAAAAAA)
                )
                Text(
                    analysis.timestamp,
                    style = MaterialTheme.typography.labelSmall,
                    color = Color(0xFFAAAAAA)
                )
            }
        }
    }
}
