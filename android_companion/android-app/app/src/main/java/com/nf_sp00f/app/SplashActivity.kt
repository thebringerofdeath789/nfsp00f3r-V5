package com.nf_sp00f.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay

class SplashActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            SplashScreen {
                startActivity(Intent(this, MainActivity::class.java))
                finish()
            }
        }
    }
}

@Composable
fun SplashScreen(onComplete: () -> Unit = {}) {
    var currentStatus by remember { mutableStateOf("Initializing EMV Platform") }
    var progress by remember { mutableFloatStateOf(0f) }
    
    val infiniteTransition = rememberInfiniteTransition(label = "loading")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "rotation"
    )
    
    val animatedProgress by animateFloatAsState(
        targetValue = progress,
        animationSpec = tween(durationMillis = 500),
        label = "progress"
    )
    
    LaunchedEffect(Unit) {
        val statusMessages = listOf(
            "Initializing EMV Platform" to 0.1f,
            "Loading NFC Subsystem" to 0.3f,
            "Initializing PN532 Support" to 0.5f,
            "Loading EMV Profiles" to 0.7f,
            "Preparing Security Engine" to 0.9f,
            "System Ready" to 1.0f
        )
        
        statusMessages.forEach { (message, targetProgress) ->
            currentStatus = message
            progress = targetProgress
            delay(800)
        }
        
        delay(500)
        onComplete()
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Image(
            painter = painterResource(id = R.drawable.nfspoof_logo),
            contentDescription = "nf-sp00f Logo",
            modifier = Modifier.size(120.dp),
            contentScale = ContentScale.Fit
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Text(
            text = "nf-sp00f",
            color = Color(0xFF4CAF50),
            fontSize = 36.sp,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "NFC PhreaK BoX",
            color = Color(0xFF4CAF50),
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(modifier = Modifier.height(12.dp))
        
        Text(
            text = "RFiD TooLKiT",
            color = Color.White,
            fontSize = 18.sp,
            textDecoration = TextDecoration.Underline
        )
        
        Spacer(modifier = Modifier.height(48.dp))
        
        Box(
            modifier = Modifier.size(60.dp),
            contentAlignment = Alignment.Center
        ) {
            CircularProgressIndicator(
                progress = animatedProgress,
                modifier = Modifier.size(60.dp),
                color = Color(0xFF4CAF50),
                strokeWidth = 4.dp,
                trackColor = Color(0xFF2E7D32)
            )
            
            if (progress < 1.0f) {
                CircularProgressIndicator(
                    modifier = Modifier
                        .size(40.dp)
                        .rotate(rotation),
                    color = Color(0xFF4CAF50).copy(alpha = 0.3f),
                    strokeWidth = 2.dp
                )
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = currentStatus,
            color = Color(0xFF4CAF50),
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "${(animatedProgress * 100).toInt()}%",
            color = Color(0xFF4CAF50).copy(alpha = 0.7f),
            fontSize = 14.sp
        )
        
        Spacer(modifier = Modifier.height(64.dp))
        
        Text(
            text = "Advanced EMV Security Research Platform",
            color = Color.Gray,
            fontSize = 12.sp
        )
    }
}

@Preview(showBackground = true)
@Composable
fun SplashScreenPreview() {
    SplashScreen()
}
