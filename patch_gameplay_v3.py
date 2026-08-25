#!/usr/bin/env python3
from pathlib import Path
import base64
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_gameplay_v3.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'v3 patch failed: {label}')
    text = text.replace(old, new, 1)

# System-bar safe layout so the title and roll button are never hidden by Android controls.
replace_once(
    'import androidx.compose.foundation.layout.width',
    'import androidx.compose.foundation.layout.width\nimport androidx.compose.foundation.layout.navigationBarsPadding\nimport androidx.compose.foundation.layout.statusBarsPadding',
    'system bar imports',
)
replace_once(
    'Column(Modifier.fillMaxWidth().background(WoodDark)) {',
    'Column(Modifier.fillMaxWidth().background(WoodDark).statusBarsPadding()) {',
    'header status bar padding',
)
roll_pattern = re.compile(
    r'(@Composable\nprivate fun RollBar\(.*?\) \{\n    Surface\(\n        modifier = Modifier\.fillMaxWidth\(\))',
    re.S,
)
if not roll_pattern.search(text):
    raise SystemExit('v3 patch failed: RollBar surface')
text = roll_pattern.sub(r'\1.navigationBarsPadding()', text, count=1)

# Auto-eat is a paid mid-range upgrade and follows the existing pay-then-challenge rule.
replace_once(
    'private const val TV_MODE_POND_LIFE = 1',
    'private const val TV_MODE_POND_LIFE = 1\nprivate const val AUTO_EAT_COST = 1_000_000\nprivate const val AUTO_EAT_MIN_RANGE_LEVEL = 3',
    'auto eat constants',
)
replace_once(
    'private enum class UpgradeKind { RANGE, CAPACITY, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'auto eat upgrade kind',
)
replace_once(
    '    var capacityLevel by remember { mutableIntStateOf(prefs.getInt("capacityLevel", 0).coerceIn(0, CAPACITY_COSTS.size)) }',
    '    var capacityLevel by remember { mutableIntStateOf(prefs.getInt("capacityLevel", 0).coerceIn(0, CAPACITY_COSTS.size)) }\n'
    '    var autoEatUnlocked by remember { mutableStateOf(prefs.getBoolean("autoEatUnlocked", false)) }',
    'auto eat state',
)
replace_once(
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'auto eat save effect',
)
replace_once(
    '            .putInt("capacityLevel", capacityLevel)',
    '            .putInt("capacityLevel", capacityLevel)\n            .putBoolean("autoEatUnlocked", autoEatUnlocked)',
    'save auto eat',
)

# Pass the upgrade into the gameplay board and shop.
replace_once(
    '                    catchCapacity = capacityLevel + 1,\n                    subscriptionPurchased = subscriptionPurchased,',
    '                    catchCapacity = capacityLevel + 1,\n                    autoEatEnabled = autoEatUnlocked,\n                    subscriptionPurchased = subscriptionPurchased,',
    'GameBoard auto eat argument',
)
replace_once(
    '                    capacityLevel = capacityLevel,\n                    secondDie = secondDie,',
    '                    capacityLevel = capacityLevel,\n                    autoEatUnlocked = autoEatUnlocked,\n                    secondDie = secondDie,',
    'shop auto eat argument',
)
replace_once(
    '    catchCapacity: Int,\n    subscriptionPurchased: Boolean,',
    '    catchCapacity: Int,\n    autoEatEnabled: Boolean,\n    subscriptionPurchased: Boolean,',
    'GameBoard auto eat signature',
)
replace_once(
    '    capacityLevel: Int,\n    secondDie: Boolean,',
    '    capacityLevel: Int,\n    autoEatUnlocked: Boolean,\n    secondDie: Boolean,',
    'shop auto eat signature state',
)
replace_once(
    '    onBuyCapacity: () -> Unit,\n    onBuyDie: () -> Unit,',
    '    onBuyCapacity: () -> Unit,\n    onBuyAutoEat: () -> Unit,\n    onBuyDie: () -> Unit,',
    'shop auto eat callback signature',
)

# Add purchase callback before die upgrades.
replace_once(
    '                    onBuyDie = {',
    '''                    onBuyAutoEat = {
                        if (!autoEatUnlocked && rangeLevel >= AUTO_EAT_MIN_RANGE_LEVEL && coins >= AUTO_EAT_COST && pendingUpgrade == null) {
                            coins -= AUTO_EAT_COST
                            pendingUpgrade = UpgradeKind.AUTO_EAT
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Auto-Eat Trial to install it!"
                        }
                    },
                    onBuyDie = {''',
    'auto eat purchase callback',
)

# Add Auto-Eat shop card directly after Catch Capacity.
capacity_end = '''                    onClick = onBuyCapacity
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
auto_card = '''                    onClick = onBuyCapacity
                )

                UpgradeRowCard(
                    icon = "🐸⚡",
                    title = "Auto-Eat (Mid Range)",
                    levelText = if (autoEatUnlocked) "Installed" else if (rangeLevel >= AUTO_EAT_MIN_RANGE_LEVEL) "Available now" else "Unlocks at Tongue Level ${AUTO_EAT_MIN_RANGE_LEVEL + 1}",
                    currentText = if (autoEatUnlocked) "Automatically snaps at bugs crossing the middle of your tongue range" else "Hands-free eating for bugs that enter the mid-range zone",
                    nextText = if (autoEatUnlocked) "Active every round" else "Requires the paid Auto-Eat Trial",
                    progress = if (autoEatUnlocked) 1f else if (rangeLevel >= AUTO_EAT_MIN_RANGE_LEVEL) 0.5f else 0f,
                    cost = if (autoEatUnlocked) null else AUTO_EAT_COST,
                    affordable = !autoEatUnlocked && rangeLevel >= AUTO_EAT_MIN_RANGE_LEVEL && coins >= AUTO_EAT_COST,
                    buttonText = if (autoEatUnlocked) "INSTALLED" else if (rangeLevel < AUTO_EAT_MIN_RANGE_LEVEL) "REQUIRES MID RANGE" else "BUY AUTO-EAT",
                    onClick = onBuyAutoEat
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
replace_once(capacity_end, auto_card, 'auto eat shop card')

# Challenge completion and title for Auto-Eat.
replace_once(
    '                                UpgradeKind.CAPACITY -> capacityLevel++\n                                UpgradeKind.DIE_ONE -> dieIndex++',
    '                                UpgradeKind.CAPACITY -> capacityLevel++\n                                UpgradeKind.AUTO_EAT -> autoEatUnlocked = true\n                                UpgradeKind.DIE_ONE -> dieIndex++',
    'auto eat challenge completion',
)
replace_once(
    '    UpgradeKind.CAPACITY -> "Catch Trial"\n    UpgradeKind.DIE_ONE -> "Dice Trial"',
    '    UpgradeKind.CAPACITY -> "Catch Trial"\n    UpgradeKind.AUTO_EAT -> "Auto-Eat Trial"\n    UpgradeKind.DIE_ONE -> "Dice Trial"',
    'auto eat challenge title',
)

# Move frog mouth slightly upward to match the new art sitting on the TV stand.
text = text.replace('boardSize.height * 0.70f', 'boardSize.height * 0.665f')
text = text.replace('size.height * 0.70f', 'size.height * 0.665f')

# Spawn most bugs inside or just at the edge of the catchable zone instead of high above the frog.
old_spawn = '''                val x = Random.nextFloat() * boardSize.width * 0.76f + boardSize.width * 0.12f
                val y = Random.nextFloat() * boardSize.height * 0.40f + boardSize.height * 0.08f
                onFlyMoved(fly.id, Offset(x, y))'''
new_spawn = '''                val mouth = mouthPosition()
                val reach = catchRadiusPx * 0.92f
                val x = mouth.x + (Random.nextFloat() - 0.5f) * reach * 1.45f
                val y = mouth.y - reach * (0.20f + Random.nextFloat() * 0.72f)
                onFlyMoved(
                    fly.id,
                    Offset(
                        x.coerceIn(28f, boardSize.width - 28f),
                        y.coerceIn(boardSize.height * 0.18f, boardSize.height * 0.64f)
                    )
                )'''
replace_once(old_spawn, new_spawn, 'closer bug spawn')

# Faster, more noticeable autonomous movement plus a gentle pull back toward catchable range.
replace_once('            delay(70)', '            delay(45)', 'faster bug tick')
replace_once('                val step = fly.type.wanderStep', '                val step = fly.type.wanderStep * 2.6f', 'larger bug movement')
old_clamp = '''                val margin = 26f
                val newX = (fly.position.x + dx).coerceIn(margin, boardSize.width - margin)
                val newY = (fly.position.y + dy).coerceIn(margin, boardSize.height * 0.61f)'''
new_clamp = '''                val mouth = mouthPosition()
                val currentDistance = distance(fly.position, mouth)
                if (currentDistance > catchRadiusPx * 0.94f) {
                    val pull = 0.012f
                    dx += (mouth.x - fly.position.x) * pull
                    dy += (mouth.y - fly.position.y) * pull
                }

                val margin = 26f
                val newX = (fly.position.x + dx).coerceIn(margin, boardSize.width - margin)
                val newY = (fly.position.y + dy).coerceIn(margin, boardSize.height * 0.64f)'''
replace_once(old_clamp, new_clamp, 'bug range attraction')

# Auto-Eat automatically targets one bug at a time in the middle band of the current tongue range.
auto_effect = '''

    LaunchedEffect(autoEatEnabled, boardSize, flies.size) {
        if (!autoEatEnabled) return@LaunchedEffect
        while (true) {
            delay(1_350)
            if (boardSize == IntSize.Zero || strikeInProgress || flies.isEmpty()) continue
            val mouth = mouthPosition()
            val target = flies
                .filter { it.position != Offset.Unspecified && it.id !in pendingCatchIds }
                .filter {
                    val d = distance(it.position, mouth)
                    d >= catchRadiusPx * 0.34f && d <= catchRadiusPx * 0.74f
                }
                .minByOrNull { distance(it.position, mouth) }

            if (target != null) {
                tongueTarget = target.position
                pendingCatchIds = listOf(target.id)
                strikeInProgress = true
                strikeSerial++
                onTongueSnap()
            }
        }
    }
'''
replace_once('\n    LaunchedEffect(strikeSerial) {', auto_effect + '\n    LaunchedEffect(strikeSerial) {', 'auto eat effect')

# Replace vector frog with the supplied glossy frog art. The Image is layered over the
# TV stand while tongue/bugs stay animated on the Canvas behind it.
replace_once('    Box(modifier = modifier) {', '    BoxWithConstraints(modifier = modifier) {', 'GameBoard BoxWithConstraints')
replace_once('        drawFrog(mouth)\n', '        // Glossy frog sprite is drawn as a Compose Image above this Canvas.\n', 'remove vector frog')
frog_layer = '''

        val frogWidth = maxWidth * 0.36f
        val frogBob = (kotlin.math.sin(buzzPhase * 0.55f) * 2.0f).dp
        Image(
            painter = painterResource(R.drawable.ftf_frog),
            contentDescription = "Feed the Frog",
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = maxHeight * 0.57f + frogBob)
                .width(frogWidth)
        )
'''
replace_once(
    '\n        Column(\n            modifier = Modifier\n                .align(Alignment.TopStart)',
    frog_layer + '\n        Column(\n            modifier = Modifier\n                .align(Alignment.TopStart)',
    'glossy frog layer',
)

# Decode the supplied glossy frog art into the Android drawable resources.
drawable_dir = project_dir / 'app' / 'src' / 'main' / 'res' / 'drawable-nodpi'
drawable_dir.mkdir(parents=True, exist_ok=True)
frog_src = repo_root / 'ui_assets' / 'ftf_frog.b64'
if not frog_src.exists():
    raise SystemExit('missing glossy frog asset')
(drawable_dir / 'ftf_frog.webp').write_bytes(base64.b64decode(frog_src.read_text().strip()))

main_file.write_text(text)
print('patched glossy frog, closer/faster flies, mid-range auto-eat, and Android safe areas')
