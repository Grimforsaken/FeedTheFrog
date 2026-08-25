#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_tap_game.py <MainActivity.kt>")

path = Path(sys.argv[1])
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"patch failed: {label}")
    text = text.replace(old, new, 1)


replace_once(
    "import androidx.compose.foundation.gestures.detectDragGestures",
    "import androidx.compose.foundation.gestures.detectTapGestures",
    "gesture import",
)

replace_once(
    "private val RANGE_REACH_DP = intArrayOf(48, 66, 84, 102, 120, 138, 156)",
    "private val RANGE_REACH_DP = intArrayOf(48, 66, 84, 102, 120, 138, 156)\n"
    "private val CAPACITY_COSTS = intArrayOf(250, 600, 1_400, 3_000, 6_500, 13_000, 26_000)\n"
    "private const val TAP_CATCH_RADIUS_DP = 54",
    "capacity constants",
)

replace_once(
    '    var rangeLevel by remember { mutableIntStateOf(prefs.getInt("rangeLevel", 0).coerceIn(0, RANGE_COSTS.size)) }',
    '    var rangeLevel by remember { mutableIntStateOf(prefs.getInt("rangeLevel", 0).coerceIn(0, RANGE_COSTS.size)) }\n'
    '    var capacityLevel by remember { mutableIntStateOf(prefs.getInt("capacityLevel", 0).coerceIn(0, CAPACITY_COSTS.size)) }',
    "capacity state",
)

replace_once(
    "LaunchedEffect(coins, dieIndex, rangeLevel, secondDie, secondDieIndex, totalCaught, soundOn)",
    "LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, secondDie, secondDieIndex, totalCaught, soundOn)",
    "save effect key",
)

replace_once(
    '            .putInt("rangeLevel", rangeLevel)',
    '            .putInt("rangeLevel", rangeLevel)\n            .putInt("capacityLevel", capacityLevel)',
    "save capacity",
)

replace_once(
    "                    rangeLevel = rangeLevel,\n                    onFlyGrabbed = { audio.playGrab() },\n                    onTongueSnap = { audio.playTongue() },",
    "                    rangeLevel = rangeLevel,\n                    catchCapacity = capacityLevel + 1,\n                    onTongueSnap = { audio.playTongue() },",
    "game board arguments",
)

replace_once(
    '                            "A new swarm is out. Drag bugs close to the frog\'s tongue."',
    '                            "A new swarm is out. Tap bugs inside the frog\'s tongue range."',
    "roll instruction",
)

replace_once(
    "                    rangeLevel = rangeLevel,\n                    secondDie = secondDie,",
    "                    rangeLevel = rangeLevel,\n                    capacityLevel = capacityLevel,\n                    secondDie = secondDie,",
    "shop capacity argument",
)

range_buy = '''                    onBuyRange = {
                        if (rangeLevel < RANGE_COSTS.size) {
                            val cost = RANGE_COSTS[rangeLevel]
                            if (coins >= cost) {
                                coins -= cost
                                rangeLevel++
                                audio.playUpgrade()
                            }
                        }
                    },'''
capacity_buy = range_buy + '''
                    onBuyCapacity = {
                        if (capacityLevel < CAPACITY_COSTS.size) {
                            val cost = CAPACITY_COSTS[capacityLevel]
                            if (coins >= cost) {
                                coins -= cost
                                capacityLevel++
                                audio.playUpgrade()
                            }
                        }
                    },'''
replace_once(range_buy, capacity_buy, "capacity purchase callback")

replace_once(
    '                        Text("ROLL • DRAG • SNAP!", color = Color(0xFF9A6A00), fontWeight = FontWeight.Black, fontSize = 13.sp)',
    '                        Text("ROLL • TAP • SNAP!", color = Color(0xFF9A6A00), fontWeight = FontWeight.Black, fontSize = 13.sp)',
    "start slogan",
)
replace_once(
    '                    "Drag buzzing bugs close enough for the frog to strike.",',
    '                    "Tap a bug or nearby area inside the tongue ring to strike.",',
    "start instructions",
)

replace_once(
    "    rangeLevel: Int,\n    secondDie: Boolean,",
    "    rangeLevel: Int,\n    capacityLevel: Int,\n    secondDie: Boolean,",
    "shop signature capacity",
)
replace_once(
    "    onClose: () -> Unit,\n    onBuyRange: () -> Unit,\n    onBuyDie: () -> Unit,",
    "    onClose: () -> Unit,\n    onBuyRange: () -> Unit,\n    onBuyCapacity: () -> Unit,\n    onBuyDie: () -> Unit,",
    "shop callback signature",
)

range_card = '''                UpgradeRowCard(
                    icon = "👅",
                    title = "Tongue Distance",
                    levelText = "Level ${rangeLevel + 1} / ${RANGE_REACH_DP.size}",
                    currentText = "${RANGE_REACH_DP[rangeLevel]} dp reach",
                    nextText = if (rangeMaxed) "Maximum reach" else "Next: ${RANGE_REACH_DP[rangeLevel + 1]} dp",
                    progress = rangeLevel.toFloat() / RANGE_COSTS.size.toFloat(),
                    cost = if (rangeMaxed) null else RANGE_COSTS[rangeLevel],
                    affordable = !rangeMaxed && coins >= RANGE_COSTS[rangeLevel],
                    buttonText = if (rangeMaxed) "MAXED" else "EXTEND",
                    onClick = onBuyRange
                )'''
capacity_card = range_card + '''

                val capacityMaxed = capacityLevel >= CAPACITY_COSTS.size
                UpgradeRowCard(
                    icon = "🎯",
                    title = "Catch Capacity",
                    levelText = "Level ${capacityLevel + 1} / ${CAPACITY_COSTS.size + 1}",
                    currentText = "Catch up to ${capacityLevel + 1} bug${if (capacityLevel == 0) "" else "s"} per strike",
                    nextText = if (capacityMaxed) "Maximum capacity" else "Next: catch up to ${capacityLevel + 2} bugs in the tapped area",
                    progress = capacityLevel.toFloat() / CAPACITY_COSTS.size.toFloat(),
                    cost = if (capacityMaxed) null else CAPACITY_COSTS[capacityLevel],
                    affordable = !capacityMaxed && coins >= CAPACITY_COSTS[capacityLevel],
                    buttonText = if (capacityMaxed) "MAXED" else "MORE BUGS",
                    onClick = onBuyCapacity
                )'''
replace_once(range_card, capacity_card, "capacity shop card")

new_board = r'''@Composable
private fun GameBoard(
    modifier: Modifier,
    flies: List<Fly>,
    rangeLevel: Int,
    catchCapacity: Int,
    onTongueSnap: () -> Unit,
    onFlyResolved: (Fly) -> Unit,
    onFlyMoved: (Int, Offset) -> Unit
) {
    val density = LocalDensity.current
    var boardSize by remember { mutableStateOf(IntSize.Zero) }
    var pendingCatchIds by remember { mutableStateOf<List<Int>>(emptyList()) }
    var tongueTarget by remember { mutableStateOf(Offset.Zero) }
    var strikeSerial by remember { mutableIntStateOf(0) }
    var strikeInProgress by remember { mutableStateOf(false) }
    val tongueProgress = remember { Animatable(0f) }

    val buzzTransition = rememberInfiniteTransition(label = "buzz")
    val buzzPhase by buzzTransition.animateFloat(
        initialValue = 0f,
        targetValue = (2f * PI).toFloat(),
        animationSpec = infiniteRepeatable(
            animation = tween(720, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "buzzPhase"
    )

    val catchRadiusPx = with(density) { RANGE_REACH_DP[rangeLevel].dp.toPx() }
    val tapCatchRadiusPx = with(density) { TAP_CATCH_RADIUS_DP.dp.toPx() }

    fun mouthPosition(): Offset = Offset(boardSize.width * 0.5f, boardSize.height * 0.70f)

    LaunchedEffect(boardSize, flies.size) {
        if (boardSize == IntSize.Zero) return@LaunchedEffect
        flies.toList().forEach { fly ->
            if (fly.position == Offset.Unspecified) {
                val x = Random.nextFloat() * boardSize.width * 0.76f + boardSize.width * 0.12f
                val y = Random.nextFloat() * boardSize.height * 0.40f + boardSize.height * 0.08f
                onFlyMoved(fly.id, Offset(x, y))
            }
        }
    }

    // Bugs roam continuously on their own. Bugs selected by a tongue strike pause
    // just long enough for the tongue animation to reach the tapped area.
    LaunchedEffect(boardSize, flies.size, pendingCatchIds) {
        if (boardSize == IntSize.Zero) return@LaunchedEffect
        var tick = 0f
        while (true) {
            delay(70)
            tick += 0.10f
            flies.toList().forEach { fly ->
                if (fly.position == Offset.Unspecified) return@forEach
                if (fly.id in pendingCatchIds) return@forEach

                val step = fly.type.wanderStep
                val phase = tick * fly.type.speedMultiplier + fly.buzzSeed
                val zig = when (fly.type) {
                    BugType.FAST_FLY -> sin(phase * 3.7f) * step * 1.5f
                    BugType.MOSQUITO -> sin(phase * 4.6f) * step
                    BugType.MOTH -> sin(phase * 0.7f) * step * 0.45f
                    else -> sin(phase * 1.5f) * step * 0.65f
                }

                var dx = cos(phase) * step + zig
                var dy = sin(phase * 1.12f) * step

                if (fly.type == BugType.BEE) {
                    dx = cos(phase * 0.72f) * step * 1.15f
                    dy = sin(phase * 0.72f) * step * 0.75f
                }
                if (fly.type == BugType.GOLDEN_FLY) {
                    dx += sin(phase * 2.8f) * 2.6f
                    dy += cos(phase * 2.3f) * 2.1f
                }

                val margin = 26f
                val newX = (fly.position.x + dx).coerceIn(margin, boardSize.width - margin)
                val newY = (fly.position.y + dy).coerceIn(margin, boardSize.height * 0.61f)
                onFlyMoved(fly.id, Offset(newX, newY))
            }
        }
    }

    LaunchedEffect(strikeSerial) {
        if (strikeSerial == 0) return@LaunchedEffect
        val caught = flies.filter { it.id in pendingCatchIds }
        tongueProgress.snapTo(0f)
        tongueProgress.animateTo(1f, tween(120))
        delay(75)
        caught.forEach { onFlyResolved(it) }
        tongueProgress.animateTo(0f, tween(155))
        pendingCatchIds = emptyList()
        strikeInProgress = false
    }

    Canvas(
        modifier = modifier
            .onSizeChanged { boardSize = it }
            .pointerInput(flies, catchRadiusPx, tapCatchRadiusPx, catchCapacity, strikeInProgress) {
                detectTapGestures { touch ->
                    if (strikeInProgress) return@detectTapGestures
                    val mouth = Offset(size.width * 0.5f, size.height * 0.70f)
                    if (distance(touch, mouth) > catchRadiusPx) return@detectTapGestures

                    val selected = flies
                        .filter { it.position != Offset.Unspecified && distance(it.position, touch) <= tapCatchRadiusPx }
                        .sortedBy { distance(it.position, touch) }
                        .take(catchCapacity.coerceAtLeast(1))

                    tongueTarget = touch
                    pendingCatchIds = selected.map { it.id }
                    strikeInProgress = true
                    strikeSerial++
                    onTongueSnap()
                }
            }
    ) {
        drawRect(PondLight)
        drawPondBackground()

        val mouth = Offset(size.width * 0.5f, size.height * 0.70f)
        drawCatchRing(mouth, catchRadiusPx, strikeInProgress)
        drawFrog(mouth)

        if (strikeInProgress) {
            drawCircle(
                color = Gold.copy(alpha = 0.34f),
                radius = tapCatchRadiusPx,
                center = tongueTarget,
                style = Stroke(width = 3f)
            )
            val end = Offset(
                mouth.x + (tongueTarget.x - mouth.x) * tongueProgress.value,
                mouth.y + (tongueTarget.y - mouth.y) * tongueProgress.value
            )
            drawLine(Tongue, mouth, end, strokeWidth = 16f, cap = androidx.compose.ui.graphics.StrokeCap.Round)
            drawCircle(Tongue, radius = 11f, center = end)
        }

        flies.forEach { fly ->
            if (fly.position == Offset.Unspecified || fly.id in pendingCatchIds) return@forEach
            val phase = buzzPhase * fly.type.speedMultiplier + fly.buzzSeed
            val amp = fly.type.movementAmplitude
            val buzz = Offset(cos(phase) * amp, sin(phase * 1.6f) * (amp * 0.68f))
            val center = fly.position + buzz
            val highlightColor = if (fly.type == BugType.GOLDEN_FLY) Gold.copy(alpha = 0.20f) else Color.White.copy(alpha = 0.18f)
            drawCircle(highlightColor, 24f * fly.type.scale, center)
            drawBug(center, fly.type, 1f)
        }

        if (flies.isEmpty()) {
            val bannerWidth = size.width * 0.68f
            drawRoundRect(
                color = Color.White.copy(alpha = 0.88f),
                topLeft = Offset((size.width - bannerWidth) / 2f, size.height * 0.08f),
                size = Size(bannerWidth, 60f),
                cornerRadius = CornerRadius(20f, 20f)
            )
        }
    }
}
'''

pattern = re.compile(
    r'@Composable\nprivate fun GameBoard\(.*?\n\}\n\nprivate fun DrawScope\.drawPondBackground\(\)',
    re.S,
)
match = pattern.search(text)
if not match:
    raise SystemExit("patch failed: GameBoard block")
text = text[:match.start()] + new_board + "\nprivate fun DrawScope.drawPondBackground()" + text[match.end():]

old_ring = '''private fun DrawScope.drawCatchRing(center: Offset, radius: Float, active: Boolean) {
    if (!active) return
    drawCircle(color = Gold.copy(alpha = 0.18f), radius = radius, center = center)
    drawCircle(color = Gold.copy(alpha = 0.88f), radius = radius, center = center, style = Stroke(width = 5f))
}'''
new_ring = '''private fun DrawScope.drawCatchRing(center: Offset, radius: Float, active: Boolean) {
    drawCircle(color = Gold.copy(alpha = if (active) 0.16f else 0.055f), radius = radius, center = center)
    drawCircle(
        color = Gold.copy(alpha = if (active) 0.90f else 0.42f),
        radius = radius,
        center = center,
        style = Stroke(width = if (active) 5f else 3f)
    )
}'''
replace_once(old_ring, new_ring, "range ring")

path.write_text(text)
print(f"patched tap-to-feed gameplay in {path}")
