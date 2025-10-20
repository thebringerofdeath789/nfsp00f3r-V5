package com.nf_sp00f.app.ui.screens
import com.nf_sp00f.app.R

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nf_sp00f.app.data.DatabaseCard

@Composable
fun databaseScreen() {
    var searchText by remember { mutableStateOf("") }
    var selectedFilter by remember { mutableStateOf("All") }
    var showAddCardDialog by remember { mutableStateOf(false) }

    val databaseCards = listOf(
        DatabaseCard("JOHN DOE", "4154 **** **** 3556", "02/29", 47, "VISA", "Real", true, "2h ago"),
        DatabaseCard("TEST CARD", "4000 **** **** 0002", "12/25", 12, "VISA", "Test", false, "1d ago"),
        DatabaseCard("ALICE CRYPTO", "5555 **** **** 4444", "06/27", 156, "MC", "Attack", true, "5m ago"),
        DatabaseCard("BOB RESEARCH", "3782 **** **** 1007", "03/28", 89, "AMEX", "Real", true, "1h ago"),
        DatabaseCard("FUZZER PROFILE", "6011 **** **** 0004", "09/26", 234, "DISC", "Attack", false, "30m ago"),
        DatabaseCard("JANE SMITH", "4111 **** **** 1111", "11/29", 67, "VISA", "Test", true, "3h ago")
    )

    val filteredCards = if (selectedFilter == "All") {
        databaseCards.filter {
            it.cardholderName.contains(searchText, ignoreCase = true) ||
            it.pan.contains(searchText, ignoreCase = true)
        }
    } else {
        databaseCards.filter {
            it.category == selectedFilter &&
            (it.cardholderName.contains(searchText, ignoreCase = true) ||
             it.pan.contains(searchText, ignoreCase = true))
        }
    }

    Column(
        modifier = Modifier.fillMaxSize()
            .background(Brush.verticalGradient(colors = listOf(Color(0xFF0F0F0F), Color(0xFF1A1A1A), Color(0xFF0F0F0F))))
            .padding(16.dp)
    ) {
        // Header with nfspoof background
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
                        "CARD DATABASE",
                        style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Bold),
                        color = Color(0xFF4CAF50),
                        textAlign = TextAlign.Center
                    )
                    Text(
                        "EMV Security Research Archive",
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

        // Search and Filter Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Search Field
            OutlinedTextField(
                value = searchText,
                onValueChange = { searchText = it },
                label = { Text("Search cards...", color = Color(0xFF4CAF50)) },
                leadingIcon = {
                    Icon(
                        Icons.Default.Search,
                        contentDescription = null,
                        tint = Color(0xFF4CAF50)
                    )
                },
                modifier = Modifier.weight(1f),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF4CAF50),
                    unfocusedBorderColor = Color(0xFF4CAF50).copy(alpha = 0.5f),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                )
            )

            // Filter Dropdown
            var expanded by remember { mutableStateOf(false) }
            val filters = listOf("All", "Real", "Test", "Attack")

            Box {
                OutlinedButton(
                    onClick = { expanded = true },
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF4CAF50)),
                    border = BorderStroke(1.dp, Color(0xFF4CAF50))
                ) {
                    Text(selectedFilter)
                    Icon(Icons.Default.ArrowDropDown, contentDescription = null)
                }

                DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    filters.forEach { filter ->
                        DropdownMenuItem(
                            text = { Text(filter, color = Color.White) },
                            onClick = {
                                selectedFilter = filter
                                expanded = false
                            }
                        )
                    }
                }
            }

            // Add Card Button
            Button(
                onClick = { showAddCardDialog = true },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4CAF50))
            ) {
                Icon(Icons.Default.Add, contentDescription = null)
                Text("Add Card", color = Color.Black)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Statistics Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            DatabaseStatCard("Total Cards", databaseCards.size.toString(), Icons.Default.CreditCard, Modifier.weight(1f))
            DatabaseStatCard("Encrypted", databaseCards.count { it.isEncrypted }.toString(), Icons.Default.Security, Modifier.weight(1f))
            DatabaseStatCard("Categories", databaseCards.map { it.category }.distinct().size.toString(), Icons.Default.Category, Modifier.weight(1f))
            DatabaseStatCard("Total APDUs", databaseCards.sumOf { it.apduCount }.toString(), Icons.Default.DataArray, Modifier.weight(1f))
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Cards Grid
        LazyVerticalGrid(
            columns = GridCells.Fixed(if (LocalConfiguration.current.screenWidthDp > 600) 2 else 1),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            items(filteredCards) { card ->
                DatabaseVirtualCard(
                    card = card,
                    onEdit = { /* Handle edit */ },
                    onClone = { /* Handle clone */ },
                    onDelete = { /* Handle delete */ },
                    onExport = { /* Handle export */ },
                    onViewHistory = { /* Handle view APDU history */ }
                )
            }
        }
    }

    // Add Card Dialog
    if (showAddCardDialog) {
        AlertDialog(
            onDismissRequest = { showAddCardDialog = false },
            title = { Text("Add New Card", color = Color.White) },
            text = { Text("Card creation dialog would go here", color = Color.White) },
            confirmButton = {
                TextButton(onClick = { showAddCardDialog = false }) {
                    Text("OK", color = Color(0xFF4CAF50))
                }
            }
        )
    }
}

@Composable
fun DatabaseStatCard(
    title: String,
    value: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = Color(0xFF4CAF50),
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                value,
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
                color = Color(0xFF4CAF50)
            )
            Text(
                title,
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFFAAAAAA),
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
fun DatabaseVirtualCard(
    card: DatabaseCard,
    onEdit: () -> Unit,
    onClone: () -> Unit,
    onDelete: () -> Unit,
    onExport: () -> Unit,
    onViewHistory: () -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth().height(200.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF121717)),
        shape = RoundedCornerShape(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Background logo
            Image(
                painter = painterResource(id = R.drawable.nfspoof_logo),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize(),
                alpha = 0.1f
            )

            // Card content
            Column(
                modifier = Modifier.padding(16.dp).fillMaxSize(),
                verticalArrangement = Arrangement.SpaceBetween
            ) {
                // Header with menu
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top
                ) {
                    Column {
                        Text(
                            card.cardType,
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                            color = Color(0xFF4CAF50)
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            // Category badge
                            val categoryColor = when (card.category) {
                                "Real" -> Color(0xFF4CAF50)
                                "Test" -> Color(0xFF2196F3)
                                "Attack" -> Color(0xFFFF5722)
                                else -> Color(0xFF9E9E9E)
                            }
                            Box(
                                modifier = Modifier.background(categoryColor, RoundedCornerShape(4.dp))
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    card.category,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Color.White
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            if (card.isEncrypted) {
                                Icon(
                                    Icons.Default.Security,
                                    contentDescription = "Encrypted",
                                    tint = Color(0xFF4CAF50),
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                        }
                    }

                    // Menu button
                    Box {
                        IconButton(onClick = { showMenu = true }) {
                            Icon(
                                Icons.Default.MoreVert,
                                contentDescription = "Menu",
                                tint = Color(0xFF4CAF50)
                            )
                        }

                        DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                            DropdownMenuItem(
                                text = { Text("Edit", color = Color.White) },
                                leadingIcon = { Icon(Icons.Default.Edit, contentDescription = null, tint = Color(0xFF4CAF50)) },
                                onClick = { onEdit(); showMenu = false }
                            )
                            DropdownMenuItem(
                                text = { Text("Clone", color = Color.White) },
                                leadingIcon = { Icon(Icons.Default.ContentCopy, contentDescription = null, tint = Color(0xFF4CAF50)) },
                                onClick = { onClone(); showMenu = false }
                            )
                            DropdownMenuItem(
                                text = { Text("APDU History", color = Color.White) },
                                leadingIcon = { Icon(Icons.Default.History, contentDescription = null, tint = Color(0xFF4CAF50)) },
                                onClick = { onViewHistory(); showMenu = false }
                            )
                            DropdownMenuItem(
                                text = { Text("Export", color = Color.White) },
                                leadingIcon = { Icon(Icons.Default.FileDownload, contentDescription = null, tint = Color(0xFF4CAF50)) },
                                onClick = { onExport(); showMenu = false }
                            )
                            DropdownMenuItem(
                                text = { Text("Delete", color = Color(0xFFFF5722)) },
                                leadingIcon = { Icon(Icons.Default.Delete, contentDescription = null, tint = Color(0xFFFF5722)) },
                                onClick = { onDelete(); showMenu = false }
                            )
                        }
                    }
                }

                // Card details
                Column {
                    Text(
                        card.cardholderName,
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = Color.White
                    )
                    Text(
                        card.pan,
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 2.sp
                        ),
                        color = Color(0xFF4CAF50)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(
                                "EXP",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color(0xFFAAAAAA)
                            )
                            Text(
                                card.expiry,
                                style = MaterialTheme.typography.bodyMedium,
                                color = Color.White
                            )
                        }

                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                "${card.apduCount} APDUs",
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
                                color = Color(0xFF4CAF50)
                            )
                            Text(
                                "Last used: ${card.lastUsed}",
                                style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFFAAAAAA)
                            )
                        }
                    }
                }
            }
        }
    }
}
