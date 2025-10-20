package com.nf_sp00f.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

@Composable
fun nfSp00fTheme(content: @Composable () -> Unit) {
        MaterialTheme(
                colorScheme =
                        darkColorScheme(
                                primary = Color(0xFF4CAF50),
                                secondary = Color(0xFF4CAF50),
                                background = Color.Black,
                                surface = Color(0xFF1E1E1E),
                                onSurface = Color(0xFF4CAF50),
                                onBackground = Color(0xFF4CAF50),
                                surfaceVariant = Color(0xFF2D2D2D),
                                onSurfaceVariant = Color(0xFF4CAF50)
                        ),
                typography =
                        Typography(
                                // Headlines: Roboto Medium 24sp/20sp
                                headlineLarge =
                                        MaterialTheme.typography.headlineLarge.copy(
                                                fontWeight = FontWeight.Medium,
                                                fontSize = 24.sp,
                                                lineHeight = 32.sp,
                                                letterSpacing = 0.sp
                                        ),
                                headlineMedium =
                                        MaterialTheme.typography.headlineMedium.copy(
                                                fontWeight = FontWeight.Medium,
                                                fontSize = 20.sp,
                                                lineHeight = 28.sp,
                                                letterSpacing = 0.sp
                                        ),
                                // Titles: Roboto Regular 18sp/16sp
                                titleLarge =
                                        MaterialTheme.typography.titleLarge.copy(
                                                fontWeight = FontWeight.Normal,
                                                fontSize = 18.sp,
                                                lineHeight = 24.sp,
                                                letterSpacing = 0.sp
                                        ),
                                titleMedium =
                                        MaterialTheme.typography.titleMedium.copy(
                                                fontWeight = FontWeight.Normal,
                                                fontSize = 16.sp,
                                                lineHeight = 22.sp,
                                                letterSpacing = 0.15.sp
                                        ),
                                // Body: Roboto Regular 14sp
                                bodyLarge =
                                        MaterialTheme.typography.bodyLarge.copy(
                                                fontWeight = FontWeight.Normal,
                                                fontSize = 14.sp,
                                                lineHeight = 20.sp,
                                                letterSpacing = 0.25.sp
                                        ),
                                // Captions: Roboto Regular 12sp
                                labelSmall =
                                        MaterialTheme.typography.labelSmall.copy(
                                                fontWeight = FontWeight.Normal,
                                                fontSize = 12.sp,
                                                lineHeight = 16.sp,
                                                letterSpacing = 0.5.sp
                                        )
                        ),
                content = content
        )
}
