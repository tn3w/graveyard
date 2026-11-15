package com.tn3w.novi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.tn3w.novi.ui.components.BottomNavBar
import com.tn3w.novi.ui.screens.NowPlayingScreen
import com.tn3w.novi.ui.components.NowPlayingTrack
import com.tn3w.novi.ui.screens.HomeScreen
import com.tn3w.novi.ui.theme.NoviTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            NoviTheme {
                var selectedIndex by remember { mutableIntStateOf(0) }
                var playerExpanded by remember {
                    mutableStateOf(false)
                }

                val nowPlaying = NowPlayingTrack(
                    title = "Midnight Drive (feat. Luna Ray)",
                    artist = "Neon Pulse",
                    color = Color(0xFF1A3A5A),
                    playlistName = "Daily Mix 1",
                )

                Surface(modifier = Modifier.fillMaxSize()) {
                    Box(modifier = Modifier.fillMaxSize()) {
                        HomeScreen()

                        AnimatedVisibility(
                            visible = !playerExpanded,
                            enter = fadeIn() + slideInVertically {
                                it / 2
                            },
                            exit = fadeOut() + slideOutVertically {
                                it / 2
                            },
                            modifier = Modifier
                                .align(Alignment.BottomCenter),
                        ) {
                            BottomNavBar(
                                selectedIndex = selectedIndex,
                                onSelect = { selectedIndex = it },
                            )
                        }

                        NowPlayingScreen(
                            track = nowPlaying,
                            expanded = playerExpanded,
                            onExpandedChange = {
                                playerExpanded = it
                            },
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .navigationBarsPadding()
                                .padding(bottom = 80.dp),
                        )
                    }
                }
            }
        }
    }
}
