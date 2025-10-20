package com.nf_sp00f.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nf_sp00f.app.hardware.NfcAdapterManager
import com.nf_sp00f.app.hardware.PermissionManager
import com.nf_sp00f.app.ui.screens.dashboardScreen
import com.nf_sp00f.app.ui.screens.cardReadingScreen
import com.nf_sp00f.app.ui.screens.emulationScreen
import com.nf_sp00f.app.ui.screens.databaseScreen
import com.nf_sp00f.app.ui.screens.analysisScreen

class MainActivity : ComponentActivity() {
    
    private lateinit var nfcAdapterManager: NfcAdapterManager
    private lateinit var permissionManager: PermissionManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize hardware managers
        permissionManager = PermissionManager(this)
        nfcAdapterManager = NfcAdapterManager(this)
        
        setContent { 
            NfSp00fTheme { 
                NfSp00fApp(
                    nfcAdapterManager = nfcAdapterManager,
                    permissionManager = permissionManager,
                    activity = this
                ) 
            } 
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        permissionManager.onPermissionResult(requestCode, permissions, grantResults)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        nfcAdapterManager.cleanup()
    }
}

@Composable
fun NfSp00fTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF4CAF50),
            secondary = Color(0xFF4CAF50),
            background = Color.Black,
            surface = Color(0xFF1E1E1E),
            onSurface = Color(0xFF4CAF50),
            onBackground = Color(0xFF4CAF50),
            surfaceVariant = Color(0xFF2D2D2D),
            onSurfaceVariant = Color(0xFF4CAF50)
        ),
        typography = Typography(
            headlineLarge = MaterialTheme.typography.headlineLarge.copy(
                fontWeight = FontWeight.Medium,
                fontSize = 24.sp,
                lineHeight = 32.sp,
                letterSpacing = 0.sp
            ),
            headlineMedium = MaterialTheme.typography.headlineMedium.copy(
                fontWeight = FontWeight.Medium,
                fontSize = 20.sp,
                lineHeight = 28.sp,
                letterSpacing = 0.sp
            ),
            titleLarge = MaterialTheme.typography.titleLarge.copy(
                fontWeight = FontWeight.Normal,
                fontSize = 18.sp,
                lineHeight = 24.sp,
                letterSpacing = 0.sp
            ),
            titleMedium = MaterialTheme.typography.titleMedium.copy(
                fontWeight = FontWeight.Normal,
                fontSize = 16.sp,
                lineHeight = 22.sp,
                letterSpacing = 0.15.sp
            ),
            bodyLarge = MaterialTheme.typography.bodyLarge.copy(
                fontWeight = FontWeight.Normal,
                fontSize = 14.sp,
                lineHeight = 20.sp,
                letterSpacing = 0.25.sp
            ),
            labelSmall = MaterialTheme.typography.labelSmall.copy(
                fontWeight = FontWeight.Normal,
                fontSize = 12.sp,
                lineHeight = 16.sp,
                letterSpacing = 0.5.sp
            )
        ),
        content = content
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NfSp00fApp(
    nfcAdapterManager: NfcAdapterManager,
    permissionManager: PermissionManager,
    activity: ComponentActivity
) {
    var selectedTab by rememberSaveable { mutableIntStateOf(0) }
    
    // Collect permission status
    val allPermissionsGranted by permissionManager.allPermissionsGranted.collectAsStateWithLifecycle()
    val systemReady = permissionManager.checkSystemReady()
    
    // Show permission request if needed
    LaunchedEffect(allPermissionsGranted) {
        if (!allPermissionsGranted) {
            permissionManager.requestMissingPermissions(activity)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            Icons.Default.Security,
                            contentDescription = "Security Shield",
                            tint = Color(0xFF4CAF50)
                        )
                        Text(
                            "nf-sp00f",
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF4CAF50)
                        )
                        
                        // System status indicator
                        Spacer(modifier = Modifier.weight(1f))
                        
                        if (systemReady.allReady) {
                            Icon(
                                Icons.Default.CheckCircle,
                                contentDescription = "System Ready",
                                tint = Color(0xFF4CAF50),
                                modifier = Modifier.size(20.dp)
                            )
                        } else {
                            Icon(
                                Icons.Default.Warning,
                                contentDescription = "System Not Ready",
                                tint = Color(0xFFFF9800),
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Black)
            )
        },
        bottomBar = {
            NavigationBar(containerColor = Color.Black) {
                val items = listOf(
                    "Dashboard" to Icons.Default.Dashboard,
                    "Read" to Icons.Default.Nfc,
                    "Emulate" to Icons.Default.Security,
                    "Database" to Icons.Default.Storage,
                    "Analysis" to Icons.Default.Analytics
                )

                items.forEachIndexed { index, (label, icon) ->
                    NavigationBarItem(
                        icon = {
                            Icon(
                                icon,
                                contentDescription = label,
                                tint = if (selectedTab == index) Color(0xFF4CAF50)
                                else Color(0xFF4CAF50).copy(alpha = 0.6f)
                            )
                        },
                        label = {
                            Text(
                                label,
                                color = if (selectedTab == index) Color(0xFF4CAF50)
                                else Color(0xFF4CAF50).copy(alpha = 0.6f),
                                fontWeight = if (selectedTab == index) FontWeight.Bold
                                else FontWeight.Normal
                            )
                        },
                        selected = selectedTab == index,
                        onClick = { selectedTab = index },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = Color(0xFF4CAF50),
                            unselectedIconColor = Color(0xFF4CAF50).copy(alpha = 0.6f),
                            selectedTextColor = Color(0xFF4CAF50),
                            unselectedTextColor = Color(0xFF4CAF50).copy(alpha = 0.6f),
                            indicatorColor = Color.Transparent
                        )
                    )
                }
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            when (selectedTab) {
                0 -> dashboardScreen(virtualCards = emptyList(), onNavigateToRead = { selectedTab = 1 }, onNavigateToEmulate = { selectedTab = 2 }, onNavigateToDatabase = { selectedTab = 3 }, onNavigateToAnalysis = { selectedTab = 4 })
                1 -> cardReadingScreen(
                    nfcAdapterManager = nfcAdapterManager,
                    permissionManager = permissionManager
                )
                2 -> emulationScreen()
                3 -> databaseScreen()
                4 -> analysisScreen()
            }
        }
    }
}
