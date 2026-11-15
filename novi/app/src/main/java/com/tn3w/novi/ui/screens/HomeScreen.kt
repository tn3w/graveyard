package com.tn3w.novi.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.MoreVert
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import com.tn3w.novi.ui.theme.DarkCard
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class MediaItem(val name: String, val artist: String? = null, val color: Color)

private data class Playlist(
    val name: String,
    val trackCount: Int,
    val description: String,
    val color: Color,
)

private data class Section(val title: String, val playlists: List<Playlist>)

private val quickItems = listOf(
    MediaItem("Summer Nights (feat...)", "Artist A", Color(0xFF3A3A5A)),
    MediaItem("Daily Mix 2", color = Color(0xFF2A4A3A)),
    MediaItem("Daily Mix 1", color = Color(0xFF4A3A2A)),
    MediaItem("City Lights", "Artist A", Color(0xFF2A3A5A)),
    MediaItem("Endless Road...", "Artist B", Color(0xFF3A2A4A)),
    MediaItem("Rock Mix", color = Color(0xFF5A2A2A)),
)

private val sections = listOf(
    Section(
        "Made For You",
        listOf(
            Playlist(
                "Discover Weekly",
                50,
                "Your weekly mixtape of fresh music.",
                Color(0xFF4A6A8A),
            ),
            Playlist(
                "Daily Mix 1",
                50,
                "Artist C, Artist D, Artist E and more",
                Color(0xFF3A5A3A),
            ),
            Playlist(
                "Daily Mix 2",
                42,
                "Artist F, Artist G, Artist H and more",
                Color(0xFF7A4A5A),
            ),
            Playlist(
                "Daily Mix 3",
                38,
                "Artist I, Artist J, Artist K and more",
                Color(0xFF5A4A2A),
            ),
        ),
    ),
    Section(
        "Recently Played",
        listOf(
            Playlist("Rock Mix", 30, "Classic rock anthems you love.", Color(0xFF6A3A3A)),
            Playlist("Chill Vibes", 25, "Relaxing beats for your downtime.", Color(0xFF3A4A6A)),
            Playlist("Top Hits", 40, "Today's biggest hits all in one place.", Color(0xFF5A5A3A)),
        ),
    ),
)

@Composable
fun HomeScreen() {
    val tabs = listOf("Music", "Podcasts", "Audiobooks")
    var selectedTab by remember { mutableIntStateOf(0) }
    var settingsActive by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .statusBarsPadding()
            .padding(horizontal = 16.dp),
    ) {
        TopMediaNav(
            tabs = tabs,
            selectedTab = selectedTab,
            onTabSelect = { selectedTab = it },
            settingsActive = settingsActive,
            onSettingsToggle = { settingsActive = !settingsActive },
        )

        Spacer(Modifier.height(8.dp))

        quickItems.chunked(2).forEach { row ->
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
            ) {
                row.forEach { item ->
                    MediaGridItem(item = item, modifier = Modifier.weight(1f))
                }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }

        Spacer(Modifier.height(24.dp))

        sections.forEach { section ->
            MediaSection(section = section)
            Spacer(Modifier.height(24.dp))
        }

        Spacer(Modifier.height(80.dp))
    }
}

@Composable
private fun TopMediaNav(
    tabs: List<String>,
    selectedTab: Int,
    onTabSelect: (Int) -> Unit,
    settingsActive: Boolean,
    onSettingsToggle: () -> Unit,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 12.dp),
    ) {
        Row(
            modifier = Modifier
                .weight(1f)
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            tabs.forEachIndexed { index, label ->
                val selected = index == selectedTab
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = DarkCard,
                    modifier = Modifier.clickable { onTabSelect(index) },
                ) {
                    Text(
                        text = label,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        color = if (selected) MaterialTheme.colorScheme.onSurface
                                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.45f),
                        fontSize = 14.sp,
                        fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                    )
                }
            }
        }
        // FIXME: should switch to Icons.Filled.Settings when settingsActive is true
        IconButton(onClick = onSettingsToggle) {
            Icon(
                imageVector = Icons.Outlined.Settings,
                contentDescription = "Settings",
                tint = if (settingsActive) MaterialTheme.colorScheme.primary
                       else MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}

@Composable
private fun MediaGridItem(item: MediaItem, modifier: Modifier = Modifier) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = DarkCard,
        modifier = modifier.height(56.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .padding(6.dp)
                    .size(44.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(item.color),
            )
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 10.dp),
                contentAlignment = Alignment.CenterStart,
            ) {
                Column {
                    Text(
                        text = item.name,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (item.artist != null) {
                        Text(
                            text = item.artist,
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MediaSection(section: Section) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = section.title,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f),
        )
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Outlined.MoreVert,
                contentDescription = "More",
                tint = MaterialTheme.colorScheme.onSurface,
            )
        }
    }

    Spacer(Modifier.height(12.dp))

    Row(
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
    ) {
        section.playlists.forEach { playlist ->
            PlaylistCard(playlist = playlist)
        }
    }
}

@Composable
private fun PlaylistCard(playlist: Playlist) {
    val cardWidth = 140.dp

    Column(modifier = Modifier.width(cardWidth)) {
        AlbumStackEffect(color = playlist.color, modifier = Modifier.fillMaxWidth())

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(cardWidth)
                .clip(RoundedCornerShape(bottomStart = 4.dp, bottomEnd = 4.dp))
                .background(
                    Brush.linearGradient(
                        colors = listOf(playlist.color, playlist.color.copy(alpha = 0.7f)),
                    ),
                ),
        )

        Spacer(Modifier.height(8.dp))

        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = playlist.name,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "${playlist.trackCount}",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = playlist.color,
            )
        }

        Text(
            text = playlist.description,
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            lineHeight = 15.sp,
        )
    }
}

@Composable
private fun AlbumStackEffect(color: Color, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        listOf(0.60f to 0.20f, 0.78f to 0.35f, 0.92f to 0.55f).forEach { (widthFraction, alpha) ->
            Box(
                modifier = Modifier
                    .fillMaxWidth(widthFraction)
                    .height(6.dp)
                    .clip(RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))
                    .background(color.copy(alpha = alpha)),
            )
        }
    }
}
