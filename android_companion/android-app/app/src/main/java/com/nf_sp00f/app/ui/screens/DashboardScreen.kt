package com.nf_sp00f.app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nf_sp00f.app.R
import com.nf_sp00f.app.data.VirtualCard
import androidx.compose.ui.graphics.vector.ImageVector

@Composable
fun dashboardScreen(
    virtualCards: List<VirtualCard>,
    onNavigateToRead: () -> Unit,
    onNavigateToEmulate: () -> Unit,
    onNavigateToDatabase: () -> Unit,
    onNavigateToAnalysis: () -> Unit
) {
    var systemStatus by remember { mutableStateOf("🟢 OPERATIONAL") }
    var nfcStatus by remember { mutableStateOf("NFC: READY") }
    var emulationStatus by remember { mutableStateOf("HCE: STANDBY") }

    val sampleCards = remember {
        listOf(
            VirtualCard("ALICE JOHNSON", "4154 **** **** 3556", "02/29", 47, "VISA"),
            VirtualCard("BOB SMITH", "5555 **** **** 4444", "12/28", 23, "MASTERCARD"),
            VirtualCard("CAROL WILSON", "3782 **** **** 1007", "05/27", 89, "AMEX")
        )
    }

    val totalCards by remember { mutableStateOf(sampleCards.size) }
    val activeSessions by remember { mutableStateOf(2) }
    val successRate by remember { mutableStateOf(94.2f) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Box(modifier = Modifier.fillMaxSize()) {
                    Image(
                        painter = painterResource(id = R.drawable.nfspoof_logo),
                        contentDescription = "System Status Background",
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop
                    )

                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(
                                Brush.verticalGradient(
                                    colors = listOf(
                                        Color.Black.copy(alpha = 0.3f),
                                        Color.Black.copy(alpha = 0.7f)
                                    )
                                )
                            )
                    )

                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(20.dp),
                        verticalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(
                                text = "nf-sp00f",
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF00FF00)
                            )
                            Text(
                                text = "NFC PhreaK BoX",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color.White,
                                textDecoration = TextDecoration.Underline
                            )
                        }

                        Column {
                            Text(
                                text = systemStatus,
                                fontSize = 16.sp,
                                color = Color.White,
                                fontWeight = FontWeight.Medium
                            )
                            Text(
                                text = nfcStatus,
                                fontSize = 14.sp,
                                color = Color(0xFF00FF00)
                            )
                            Text(
                                text = emulationStatus,
                                fontSize = 14.sp,
                                color = Color(0xFFFFAA00)
                            )
                        }
                    }
                }
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                StatCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.CreditCard,
                    value = totalCards.toString(),
                    label = "Total Cards"
                )
                StatCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.Wifi,
                    value = activeSessions.toString(),
                    label = "Active Sessions"
                )
                StatCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.CheckCircle,
                    value = "${successRate}%",
                    label = "Success Rate"
                )
            }
        }

        item {
            Text(
                text = "Recent Virtual Cards",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF00FF00),
                modifier = Modifier.padding(vertical = 8.dp)
            )
        }

        items(sampleCards) { card ->
            VirtualCardItem(
                card = card,
                modifier = Modifier.fillMaxWidth(0.5f)
            )
        }

        if (sampleCards.isEmpty()) {
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth(0.5f)
                        .height(120.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A))
                ) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No cards in database\nTap READ to capture EMV data",
                            color = Color.Gray,
                            textAlign = TextAlign.Center,
                            fontSize = 14.sp
                        )
                    }
                }
            }
        }
    }

    // Local composables moved to top-level to avoid inline-lambda resolution issues
}

@Composable
fun StatCard(
    modifier: Modifier = Modifier,
    icon: ImageVector,
    value: String,
    label: String
) {
    Card(
        modifier = modifier.height(100.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A1A))
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = Color(0xFF00FF00),
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Text(
                text = label,
                color = Color.Gray,
                fontSize = 10.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
fun VirtualCardItem(
    card: VirtualCard,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.height(120.dp),
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Image(
                painter = painterResource(id = R.drawable.nfspoof_logo),
                contentDescription = "Card Background",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                contentAlignment = Alignment.TopStart
            ) {
                Text(
                    text = card.cardType,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                contentAlignment = Alignment.BottomStart
            ) {
                Column {
                    Text(
                        text = card.cardholderName,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "**** **** **** ${card.pan.takeLast(4)}",
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                contentAlignment = Alignment.BottomEnd
            ) {
                Text(
                    text = card.expiry,
                    color = Color.White,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
