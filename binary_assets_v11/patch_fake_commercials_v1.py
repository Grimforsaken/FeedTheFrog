#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_fake_commercials_v1.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'fake-commercial patch failed: {label}')
    text = text.replace(old, new, 1)

# Keep ad architecture independent of frog gameplay. The provider interface is
# intentionally tiny so FakeCommercialProvider can later be swapped for a real
# implementation without changing the game board or frog mechanics.
kotlin_dir = project_dir / 'app' / 'src' / 'main' / 'java' / 'com' / 'feedthefrog' / 'game'
kotlin_dir.mkdir(parents=True, exist_ok=True)
commercial_file = kotlin_dir / 'CommercialSystem.kt'
commercial_file.write_text(r'''package com.feedthefrog.game

enum class TvContentType(val legacyMode: Int) {
    COMMERCIAL_BREAK(0),
    POND_LOOP(1),
    LOOP_2(2),
    LOOP_3(3);

    companion object {
        fun fromPersisted(savedName: String?, legacyMode: Int): TvContentType {
            return values().firstOrNull { it.name == savedName }
                ?: values().firstOrNull { it.legacyMode == legacyMode }
                ?: COMMERCIAL_BREAK
        }
    }
}

data class TvContent(val type: TvContentType, val displayName: String) {
    companion object {
        val included: List<TvContent> = listOf(
            TvContent(TvContentType.COMMERCIAL_BREAK, "Commercial Break"),
            TvContent(TvContentType.POND_LOOP, "Pond Loop"),
            TvContent(TvContentType.LOOP_2, "Loop 2"),
            TvContent(TvContentType.LOOP_3, "Loop 3")
        )
    }
}

data class FakeCommercial(
    val id: String,
    val advertiserName: String,
    val headline: String,
    val detail: String,
    val durationMs: Long
)

interface CommercialProvider {
    fun commercials(): List<FakeCommercial>
}

class FakeCommercialProvider(private val defaultDurationMs: Long = 6_000L) : CommercialProvider {
    override fun commercials(): List<FakeCommercial> = listOf(
        FakeCommercial(
            id = "frog_cola",
            advertiserName = "Frog Cola",
            headline = "HOP. SIP. REPEAT.",
            detail = "The fizzy refreshment for long nights at the pond.",
            durationMs = defaultDurationMs
        ),
        FakeCommercial(
            id = "bug_burger",
            advertiserName = "Bug Burger",
            headline = "CATCH A BITE!",
            detail = "Now serving the Triple Fly Stack with extra crunch.",
            durationMs = defaultDurationMs
        ),
        FakeCommercial(
            id = "lily_pad_insurance",
            advertiserName = "Lily Pad Insurance",
            headline = "COVER YOUR PAD.",
            detail = "Protection from rain, ripples, and unexpected herons.",
            durationMs = defaultDurationMs
        )
    )
}

class CommercialBreakManager(private val provider: CommercialProvider) {
    private val items: List<FakeCommercial> = provider.commercials().also {
        require(it.isNotEmpty()) { "Commercial provider must supply at least one commercial" }
    }

    fun commercialAt(index: Int): FakeCommercial {
        val safeIndex = ((index % items.size) + items.size) % items.size
        return items[safeIndex]
    }

    fun nextIndex(index: Int): Int = (index + 1) % items.size
    fun firstIndex(): Int = 0
}
''')

# Shared protected-control geometry. Game taps return immediately in this area,
# and every generated/autonomous fly position is pushed outside it.
replace_once(
    'private const val TV_MODE_SKUNK = 3',
    '''private const val TV_MODE_SKUNK = 3
private const val PROTECTED_CONTROL_RIGHT_FRACTION = 0.46f
private const val PROTECTED_CONTROL_BOTTOM_FRACTION = 0.22f
private const val PROTECTED_CONTROL_PADDING_PX = 18f''',
    'protected control constants',
)

helper_marker = 'private data class Fly(\n'
helpers = r'''private fun isInProtectedControlArea(point: Offset, width: Float, height: Float): Boolean {
    if (width <= 0f || height <= 0f) return false
    return point.x <= width * PROTECTED_CONTROL_RIGHT_FRACTION &&
        point.y <= height * PROTECTED_CONTROL_BOTTOM_FRACTION
}

private fun keepFlyOutsideProtectedControls(position: Offset, boardSize: IntSize): Offset {
    if (boardSize == IntSize.Zero || position == Offset.Unspecified) return position
    val right = boardSize.width * PROTECTED_CONTROL_RIGHT_FRACTION
    val bottom = boardSize.height * PROTECTED_CONTROL_BOTTOM_FRACTION
    if (position.x > right || position.y > bottom) return position

    val pushRight = right - position.x
    val pushDown = bottom - position.y
    return if (pushRight <= pushDown) {
        Offset((right + PROTECTED_CONTROL_PADDING_PX).coerceAtMost(boardSize.width - 18f), position.y)
    } else {
        Offset(position.x, (bottom + PROTECTED_CONTROL_PADDING_PX).coerceAtMost(boardSize.height - 18f))
    }
}

'''
replace_once(helper_marker, helpers + helper_marker, 'protected control helpers')

old_state = '''    var subscriptionPurchased by remember { mutableStateOf(prefs.getBoolean("subscriptionPurchased", false)) }
    var tvMode by remember { mutableIntStateOf(prefs.getInt("tvMode", TV_MODE_COMMERCIAL).coerceIn(TV_MODE_COMMERCIAL, TV_MODE_SKUNK)) }'''
new_state = '''    var premiumOwned by remember {
        mutableStateOf(prefs.getBoolean("premiumOwned", prefs.getBoolean("subscriptionPurchased", false)))
    }
    var selectedTvContent by remember {
        mutableStateOf(
            TvContentType.fromPersisted(
                prefs.getString("selectedTvContent", null),
                prefs.getInt("tvMode", TV_MODE_COMMERCIAL)
            )
        )
    }
    val commercialBreakManager = remember {
        CommercialBreakManager(FakeCommercialProvider(defaultDurationMs = 6_000L))
    }
    var fakeCommercialIndex by remember { mutableIntStateOf(commercialBreakManager.firstIndex()) }
    val currentFakeCommercial = commercialBreakManager.commercialAt(fakeCommercialIndex)
    var showAdvertiserDialog by remember { mutableStateOf(false) }
    var showTvPicker by remember { mutableStateOf(false) }'''
replace_once(old_state, new_state, 'premium and TV state')

replace_once(
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, timerSkipUnlocked, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, timerSkipUnlocked, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, premiumOwned, selectedTvContent)',
    'save effect state keys',
)
replace_once(
    '''            .putBoolean("subscriptionPurchased", subscriptionPurchased)
            .putInt("tvMode", tvMode)''',
    '''            .putBoolean("premiumOwned", premiumOwned)
            .putString("selectedTvContent", selectedTvContent.name)
            .putBoolean("subscriptionPurchased", premiumOwned)
            .putInt("tvMode", selectedTvContent.legacyMode)''',
    'premium and TV persistence',
)

replace_once(
    '    DisposableEffect(audio) {',
    '''    LaunchedEffect(premiumOwned, selectedTvContent, fakeCommercialIndex) {
        val commercialBreakActive = !premiumOwned || selectedTvContent == TvContentType.COMMERCIAL_BREAK
        if (!commercialBreakActive) return@LaunchedEffect
        delay(currentFakeCommercial.durationMs)
        fakeCommercialIndex = commercialBreakManager.nextIndex(fakeCommercialIndex)
    }

    DisposableEffect(audio) {''',
    'commercial rotation effect',
)

game_surface_marker = '    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFFE9F6DB)) {'
dialogs = r'''    if (showAdvertiserDialog) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showAdvertiserDialog = false },
            title = { Text(currentFakeCommercial.advertiserName, fontWeight = FontWeight.Black) },
            text = {
                Column {
                    Text(currentFakeCommercial.headline, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text("Test advertiser link — no real website opened.")
                }
            },
            confirmButton = {
                Button(onClick = { showAdvertiserDialog = false }) { Text("CLOSE") }
            }
        )
    }

    if (showTvPicker && premiumOwned) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showTvPicker = false },
            title = { Text("Change TV", fontWeight = FontWeight.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    TvContent.included.forEach { content ->
                        Button(
                            onClick = {
                                selectedTvContent = content.type
                                if (content.type == TvContentType.COMMERCIAL_BREAK) {
                                    fakeCommercialIndex = commercialBreakManager.firstIndex()
                                }
                                showTvPicker = false
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (selectedTvContent == content.type) FrogDark else WoodDark
                            )
                        ) {
                            Text(content.displayName, color = Color.White, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = { showTvPicker = false }) { Text("CLOSE") }
            }
        )
    }

'''
replace_once(game_surface_marker, dialogs + game_surface_marker, 'local test dialogs')

old_call = '''                    subscriptionPurchased = subscriptionPurchased,
                    tvMode = tvMode,
                    onAdvertiser = { latestEvent = "Advertiser link will activate when a campaign is loaded." },
                    onPurchaseSubscription = {
                        subscriptionPurchased = true
                        tvMode = TV_MODE_POND_LIFE
                        latestEvent = "Subscription service unlocked for testing. Pond Life is now playing."
                    },
                    onSelectTvMode = { tvMode = it },'''
new_call = '''                    premiumOwned = premiumOwned,
                    selectedTvContent = selectedTvContent,
                    currentCommercial = currentFakeCommercial,
                    onAdvertiser = { showAdvertiserDialog = true },
                    onPurchaseSubscription = {
                        premiumOwned = true
                        selectedTvContent = TvContentType.POND_LOOP
                        latestEvent = "Subscription Service unlocked for testing. Pond Loop is now playing."
                    },
                    onOpenTvPicker = { showTvPicker = true },'''
replace_once(old_call, new_call, 'GameBoard commercial state call')

old_sig = '''    subscriptionPurchased: Boolean,
    tvMode: Int,
    onAdvertiser: () -> Unit,
    onPurchaseSubscription: () -> Unit,
    onSelectTvMode: (Int) -> Unit,'''
new_sig = '''    premiumOwned: Boolean,
    selectedTvContent: TvContentType,
    currentCommercial: FakeCommercial,
    onAdvertiser: () -> Unit,
    onPurchaseSubscription: () -> Unit,
    onOpenTvPicker: () -> Unit,'''
replace_once(old_sig, new_sig, 'GameBoard commercial state signature')

replace_once(
    '''        TvScreenLayer(
            subscriptionPurchased = subscriptionPurchased,
            tvMode = tvMode,
            modifier = Modifier.fillMaxSize()
        )''',
    '''        TvScreenLayer(
            premiumOwned = premiumOwned,
            selectedTvContent = selectedTvContent,
            currentCommercial = currentCommercial,
            modifier = Modifier.fillMaxSize()
        )''',
    'TV screen layer call',
)

tv_pattern = re.compile(
    r'@Composable\nprivate fun TvScreenLayer\(.*?\n\}\n\nprivate fun DrawScope\.drawPondBackground\(\)',
    re.S,
)
tv_replacement = r'''@Composable
private fun TvScreenLayer(
    premiumOwned: Boolean,
    selectedTvContent: TvContentType,
    currentCommercial: FakeCommercial,
    modifier: Modifier = Modifier
) {
    BoxWithConstraints(modifier) {
        val screenLeft = maxWidth * 0.083f
        val screenTop = maxHeight * 0.221f
        val screenWidth = maxWidth * 0.690f
        val screenHeight = maxHeight * 0.333f
        val screenModifier = Modifier
            .offset(x = screenLeft, y = screenTop)
            .size(width = screenWidth, height = screenHeight)

        val commercialBreakActive = !premiumOwned || selectedTvContent == TvContentType.COMMERCIAL_BREAK
        val videoRes = if (commercialBreakActive) null else when (selectedTvContent) {
            TvContentType.POND_LOOP -> R.raw.subscription_pond
            TvContentType.LOOP_2 -> R.raw.subscription_meadow
            TvContentType.LOOP_3 -> R.raw.subscription_skunk
            TvContentType.COMMERCIAL_BREAK -> null
        }

        if (videoRes != null) {
            AndroidView(
                factory = { context -> VideoView(context) },
                update = { view ->
                    if (view.tag != videoRes) {
                        view.tag = videoRes
                        view.setVideoURI(Uri.parse("android.resource://${view.context.packageName}/$videoRes"))
                        view.setOnPreparedListener { player ->
                            player.isLooping = true
                            player.setVolume(0f, 0f)
                            view.start()
                        }
                    } else if (!view.isPlaying) {
                        view.start()
                    }
                },
                modifier = screenModifier
            )
        } else {
            FakeCommercialScreen(currentCommercial, screenModifier)
        }
    }
}

@Composable
private fun FakeCommercialScreen(commercial: FakeCommercial, modifier: Modifier) {
    val adMotion = rememberInfiniteTransition(label = "fakeCommercialMotion")
    val pulse by adMotion.animateFloat(
        initialValue = 0.60f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(850, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "fakeCommercialPulse"
    )
    val background = when (commercial.id) {
        "frog_cola" -> Color(0xFF0C6570)
        "bug_burger" -> Color(0xFF8A2E17)
        else -> Color(0xFF315B2A)
    }
    val accent = when (commercial.id) {
        "frog_cola" -> Color(0xFFB7F4FF)
        "bug_burger" -> Color(0xFFFFD46A)
        else -> Color(0xFFD6FF99)
    }

    Surface(modifier = modifier, color = background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text("COMMERCIAL BREAK", color = Gold, fontWeight = FontWeight.Black, fontSize = 11.sp, textAlign = TextAlign.Center)
            Spacer(Modifier.height(4.dp))
            Text(commercial.advertiserName.uppercase(), color = accent.copy(alpha = pulse), fontWeight = FontWeight.Black, fontSize = 17.sp, textAlign = TextAlign.Center)
            Text(commercial.headline, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 11.sp, textAlign = TextAlign.Center)
            Text(commercial.detail, color = Color.White.copy(alpha = 0.88f), fontSize = 8.sp, textAlign = TextAlign.Center)
        }
    }
}

private fun DrawScope.drawPondBackground()'''
if not tv_pattern.search(text):
    raise SystemExit('fake-commercial patch failed: TvScreenLayer block')
text = tv_pattern.sub(tv_replacement, text, count=1)

controls_pattern = re.compile(
    r'''        Column\(\n            modifier = Modifier\n                \.align\(Alignment\.TopStart\)\n                \.padding\(start = 6\.dp, top = 6\.dp\),\n            horizontalAlignment = Alignment\.Start\n        \) \{\n            Button\(\n                onClick = onAdvertiser,.*?\n        \}\n    \}\n\}''',
    re.S,
)
controls_replacement = r'''        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(start = 6.dp, top = 6.dp)
                .background(WoodDark.copy(alpha = 0.24f), RoundedCornerShape(12.dp))
                .padding(4.dp),
            horizontalAlignment = Alignment.Start
        ) {
            Button(
                onClick = onAdvertiser,
                modifier = Modifier.height(34.dp),
                contentPadding = ButtonDefaults.ContentPadding,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = WoodDark.copy(alpha = 0.96f))
            ) {
                Text("VISIT ADVERTISER", color = Gold, fontWeight = FontWeight.Black, fontSize = 8.sp)
            }
            Spacer(Modifier.height(4.dp))
            Button(
                onClick = { if (!premiumOwned) onPurchaseSubscription() else onOpenTvPicker() },
                modifier = Modifier.height(36.dp),
                contentPadding = ButtonDefaults.ContentPadding,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = FrogDark.copy(alpha = 0.96f))
            ) {
                Text(
                    if (!premiumOwned) "SUBSCRIPTION SERVICE" else "CHANGE TV",
                    color = Color.White,
                    fontWeight = FontWeight.Black,
                    fontSize = 8.sp
                )
            }
        }
    }
}'''
text, controls_count = controls_pattern.subn(controls_replacement, text, count=1)
if controls_count != 1:
    raise SystemExit(f'fake-commercial patch failed: protected controls block (matches={controls_count})')

replace_once(
    '''                detectTapGestures { touch ->
                    if (strikeInProgress) return@detectTapGestures''',
    '''                detectTapGestures { touch ->
                    if (isInProtectedControlArea(touch, size.width.toFloat(), size.height.toFloat())) {
                        return@detectTapGestures
                    }
                    if (strikeInProgress) return@detectTapGestures''',
    'protected gameplay touch guard',
)

spawn_old = '''                onFlyMoved(
                    fly.id,
                    Offset(
                        x.coerceIn(28f, boardSize.width - 28f),
                        y.coerceIn(boardSize.height * 0.18f, boardSize.height * 0.64f)
                    )
                )'''
spawn_new = '''                onFlyMoved(
                    fly.id,
                    keepFlyOutsideProtectedControls(
                        Offset(
                            x.coerceIn(28f, boardSize.width - 28f),
                            y.coerceIn(boardSize.height * 0.18f, boardSize.height * 0.64f)
                        ),
                        boardSize
                    )
                )'''
replace_once(spawn_old, spawn_new, 'protected fly spawn')
replace_once(
    '                onFlyMoved(fly.id, Offset(newX, newY))',
    '                onFlyMoved(fly.id, keepFlyOutsideProtectedControls(Offset(newX, newY), boardSize))',
    'protected autonomous fly travel',
)

# Reorder visual layers to TV -> fly images -> tongue Canvas -> frog -> controls.
board_start = text.find('@Composable\nprivate fun GameBoard(')
board_end = text.find('\nprivate fun DrawScope.drawPondBackground()', board_start)
if board_start < 0 or board_end < 0:
    raise SystemExit('fake-commercial patch failed: GameBoard range for layer ordering')
board = text[board_start:board_end]
bug_pattern = re.compile(
    r'''        flies\.forEach \{ fly ->\n            if \(fly\.position != Offset\.Unspecified && fly\.id !in pendingCatchIds\) \{\n                val phase = buzzPhase.*?\n        \}\n\n(?=        Column\()''',
    re.S,
)
bug_match = bug_pattern.search(board)
if not bug_match:
    raise SystemExit('fake-commercial patch failed: Compose fly image layer')
bug_layer = bug_match.group(0)
board = board[:bug_match.start()] + board[bug_match.end():]
canvas_at = board.find('        Canvas(\n')
if canvas_at < 0:
    raise SystemExit('fake-commercial patch failed: Canvas layer marker')
board = board[:canvas_at] + bug_layer + board[canvas_at:]
text = text[:board_start] + board + text[board_end:]

app_gradle = project_dir / 'app' / 'build.gradle.kts'
gradle_text = app_gradle.read_text()
if 'versionCode = 18' not in gradle_text or 'versionName = "0.8.9-valid-home-png"' not in gradle_text:
    raise SystemExit('fake-commercial patch failed: expected v0.8.9 version values')
gradle_text = gradle_text.replace('versionCode = 18', 'versionCode = 19', 1)
gradle_text = gradle_text.replace('versionName = "0.8.9-valid-home-png"', 'versionName = "0.9.0-fake-commercials"', 1)
app_gradle.write_text(gradle_text)
main_file.write_text(text)

required_main = [
    'premiumOwned', 'selectedTvContent', 'CommercialBreakManager', 'FakeCommercialProvider',
    'FakeCommercialScreen', 'VISIT ADVERTISER', 'SUBSCRIPTION SERVICE', 'CHANGE TV',
    'Test advertiser link — no real website opened.', 'keepFlyOutsideProtectedControls',
    'isInProtectedControlArea'
]
for marker in required_main:
    if marker not in text:
        raise SystemExit(f'fake-commercial patch failed: missing marker {marker!r}')

arch_text = commercial_file.read_text()
for marker in [
    'Frog Cola', 'Bug Burger', 'Lily Pad Insurance', 'Commercial Break', 'Pond Loop',
    'Loop 2', 'Loop 3', 'interface CommercialProvider', 'class CommercialBreakManager',
    'class FakeCommercialProvider'
]:
    if marker not in arch_text:
        raise SystemExit(f'fake-commercial patch failed: missing architecture marker {marker!r}')

forbidden = ('play-services-ads', 'google mobile ads', 'admob', 'anzu', 'com.google.android.gms.ads')
scan = (text + '\n' + arch_text + '\n' + gradle_text).lower()
for marker in forbidden:
    if marker in scan:
        raise SystemExit(f'fake-commercial patch failed: real ad dependency/reference found: {marker}')

print('patched v0.9.0 fake commercial provider/manager, premium TV picker, protected controls, and gameplay-safe layering')
