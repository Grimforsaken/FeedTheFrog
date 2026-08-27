#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_gameplay_v8.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'v8 patch failed: {label}')
    text = text.replace(old, new, 1)


def regex_once(pattern: str, replacement: str, label: str, flags=0) -> None:
    global text
    text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'v8 patch failed: {label} (matches={count})')

# ---------------------------------------------------------------------------
# Full replacement HOME screen art. The new supplied portrait already contains
# the frog and pond, so remove v7's extra frog sprite and place this image over
# the old decorative home Canvas while keeping the existing interactive UI.
# ---------------------------------------------------------------------------
home_src = repo_root / 'generated_assets_v11' / 'ftf_home_screen_v2.jpg'
if not home_src.exists():
    raise SystemExit('v8 patch failed: generated home screen art missing')
drawable = project_dir / 'app' / 'src' / 'main' / 'res' / 'drawable-nodpi'
drawable.mkdir(parents=True, exist_ok=True)
shutil.copy2(home_src, drawable / 'ftf_home_screen_v2.jpg')

old_home = '''            Image(
                painter = painterResource(R.drawable.ftf_home_frog),
                contentDescription = "Feed the Frog home frog",
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .align(Alignment.Center)
                    .fillMaxWidth(0.62f)
                    .offset(y = 24.dp)
            )

            Column('''
new_home = '''            Image(
                painter = painterResource(R.drawable.ftf_home_screen_v2),
                contentDescription = "Feed the Frog pond home screen",
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize()
            )

            Column('''
replace_once(old_home, new_home, 'full home-screen replacement')

# ---------------------------------------------------------------------------
# Distinct species movement profiles requested for v0.8.8.
# Dragonfly: very fast and unpredictable.
# Butterfly: fast fluttering loops.
# Mosquito: hummingbird hover that prefers the frog's catch area.
# Bee: slow smooth loops.
# Firefly: wild quick zigzags with strong vertical travel.
# Poison Fly: same normal flight as the standard Fly.
# ---------------------------------------------------------------------------
movement_pattern = re.compile(
    r'''                val step = fly\.type\.wanderStep \* 2\.6f\n'''
    r'''.*?'''
    r'''                val newY = \(fly\.position\.y \+ dy\)\.coerceIn\(screenTop, screenBottom\)''',
    re.S,
)
movement_replacement = '''                val step = fly.type.wanderStep * 2.6f
                val phase = tick * fly.type.speedMultiplier + fly.buzzSeed

                val screenLeft = boardSize.width * 0.10f
                val screenRight = boardSize.width * 0.75f
                val screenTop = boardSize.height * 0.24f
                val screenBottom = boardSize.height * 0.56f
                val roamX = screenLeft +
                    ((sin(phase * 0.19f + fly.buzzSeed * 0.43f) + 1f) * 0.5f) *
                    (screenRight - screenLeft)
                val roamY = screenTop +
                    ((cos(phase * 0.15f + fly.buzzSeed * 0.71f) + 1f) * 0.5f) *
                    (screenBottom - screenTop)

                var dx = 0f
                var dy = 0f
                when (fly.type) {
                    BugType.COMMON_FLY, BugType.POISON_FLY -> {
                        // Poison bugs intentionally use the exact normal-fly motion.
                        dx = cos(phase) * step + sin(phase * 1.5f) * step * 0.65f
                        dy = sin(phase * 1.12f) * step
                        dx += (roamX - fly.position.x) * 0.055f
                        dy += (roamY - fly.position.y) * 0.055f
                    }
                    BugType.MOSQUITO -> {
                        // Hummingbird-like micro-darts and hovering close to the frog.
                        val mouth = mouthPosition()
                        val hoverX = mouth.x + sin(phase * 1.25f) * catchRadiusPx * 0.55f
                        val hoverY = mouth.y - catchRadiusPx * 0.34f + cos(phase * 1.75f) * catchRadiusPx * 0.22f
                        dx = sin(phase * 7.4f) * step * 0.85f + (hoverX - fly.position.x) * 0.105f
                        dy = cos(phase * 8.1f) * step * 0.78f + (hoverY - fly.position.y) * 0.105f
                    }
                    BugType.DRAGONFLY -> {
                        // Fast, long, hard-to-predict darts across the whole CRT.
                        dx = cos(phase * 2.9f + sin(phase * 1.7f) * 2.6f) * step * 2.45f
                        dx += sin(phase * 6.4f + fly.buzzSeed) * step * 1.55f
                        dy = sin(phase * 3.25f + cos(phase * 2.15f) * 2.3f) * step * 2.25f
                        dy += cos(phase * 7.1f) * step * 1.35f
                        dx += (roamX - fly.position.x) * 0.080f
                        dy += (roamY - fly.position.y) * 0.080f
                    }
                    BugType.BUTTERFLY -> {
                        // Quick looping arcs with a smaller flutter laid over the loop.
                        dx = cos(phase * 1.75f) * step * 1.65f + sin(phase * 5.1f) * step * 0.82f
                        dy = sin(phase * 1.75f) * step * 1.30f + cos(phase * 5.6f) * step * 0.72f
                        dx += (roamX - fly.position.x) * 0.058f
                        dy += (roamY - fly.position.y) * 0.058f
                    }
                    BugType.BEE -> {
                        // Deliberately slow, broad loops.
                        dx = cos(phase * 0.48f) * step * 0.55f
                        dy = sin(phase * 0.48f) * step * 0.42f
                        dx += (roamX - fly.position.x) * 0.026f
                        dy += (roamY - fly.position.y) * 0.026f
                    }
                    BugType.FIREFLY -> {
                        // Fast, sharp zigzags plus an obvious rise-and-fall motion.
                        dx = sin(phase * 9.1f + sin(phase * 2.0f) * 2.8f) * step * 2.30f
                        dx += cos(phase * 4.7f) * step * 1.25f
                        dy = cos(phase * 7.8f) * step * 1.85f + sin(phase * 1.28f) * step * 2.05f
                        dx += (roamX - fly.position.x) * 0.072f
                        dy += (roamY - fly.position.y) * 0.072f
                    }
                    BugType.GOLDEN_FLY -> {
                        dx = cos(phase) * step + sin(phase * 2.8f) * step * 0.95f
                        dy = sin(phase * 1.18f) * step + cos(phase * 2.3f) * step * 0.75f
                        dx += (roamX - fly.position.x) * 0.060f
                        dy += (roamY - fly.position.y) * 0.060f
                    }
                }

                val newX = (fly.position.x + dx).coerceIn(screenLeft, screenRight)
                val newY = (fly.position.y + dy).coerceIn(screenTop, screenBottom)'''
if not movement_pattern.search(text):
    raise SystemExit('v8 patch failed: species movement block')
text = movement_pattern.sub(movement_replacement, text, count=1)

# ---------------------------------------------------------------------------
# Timer Skip upgrade. Like the other development upgrades it costs one coin,
# uses the paid three-puzzle trial, persists in the save, and exposes a button
# only while a swarm timer is active. Skipping resolves exactly like timeout:
# all remaining bugs escape and none are counted as caught.
# ---------------------------------------------------------------------------
replace_once(
    'private const val BUG_UNLOCK_COST = 1',
    'private const val BUG_UNLOCK_COST = 1\nprivate const val TIMER_SKIP_COST = 1',
    'timer skip cost',
)
replace_once(
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, POISON_IMMUNITY, BEE_IMMUNITY, FIREFLY_IMMUNITY, BUG_UNLOCK, COIN_MULTIPLIER, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, POISON_IMMUNITY, BEE_IMMUNITY, FIREFLY_IMMUNITY, BUG_UNLOCK, TIMER_SKIP, COIN_MULTIPLIER, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'timer skip upgrade kind',
)
replace_once(
    '    var pendingBugUnlockOrdinal by remember { mutableIntStateOf(-1) }',
    '    var pendingBugUnlockOrdinal by remember { mutableIntStateOf(-1) }\n    var timerSkipUnlocked by remember { mutableStateOf(prefs.getBoolean("timerSkipUnlocked", false)) }',
    'timer skip state',
)
replace_once(
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, timerSkipUnlocked, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'timer skip save key',
)
replace_once(
    '            .putInt("unlockedBugMask", unlockedBugMask)',
    '            .putInt("unlockedBugMask", unlockedBugMask)\n            .putBoolean("timerSkipUnlocked", timerSkipUnlocked)',
    'persist timer skip',
)

replace_once(
    '                    unlockedBugMask = unlockedBugMask,\n                    secondDie = secondDie,',
    '                    unlockedBugMask = unlockedBugMask,\n                    timerSkipUnlocked = timerSkipUnlocked,\n                    secondDie = secondDie,',
    'shop timer skip state call',
)
replace_once(
    '    unlockedBugMask: Int,\n    secondDie: Boolean,',
    '    unlockedBugMask: Int,\n    timerSkipUnlocked: Boolean,\n    secondDie: Boolean,',
    'shop timer skip state signature',
)
replace_once(
    '                    onBuyDie = {',
    '''                    onBuyTimerSkip = {
                        if (!timerSkipUnlocked && coins >= TIMER_SKIP_COST && pendingUpgrade == null) {
                            coins -= TIMER_SKIP_COST
                            pendingUpgrade = UpgradeKind.TIMER_SKIP
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Timer Skip Trial to install it!"
                        }
                    },
                    onBuyDie = {''',
    'timer skip purchase callback',
)
replace_once(
    '    onBuyBugUnlock: () -> Unit,\n    onBuyDie: () -> Unit,',
    '    onBuyBugUnlock: () -> Unit,\n    onBuyTimerSkip: () -> Unit,\n    onBuyDie: () -> Unit,',
    'timer skip callback signature',
)

shop_needle = '''                    onClick = onBuyFireflyImmunity
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
shop_replacement = '''                    onClick = onBuyFireflyImmunity
                )

                UpgradeRowCard(
                    icon = "⏭️",
                    title = "Timer Skip",
                    levelText = if (timerSkipUnlocked) "Installed" else "Not installed",
                    currentText = if (timerSkipUnlocked) "End an active swarm timer instantly" else "Adds a Skip Timer button during active swarms",
                    nextText = if (timerSkipUnlocked) "Uneaten bugs still escape normally" else "Skipping behaves exactly like the timer reaching zero",
                    progress = if (timerSkipUnlocked) 1f else 0f,
                    cost = if (timerSkipUnlocked) null else TIMER_SKIP_COST,
                    affordable = !timerSkipUnlocked && coins >= TIMER_SKIP_COST,
                    buttonText = if (timerSkipUnlocked) "INSTALLED" else "BUY TIMER SKIP",
                    onClick = onBuyTimerSkip
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
replace_once(shop_needle, shop_replacement, 'timer skip shop card')

replace_once(
    '''                                UpgradeKind.BUG_UNLOCK -> {
                                    if (pendingBugUnlockOrdinal >= 0) {
                                        val unlockedType = BugType.entries[pendingBugUnlockOrdinal]
                                        unlockedBugMask = unlockedBugMask or bugBit(unlockedType)
                                        pendingBugUnlockOrdinal = -1
                                    }
                                }
                                UpgradeKind.COIN_MULTIPLIER -> coinMultiplierLevel++''',
    '''                                UpgradeKind.BUG_UNLOCK -> {
                                    if (pendingBugUnlockOrdinal >= 0) {
                                        val unlockedType = BugType.entries[pendingBugUnlockOrdinal]
                                        unlockedBugMask = unlockedBugMask or bugBit(unlockedType)
                                        pendingBugUnlockOrdinal = -1
                                    }
                                }
                                UpgradeKind.TIMER_SKIP -> timerSkipUnlocked = true
                                UpgradeKind.COIN_MULTIPLIER -> coinMultiplierLevel++''',
    'timer skip challenge completion',
)
replace_once(
    '    UpgradeKind.BUG_UNLOCK -> "Random Bug Trial"\n    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"',
    '    UpgradeKind.BUG_UNLOCK -> "Random Bug Trial"\n    UpgradeKind.TIMER_SKIP -> "Timer Skip Trial"\n    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"',
    'timer skip challenge title',
)

shop_overlay_marker = '''            AnimatedVisibility(
                visible = showShop,
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {'''
skip_button = '''            if (timerSkipUnlocked && roundSecondsRemaining > 0 && flies.isNotEmpty() && !showShop && pendingUpgrade == null) {
                Button(
                    onClick = {
                        val escaped = flies.size
                        roundSecondsRemaining = 0
                        flies.clear()
                        latestEvent = "Timer skipped! $escaped ${if (escaped == 1) "bug flew" else "bugs flew"} away. Roll again!"
                    },
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(end = 18.dp, bottom = 132.dp),
                    shape = RoundedCornerShape(18.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = WoodDark)
                ) {
                    Text("⏭ SKIP TIMER • ${roundSecondsRemaining}s", color = Gold, fontWeight = FontWeight.Black)
                }
            }

            AnimatedVisibility(
                visible = showShop,
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {'''
replace_once(shop_overlay_marker, skip_button, 'active timer skip button')

# Version bump after v7 has converted the base 0.7.2 values.
app_gradle = project_dir / 'app' / 'build.gradle.kts'
gradle_text = app_gradle.read_text()
if 'versionCode = 16' not in gradle_text or 'versionName = "0.8.7-mask-rain"' not in gradle_text:
    raise SystemExit('v8 patch failed: expected v0.8.7 version values')
gradle_text = gradle_text.replace('versionCode = 16', 'versionCode = 17', 1)
gradle_text = gradle_text.replace('versionName = "0.8.7-mask-rain"', 'versionName = "0.8.8-home-motion-timer-skip"', 1)
app_gradle.write_text(gradle_text)

main_file.write_text(text)
print('patched v0.8.8: full home screen, species movement profiles, and one-coin Timer Skip upgrade')
