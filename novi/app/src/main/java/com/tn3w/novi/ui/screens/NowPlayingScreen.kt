package com.tn3w.novi.ui.screens

import com.tn3w.novi.ui.components.NowPlayingTrack
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.QueueMusic
import androidx.compose.material.icons.filled.AddCircleOutline
import androidx.compose.material.icons.filled.DevicesOther
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Lyrics
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Repeat
import androidx.compose.material.icons.filled.RepeatOne
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.lerp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.util.lerp

@Composable
fun NowPlayingScreen(
    track: NowPlayingTrack,
    expanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val expansion by animateFloatAsState(
        targetValue = if (expanded) 1f else 0f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy,
            stiffness = Spring.StiffnessMedium,
        ),
        label = "expansion",
    )

    if (!expanded) {
        CollapsedBar(
            track = track,
            onTap = { onExpandedChange(true) },
            modifier = modifier,
        )
        return
    }

    ExpandedPlayer(
        track = track,
        expansion = expansion,
        onCollapse = { onExpandedChange(false) },
    )
}

@Composable
private fun CollapsedBar(
    track: NowPlayingTrack,
    onTap: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var isPlaying by remember { mutableStateOf(true) }
    var progress by remember { mutableFloatStateOf(0.35f) }
    var barWidth by remember { mutableFloatStateOf(0f) }

    val background = track.color.copy(alpha = 1f)

    Box(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(background)
            .clickable(
                interactionSource = remember {
                    MutableInteractionSource()
                },
                indication = null,
                onClick = onTap,
            ),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = 8.dp,
                    top = 8.dp,
                    end = 4.dp,
                    bottom = 8.dp,
                ),
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(track.color.copy(alpha = 0.5f)),
            )

            Spacer(Modifier.width(10.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = track.title,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = track.artist,
                    fontSize = 11.sp,
                    color = Color.White.copy(alpha = 0.6f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            IconButton(onClick = {}) {
                Icon(
                    imageVector = Icons.Filled.AddCircleOutline,
                    contentDescription = "Add to library",
                    tint = Color.White,
                    modifier = Modifier.size(22.dp),
                )
            }

            IconButton(onClick = { isPlaying = !isPlaying }) {
                Icon(
                    imageVector = if (isPlaying)
                        Icons.Filled.Pause else Icons.Filled.PlayArrow,
                    contentDescription =
                        if (isPlaying) "Pause" else "Play",
                    tint = Color.White,
                    modifier = Modifier.size(26.dp),
                )
            }
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(3.dp)
                .align(Alignment.BottomStart)
                .onSizeChanged { barWidth = it.width.toFloat() }
                .pointerInput(Unit) {
                    detectTapGestures { offset ->
                        if (barWidth > 0f) {
                            progress =
                                (offset.x / barWidth).coerceIn(0f, 1f)
                        }
                    }
                }
                .pointerInput(Unit) {
                    detectHorizontalDragGestures { change, _ ->
                        if (barWidth > 0f) {
                            progress = (change.position.x / barWidth)
                                .coerceIn(0f, 1f)
                        }
                    }
                },
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(3.dp)
                    .background(Color.White.copy(alpha = 0.25f)),
            )
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress)
                    .height(3.dp)
                    .background(Color.White),
            )
        }
    }
}

@Composable
private fun ExpandedPlayer(
    track: NowPlayingTrack,
    expansion: Float,
    onCollapse: () -> Unit,
) {
    var isPlaying by remember { mutableStateOf(true) }
    var progress by remember { mutableFloatStateOf(0.35f) }
    var showTimeLeft by remember { mutableStateOf(false) }
    var repeatMode by remember { mutableIntStateOf(0) }
    var shuffleOn by remember { mutableStateOf(false) }

    val totalSeconds = 225
    val currentSeconds = (totalSeconds * progress).toInt()
    val remainingSeconds = totalSeconds - currentSeconds

    Box(
        modifier = Modifier
            .fillMaxSize()
            .graphicsLayer { alpha = expansion }
            .background(track.color)
            .statusBarsPadding()
            .navigationBarsPadding()
            .pointerInput(Unit) {
                detectVerticalDragGestures { _, dragAmount ->
                    if (dragAmount > 40f) onCollapse()
                }
            },
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(8.dp))

            TopBar(
                playlistName = track.playlistName,
                onCollapse = onCollapse,
            )

            Spacer(Modifier.height(24.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
                    .clip(RoundedCornerShape(12.dp))
                    .background(track.color.copy(alpha = 0.5f)),
            )

            Spacer(Modifier.height(28.dp))

            TrackInfo(track = track)

            Spacer(Modifier.height(20.dp))

            SeekBar(
                progress = progress,
                onProgressChange = { progress = it },
            )

            Spacer(Modifier.height(4.dp))

            TimeLabels(
                currentSeconds = currentSeconds,
                totalSeconds = totalSeconds,
                remainingSeconds = remainingSeconds,
                showTimeLeft = showTimeLeft,
                onToggleTimeDisplay = {
                    showTimeLeft = !showTimeLeft
                },
            )

            Spacer(Modifier.height(12.dp))

            PlaybackControls(
                isPlaying = isPlaying,
                shuffleOn = shuffleOn,
                repeatMode = repeatMode,
                onPlayPause = { isPlaying = !isPlaying },
                onShuffle = { shuffleOn = !shuffleOn },
                onRepeat = { repeatMode = (repeatMode + 1) % 3 },
                modifier = Modifier.padding(horizontal = 8.dp),
            )

            Spacer(Modifier.height(24.dp))

            BottomActions()

            Spacer(Modifier.weight(1f))
        }
    }
}

@Composable
private fun TopBar(
    playlistName: String,
    onCollapse: () -> Unit,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        IconButton(onClick = onCollapse) {
            Icon(
                imageVector = Icons.Filled.KeyboardArrowDown,
                contentDescription = "Collapse",
                tint = Color.White,
                modifier = Modifier.size(30.dp),
            )
        }

        Text(
            text = playlistName,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White.copy(alpha = 0.8f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )

        Spacer(Modifier.width(48.dp))
    }
}

@Composable
private fun TrackInfo(track: NowPlayingTrack) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = track.title,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = track.artist,
                fontSize = 16.sp,
                color = Color.White.copy(alpha = 0.7f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Filled.FavoriteBorder,
                contentDescription = "Like",
                tint = Color.White,
                modifier = Modifier.size(24.dp),
            )
        }

        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Filled.AddCircleOutline,
                contentDescription = "Add to library",
                tint = Color.White,
                modifier = Modifier.size(24.dp),
            )
        }
    }
}

@Composable
private fun SeekBar(
    progress: Float,
    onProgressChange: (Float) -> Unit,
) {
    Slider(
        value = progress,
        onValueChange = onProgressChange,
        modifier = Modifier.fillMaxWidth(),
        colors = SliderDefaults.colors(
            thumbColor = Color.White,
            activeTrackColor = Color.White,
            inactiveTrackColor = Color.White.copy(alpha = 0.3f),
        ),
    )
}

@Composable
private fun TimeLabels(
    currentSeconds: Int,
    totalSeconds: Int,
    remainingSeconds: Int,
    showTimeLeft: Boolean,
    onToggleTimeDisplay: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = formatTime(currentSeconds),
            fontSize = 12.sp,
            color = Color.White.copy(alpha = 0.7f),
        )

        Text(
            text = if (showTimeLeft) "-${formatTime(remainingSeconds)}"
            else formatTime(totalSeconds),
            fontSize = 12.sp,
            color = Color.White.copy(alpha = 0.7f),
            modifier = Modifier.clickable(
                interactionSource = remember {
                    MutableInteractionSource()
                },
                indication = null,
                onClick = onToggleTimeDisplay,
            ),
        )
    }
}

@Composable
private fun PlaybackControls(
    isPlaying: Boolean,
    shuffleOn: Boolean,
    repeatMode: Int,
    onPlayPause: () -> Unit,
    onShuffle: () -> Unit,
    onRepeat: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = modifier.fillMaxWidth(),
    ) {
        IconButton(onClick = onShuffle, modifier = Modifier.size(48.dp)) {
            Icon(
                imageVector = Icons.Filled.Shuffle,
                contentDescription = "Shuffle",
                tint = if (shuffleOn) Color.White
                else Color.White.copy(alpha = 0.5f),
                modifier = Modifier.size(28.dp),
            )
        }

        IconButton(onClick = {}, modifier = Modifier.size(48.dp)) {
            Icon(
                imageVector = Icons.Filled.SkipPrevious,
                contentDescription = "Previous",
                tint = Color.White,
                modifier = Modifier.size(36.dp),
            )
        }

        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(64.dp)
                .clip(CircleShape)
                .background(Color.White)
                .clickable(onClick = onPlayPause),
        ) {
            Icon(
                imageVector = if (isPlaying)
                    Icons.Filled.Pause else Icons.Filled.PlayArrow,
                contentDescription =
                    if (isPlaying) "Pause" else "Play",
                tint = Color.Black,
                modifier = Modifier.size(36.dp),
            )
        }

        IconButton(onClick = {}, modifier = Modifier.size(48.dp)) {
            Icon(
                imageVector = Icons.Filled.SkipNext,
                contentDescription = "Next",
                tint = Color.White,
                modifier = Modifier.size(36.dp),
            )
        }

        IconButton(onClick = onRepeat, modifier = Modifier.size(48.dp)) {
            Icon(
                imageVector = when (repeatMode) {
                    1 -> Icons.Filled.Repeat
                    2 -> Icons.Filled.RepeatOne
                    else -> Icons.Filled.Repeat
                },
                contentDescription = "Repeat",
                tint = if (repeatMode > 0) Color.White
                else Color.White.copy(alpha = 0.5f),
                modifier = Modifier.size(28.dp),
            )
        }
    }
}

@Composable
private fun BottomActions() {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceEvenly,
        modifier = Modifier.fillMaxWidth(),
    ) {
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Filled.DevicesOther,
                contentDescription = "Play on device",
                tint = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.size(22.dp),
            )
        }
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Filled.Share,
                contentDescription = "Share",
                tint = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.size(22.dp),
            )
        }
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Filled.Lyrics,
                contentDescription = "Lyrics",
                tint = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.size(22.dp),
            )
        }
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.QueueMusic,
                contentDescription = "Queue",
                tint = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.size(22.dp),
            )
        }
        IconButton(onClick = {}) {
            Icon(
                imageVector = Icons.Filled.MoreHoriz,
                contentDescription = "More",
                tint = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.size(22.dp),
            )
        }
    }
}

private fun formatTime(seconds: Int): String {
    val minutes = seconds / 60
    val secs = seconds % 60
    return "$minutes:${secs.toString().padStart(2, '0')}"
}
