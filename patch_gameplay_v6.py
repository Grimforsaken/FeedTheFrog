#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys
import zipfile

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_gameplay_v6.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'v6 patch failed: {label}')
    text = text.replace(old, new, 1)


def regex_once(pattern: str, replacement: str, label: str, flags=0) -> None:
    global text
    text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'v6 patch failed: {label}')

text = text.replace('BugType.FAST_FLY', 'BugType.DRAGONFLY')
text = text.replace('BugType.MOTH', 'BugType.BUTTERFLY')
text = text.replace('BugType.POISON_BUG', 'BugType.POISON_FLY')
text = text.replace('FAST_FLY(', 'DRAGONFLY(')
text = text.replace('MOTH(', 'BUTTERFLY(')
text = text.replace('POISON_BUG(', 'POISON_FLY(')

regex_once(r'private const val FLY_REWARD = [0-9_]+', 'private const val FLY_REWARD = 1', 'fly reward')
replace_once(
    'private val COIN_MULTIPLIER_COSTS = intArrayOf(1, 1, 1, 1)',
    'private val COIN_MULTIPLIER_COSTS = intArrayOf(1, 1, 1, 1)\n'
    'private const val BEE_IMMUNITY_COST = 1\n'
    'private const val FIREFLY_IMMUNITY_COST = 1\n'
    'private const val BUG_UNLOCK_COST = 1\n'
    'private const val FIREFLY_DAMAGE_PER_SECOND = 5\n'
    'private const val FIREFLY_DAMAGE_SECONDS = 5\n'
    'private const val POISON_DAMAGE_PER_SECOND = 3\n'
    'private const val POISON_DAMAGE_SECONDS = 6',
    'new development constants',
)

enum_pattern = re.compile(r'    COMMON_FLY\("Fly".*?\n    GOLDEN_FLY\("Golden Fly".*?\n\}', re.S)
enum_replacement = '''    COMMON_FLY("Fly", 1, 1.0f, 7f, 1.0f, 2.2f, false, 0, "Fly +1"),
    MOSQUITO("Mosquito", 2, 0.82f, 10f, 1.45f, 4.0f, false, 0, "Mosquito +2"),
    DRAGONFLY("Dragonfly", 3, 1.05f, 13f, 1.70f, 5.3f, false, 0, "Dragonfly +3"),
    BUTTERFLY("Butterfly", 5, 1.18f, 7f, 0.78f, 1.7f, false, 0, "Butterfly +5"),
    BEE("Bee", BEE_PENALTY, 1.0f, 10f, 1.15f, 3.1f, true, 0, "Bee -40; helmet gives immunity"),
    FIREFLY("Firefly", -5, 1.02f, 10f, 1.22f, 3.5f, true, 0, "Firefly -5/sec for 5 sec"),
    POISON_FLY("Poison Fly", -3, 1.04f, 8f, 0.96f, 2.6f, true, 0, "Poison Fly -3/sec for 6 sec"),
    GOLDEN_FLY("Golden Fly", 100, 1.08f, 9f, 1.18f, 4.4f, false, 9999, "Golden Fly +100")
}'''
if not enum_pattern.search(text):
    raise SystemExit('v6 patch failed: bug enum block')
text = enum_pattern.sub(enum_replacement, text, count=1)

replace_once(
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, POISON_IMMUNITY, COIN_MULTIPLIER, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, POISON_IMMUNITY, BEE_IMMUNITY, FIREFLY_IMMUNITY, BUG_UNLOCK, COIN_MULTIPLIER, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'upgrade kinds',
)

replace_once(
    '    var coinMultiplierLevel by remember { mutableIntStateOf(prefs.getInt("coinMultiplierLevel", 0).coerceIn(0, COIN_MULTIPLIER_COSTS.size)) }',
    '    var coinMultiplierLevel by remember { mutableIntStateOf(prefs.getInt("coinMultiplierLevel", 0).coerceIn(0, COIN_MULTIPLIER_COSTS.size)) }\n'
    '    var beeImmune by remember { mutableStateOf(prefs.getBoolean("beeImmune", false)) }\n'
    '    var fireflyImmune by remember { mutableStateOf(prefs.getBoolean("fireflyImmune", false)) }\n'
    '    var unlockedBugMask by remember { mutableIntStateOf(prefs.getInt("unlockedBugMask", bugBit(BugType.COMMON_FLY)) or bugBit(BugType.COMMON_FLY)) }\n'
    '    var pendingBugUnlockOrdinal by remember { mutableIntStateOf(-1) }',
    'new saved state',
)
replace_once(
    '    var roundSerial by remember { mutableIntStateOf(0) }',
    '    var roundSerial by remember { mutableIntStateOf(0) }\n'
    '    var fireDamageSeconds by remember { mutableIntStateOf(0) }\n'
    '    var fireDamageSerial by remember { mutableIntStateOf(0) }\n'
    '    var poisonDamageSeconds by remember { mutableIntStateOf(0) }\n'
    '    var poisonDamageSerial by remember { mutableIntStateOf(0) }',
    'damage timer state',
)
replace_once(
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, beeImmune, fireflyImmune, unlockedBugMask, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'save effect keys',
)
replace_once(
    '            .putInt("coinMultiplierLevel", coinMultiplierLevel)',
    '            .putInt("coinMultiplierLevel", coinMultiplierLevel)\n'
    '            .putBoolean("beeImmune", beeImmune)\n'
    '            .putBoolean("fireflyImmune", fireflyImmune)\n'
    '            .putInt("unlockedBugMask", unlockedBugMask)',
    'persist new upgrades',
)

replace_once(
    '    DisposableEffect(audio) {',
    '''    LaunchedEffect(fireDamageSerial) {
        if (fireDamageSerial == 0) return@LaunchedEffect
        while (fireDamageSeconds > 0) {
            delay(1_000)
            if (fireflyImmune) { fireDamageSeconds = 0; break }
            coins = maxOf(0, coins - FIREFLY_DAMAGE_PER_SECOND)
            fireDamageSeconds--
            latestEvent = if (fireDamageSeconds > 0) {
                "The frog is burning! -$FIREFLY_DAMAGE_PER_SECOND coins/sec • ${fireDamageSeconds}s left"
            } else "The fire has gone out."
        }
    }

    LaunchedEffect(poisonDamageSerial) {
        if (poisonDamageSerial == 0) return@LaunchedEffect
        while (poisonDamageSeconds > 0) {
            delay(1_000)
            if (poisonImmune) { poisonDamageSeconds = 0; break }
            coins = maxOf(0, coins - POISON_DAMAGE_PER_SECOND)
            poisonDamageSeconds--
            latestEvent = if (poisonDamageSeconds > 0) {
                "Poison is draining coins! -$POISON_DAMAGE_PER_SECOND coins/sec • ${poisonDamageSeconds}s left"
            } else "The poison has worn off."
        }
    }

    DisposableEffect(audio) {''',
    'damage effects',
)

replace_once(
    '                    poisonImmune = poisonImmune,\n                    subscriptionPurchased = subscriptionPurchased,',
    '                    poisonImmune = poisonImmune,\n'
    '                    beeImmune = beeImmune,\n'
    '                    fireflyImmune = fireflyImmune,\n'
    '                    fireDamageActive = fireDamageSeconds > 0,\n'
    '                    poisonDamageActive = poisonDamageSeconds > 0,\n'
    '                    subscriptionPurchased = subscriptionPurchased,',
    'GameBoard new state call',
)
replace_once(
    '    poisonImmune: Boolean,\n    subscriptionPurchased: Boolean,',
    '    poisonImmune: Boolean,\n'
    '    beeImmune: Boolean,\n'
    '    fireflyImmune: Boolean,\n'
    '    fireDamageActive: Boolean,\n'
    '    poisonDamageActive: Boolean,\n'
    '    subscriptionPurchased: Boolean,',
    'GameBoard new state signature',
)

frog_layer = '''        val frogWidth = maxWidth * 0.36f
        val frogBob = (kotlin.math.sin(buzzPhase * 0.55f) * 2.0f).dp
        Image(
            painter = painterResource(if (poisonImmune) R.drawable.ftf_poison_frog else R.drawable.ftf_frog),
            contentDescription = "Feed the Frog",
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = maxHeight * 0.57f + frogBob)
                .width(frogWidth)
        )
'''
new_frog_layer = '''        var rainFrame by remember { mutableIntStateOf(0) }
        LaunchedEffect(fireflyImmune) {
            if (!fireflyImmune) { rainFrame = 0; return@LaunchedEffect }
            while (true) {
                delay(180)
                rainFrame = (rainFrame + 1) % 4
            }
        }

        val frogWidth = maxWidth * 0.36f
        val frogBob = (kotlin.math.sin(buzzPhase * 0.55f) * 2.0f).dp
        Image(
            painter = painterResource(if (poisonImmune) R.drawable.ftf_poison_frog else R.drawable.ftf_frog),
            contentDescription = "Feed the Frog",
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .offset(y = maxHeight * 0.57f + frogBob)
                .width(frogWidth)
        )

        if (beeImmune) {
            Image(
                painter = painterResource(R.drawable.frog_helmet),
                contentDescription = "Bee immunity helmet",
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .offset(y = maxHeight * 0.505f + frogBob)
                    .width(frogWidth * 0.76f)
            )
        }

        if (fireflyImmune) {
            val rainDrawable = when (rainFrame) {
                1 -> R.drawable.rain_cloud_1
                2 -> R.drawable.rain_cloud_2
                3 -> R.drawable.rain_cloud_3
                else -> R.drawable.rain_cloud_0
            }
            Image(
                painter = painterResource(rainDrawable),
                contentDescription = "Firefly immunity rain cloud",
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .offset(y = maxHeight * 0.445f)
                    .width(frogWidth * 0.86f)
            )
        }
'''
replace_once(frog_layer, new_frog_layer, 'frog overlays')

replace_once(
    '        drawCatchRing(mouth, catchRadiusPx, strikeInProgress)\n',
    '''        drawCatchRing(mouth, catchRadiusPx, strikeInProgress)

        if (fireDamageActive) {
            repeat(10) { i ->
                val cycle = ((buzzPhase / (2f * PI.toFloat())) + i * 0.11f) % 1f
                val x = mouth.x + sin(i * 1.73f + buzzPhase * 1.8f) * (34f + (i % 3) * 18f)
                val y = mouth.y + 42f - cycle * 145f
                val r = 11f + (i % 3) * 3f
                drawCircle(Color(0xFFFF5A00).copy(alpha = 0.82f), r, Offset(x, y))
                drawCircle(Color(0xFFFFD21A).copy(alpha = 0.88f), r * 0.52f, Offset(x, y + 2f))
            }
        }

        if (poisonDamageActive) {
            repeat(11) { i ->
                val cycle = ((buzzPhase / (2f * PI.toFloat())) + i * 0.083f) % 1f
                val x = mouth.x + sin(i * 2.12f) * (38f + (i % 4) * 15f)
                val y = mouth.y + 50f - cycle * 165f
                val r = 6f + (i % 4) * 2.2f
                drawCircle(Color(0xFF9DFF29).copy(alpha = 0.18f), r, Offset(x, y))
                drawCircle(Color(0xFF62D900).copy(alpha = 0.82f), r, Offset(x, y), style = Stroke(width = 2.4f))
            }
        }
''',
    'frog hazard animations',
)

replace_once('            drawBug(center, fly.type, 1f)\n', '            // Bug art is layered above this Canvas.\n', 'remove procedural bug render')
controls_marker = '''        Column(
            modifier = Modifier
                .align(Alignment.TopStart)'''
bug_layer = '''        flies.forEach { fly ->
            if (fly.position != Offset.Unspecified && fly.id !in pendingCatchIds) {
                val phase = buzzPhase * fly.type.speedMultiplier + fly.buzzSeed
                val amp = fly.type.movementAmplitude
                val buzz = Offset(cos(phase) * amp, sin(phase * 1.6f) * (amp * 0.68f))
                val center = fly.position + buzz
                val spritePx = 82f * fly.type.scale
                val spriteDp = with(density) { spritePx.toDp() }
                Image(
                    painter = painterResource(bugDrawable(fly.type)),
                    contentDescription = fly.type.label,
                    contentScale = ContentScale.Fit,
                    modifier = Modifier
                        .offset {
                            androidx.compose.ui.unit.IntOffset(
                                (center.x - spritePx * 0.5f).toInt(),
                                (center.y - spritePx * 0.5f).toInt()
                            )
                        }
                        .size(spriteDp)
                )
            }
        }

'''
replace_once(controls_marker, bug_layer + controls_marker, 'bug art layer')
replace_once(
    '        BugType.POISON_FLY -> {',
    '''        BugType.FIREFLY -> {
            drawStandardFly(center, 1.0f * boostScale, bodyColor = Color(0xFF6C321C), headColor = Color(0xFF2B1711), wingColor = Color(0xFFFFD58A))
            drawCircle(Color(0xFFFF8500).copy(alpha = 0.9f), 8f * boostScale, Offset(center.x - 15f, center.y + 11f))
        }
        BugType.POISON_FLY -> {''',
    'firefly fallback drawing',
)

resolution_pattern = re.compile(r'                        if \(fly\.type == BugType\.POISON_FLY\) \{.*?\n                        \}\n                    \},', re.S)
new_resolution = '''                        if (fly.type == BugType.POISON_FLY) {
                            totalCaught++
                            if (poisonImmune) {
                                audio.playCatch()
                                latestEvent = "Poison fly eaten safely! Poison immunity protected the frog."
                            } else {
                                poisonDamageSeconds = POISON_DAMAGE_SECONDS
                                poisonDamageSerial++
                                audio.playBeeBad()
                                latestEvent = "Poison fly! -$POISON_DAMAGE_PER_SECOND coins/sec for $POISON_DAMAGE_SECONDS seconds."
                            }
                        } else if (fly.type == BugType.FIREFLY) {
                            totalCaught++
                            if (fireflyImmune) {
                                audio.playCatch()
                                latestEvent = "Firefly eaten safely! The rain cloud put out the flames."
                            } else {
                                fireDamageSeconds = FIREFLY_DAMAGE_SECONDS
                                fireDamageSerial++
                                audio.playBeeBad()
                                latestEvent = "Firefly! -$FIREFLY_DAMAGE_PER_SECOND coins/sec for $FIREFLY_DAMAGE_SECONDS seconds."
                            }
                        } else if (fly.type == BugType.BEE) {
                            totalCaught++
                            if (beeImmune) {
                                audio.playCatch()
                                latestEvent = "Bee eaten safely! The knight helmet protected the frog."
                            } else {
                                coins = maxOf(0, coins + fly.type.reward)
                                audio.playBeeBad()
                                latestEvent = "Ouch! The frog ate a bee. ${fly.type.reward} coins."
                            }
                        } else {
                            totalCaught++
                            val earnedCoins = fly.type.reward * (coinMultiplierLevel + 1)
                            coins += earnedCoins
                            if (fly.type == BugType.GOLDEN_FLY) audio.playGolden() else audio.playCatch()
                            latestEvent = "${fly.type.label} eaten! +$earnedCoins coins. (x${coinMultiplierLevel + 1})"
                        }
                    },'''
if not resolution_pattern.search(text):
    raise SystemExit('v6 patch failed: catch resolution block')
text = resolution_pattern.sub(new_resolution, text, count=1)

replace_once('type = randomBugType(totalCaught)', 'type = randomBugType(unlockedBugMask)', 'spawn pool call')
helpers_pattern = re.compile(r'private fun bugTypesUnlocked\(totalCaught: Int\): List<BugType> =.*?\nprivate fun randomBugType\(totalCaught: Int\): BugType \{.*?\n\}\n\nprivate fun distance', re.S)
helpers_replacement = '''private val SPAWN_UNLOCK_TYPES = listOf(
    BugType.MOSQUITO,
    BugType.DRAGONFLY,
    BugType.BUTTERFLY,
    BugType.BEE,
    BugType.FIREFLY,
    BugType.POISON_FLY
)

private fun bugBit(type: BugType): Int = 1 shl type.ordinal
private fun isBugUnlocked(mask: Int, type: BugType): Boolean = type == BugType.COMMON_FLY || (mask and bugBit(type)) != 0
private fun unlockedSpawnTypes(mask: Int): List<BugType> = listOf(BugType.COMMON_FLY) + SPAWN_UNLOCK_TYPES.filter { isBugUnlocked(mask, it) }
private fun bugTypesUnlocked(totalCaught: Int): List<BugType> = listOf(BugType.COMMON_FLY)
private fun nextUnlockText(totalCaught: Int): String = "new bug types unlock in UPGRADES"
private fun newlyUnlockedBugMessage(oldCaught: Int, newCaught: Int): String? = null
private fun randomBugType(unlockedMask: Int): BugType {
    val pool = unlockedSpawnTypes(unlockedMask)
    return pool[Random.nextInt(pool.size)]
}
private fun bugDrawable(type: BugType): Int = when (type) {
    BugType.COMMON_FLY -> R.drawable.bug_fly
    BugType.MOSQUITO -> R.drawable.bug_mosquito
    BugType.DRAGONFLY -> R.drawable.bug_dragonfly
    BugType.BUTTERFLY -> R.drawable.bug_butterfly
    BugType.BEE -> R.drawable.bug_bee
    BugType.FIREFLY -> R.drawable.bug_firefly
    BugType.POISON_FLY -> R.drawable.bug_poison_fly
    BugType.GOLDEN_FLY -> R.drawable.bug_fly
}

private fun distance'''
if not helpers_pattern.search(text):
    raise SystemExit('v6 patch failed: spawn helper block')
text = helpers_pattern.sub(helpers_replacement, text, count=1)

replace_once(
    '                    coinMultiplierLevel = coinMultiplierLevel,\n                    secondDie = secondDie,',
    '                    coinMultiplierLevel = coinMultiplierLevel,\n                    beeImmune = beeImmune,\n                    fireflyImmune = fireflyImmune,\n                    unlockedBugMask = unlockedBugMask,\n                    secondDie = secondDie,',
    'shop new state call',
)
replace_once(
    '                    onBuyDie = {',
    '''                    onBuyBeeImmunity = {
                        if (!beeImmune && coins >= BEE_IMMUNITY_COST && pendingUpgrade == null) {
                            coins -= BEE_IMMUNITY_COST
                            pendingUpgrade = UpgradeKind.BEE_IMMUNITY
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Bee Immunity Trial to earn the knight helmet!"
                        }
                    },
                    onBuyFireflyImmunity = {
                        if (!fireflyImmune && coins >= FIREFLY_IMMUNITY_COST && pendingUpgrade == null) {
                            coins -= FIREFLY_IMMUNITY_COST
                            pendingUpgrade = UpgradeKind.FIREFLY_IMMUNITY
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Rain Cloud Trial for firefly immunity!"
                        }
                    },
                    onBuyBugUnlock = {
                        val locked = SPAWN_UNLOCK_TYPES.filter { !isBugUnlocked(unlockedBugMask, it) }
                        if (locked.isNotEmpty() && coins >= BUG_UNLOCK_COST && pendingUpgrade == null) {
                            coins -= BUG_UNLOCK_COST
                            pendingBugUnlockOrdinal = locked[Random.nextInt(locked.size)].ordinal
                            pendingUpgrade = UpgradeKind.BUG_UNLOCK
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Random Bug Trial to add a new bug to the pond!"
                        }
                    },
                    onBuyDie = {''',
    'new purchase callbacks',
)
replace_once(
    '    coinMultiplierLevel: Int,\n    secondDie: Boolean,',
    '    coinMultiplierLevel: Int,\n    beeImmune: Boolean,\n    fireflyImmune: Boolean,\n    unlockedBugMask: Int,\n    secondDie: Boolean,',
    'shop new state signature',
)
replace_once(
    '    onBuyCoinMultiplier: () -> Unit,\n    onBuyDie: () -> Unit,',
    '    onBuyCoinMultiplier: () -> Unit,\n    onBuyBeeImmunity: () -> Unit,\n    onBuyFireflyImmunity: () -> Unit,\n    onBuyBugUnlock: () -> Unit,\n    onBuyDie: () -> Unit,',
    'shop new callback signature',
)
shop_needle = '''                    onClick = onBuyCoinMultiplier
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
shop_replacement = '''                    onClick = onBuyCoinMultiplier
                )

                UpgradeRowCard(
                    icon = "🪰+",
                    title = "Random Bug Unlock",
                    levelText = "${unlockedSpawnTypes(unlockedBugMask).size} / ${SPAWN_UNLOCK_TYPES.size + 1} bug types in the pond",
                    currentText = if (SPAWN_UNLOCK_TYPES.all { isBugUnlocked(unlockedBugMask, it) }) "All bug types unlocked" else "Adds one random locked bug type to future swarms",
                    nextText = "Normal flies are the only starting bug type",
                    progress = (unlockedSpawnTypes(unlockedBugMask).size - 1).toFloat() / SPAWN_UNLOCK_TYPES.size.toFloat(),
                    cost = if (SPAWN_UNLOCK_TYPES.all { isBugUnlocked(unlockedBugMask, it) }) null else BUG_UNLOCK_COST,
                    affordable = SPAWN_UNLOCK_TYPES.any { !isBugUnlocked(unlockedBugMask, it) } && coins >= BUG_UNLOCK_COST,
                    buttonText = if (SPAWN_UNLOCK_TYPES.all { isBugUnlocked(unlockedBugMask, it) }) "ALL UNLOCKED" else "ADD RANDOM BUG",
                    onClick = onBuyBugUnlock
                )

                UpgradeRowCard(
                    icon = "🪖",
                    title = "Bee Immunity",
                    levelText = if (beeImmune) "Knight helmet equipped" else "Not protected",
                    currentText = if (beeImmune) "Bees can be eaten without losing coins" else "Protects the frog from bees",
                    nextText = if (beeImmune) "Helmet works on green and blue frog forms" else "Adds the separate knight helmet overlay",
                    progress = if (beeImmune) 1f else 0f,
                    cost = if (beeImmune) null else BEE_IMMUNITY_COST,
                    affordable = !beeImmune && coins >= BEE_IMMUNITY_COST,
                    buttonText = if (beeImmune) "HELMET EQUIPPED" else "BUY HELMET",
                    onClick = onBuyBeeImmunity
                )

                UpgradeRowCard(
                    icon = "🌧️",
                    title = "Firefly Immunity",
                    levelText = if (fireflyImmune) "Rain cloud active" else "Not protected",
                    currentText = if (fireflyImmune) "Fireflies can be eaten without burning" else "Protects the frog from fireflies",
                    nextText = if (fireflyImmune) "Animated rain cloud stays over the frog" else "Adds the rain-cloud protection effect",
                    progress = if (fireflyImmune) 1f else 0f,
                    cost = if (fireflyImmune) null else FIREFLY_IMMUNITY_COST,
                    affordable = !fireflyImmune && coins >= FIREFLY_IMMUNITY_COST,
                    buttonText = if (fireflyImmune) "RAIN ACTIVE" else "BUY RAIN CLOUD",
                    onClick = onBuyFireflyImmunity
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
replace_once(shop_needle, shop_replacement, 'new shop cards')

replace_once('                    BugGuideSection(totalCaught)', '                    BugGuideSection(unlockedBugMask)', 'bug guide call')
replace_once('ShopSectionTitle("BUG GUIDE", "Unlocked by total successful catches.")', 'ShopSectionTitle("BUG GUIDE", "Normal flies start unlocked; add random bug types in the shop.")', 'bug guide subtitle')
replace_once('private fun BugGuideSection(totalCaught: Int)', 'private fun BugGuideSection(unlockedBugMask: Int)', 'bug guide signature')
replace_once('                val unlocked = totalCaught >= row.type.unlockAtCaught', '                val unlocked = isBugUnlocked(unlockedBugMask, row.type)', 'bug guide unlock state')
replace_once('if (unlocked) row.type.guideName else "Unlock at ${row.type.unlockAtCaught} catches"', 'if (unlocked) row.type.guideName else "Unlock with Random Bug Unlock"', 'bug guide locked text')
old_guide_icon = '''                        Box(contentAlignment = Alignment.Center) {
                            Text(if (unlocked) "✓" else "?", color = if (unlocked) FrogDark else Wood, fontWeight = FontWeight.Black)
                        }'''
new_guide_icon = '''                        Box(contentAlignment = Alignment.Center) {
                            if (unlocked) {
                                Image(
                                    painter = painterResource(bugDrawable(row.type)),
                                    contentDescription = row.type.label,
                                    contentScale = ContentScale.Fit,
                                    modifier = Modifier.fillMaxSize().padding(3.dp)
                                )
                            } else {
                                Text("?", color = Wood, fontWeight = FontWeight.Black)
                            }
                        }'''
replace_once(old_guide_icon, new_guide_icon, 'bug guide art')
rows_pattern = re.compile(r'private fun bugGuideRows\(\): List<BugGuideRow> = listOf\(.*?\n\)', re.S)
rows_replacement = '''private fun bugGuideRows(): List<BugGuideRow> = listOf(
    BugGuideRow(BugType.COMMON_FLY),
    BugGuideRow(BugType.MOSQUITO),
    BugGuideRow(BugType.DRAGONFLY),
    BugGuideRow(BugType.BUTTERFLY),
    BugGuideRow(BugType.BEE),
    BugGuideRow(BugType.FIREFLY),
    BugGuideRow(BugType.POISON_FLY)
)'''
if not rows_pattern.search(text):
    raise SystemExit('v6 patch failed: bug guide rows')
text = rows_pattern.sub(rows_replacement, text, count=1)

replace_once(
    '                                UpgradeKind.POISON_IMMUNITY -> poisonImmune = true\n                                UpgradeKind.COIN_MULTIPLIER -> coinMultiplierLevel++',
    '                                UpgradeKind.POISON_IMMUNITY -> { poisonImmune = true; poisonDamageSeconds = 0 }\n'
    '                                UpgradeKind.BEE_IMMUNITY -> beeImmune = true\n'
    '                                UpgradeKind.FIREFLY_IMMUNITY -> { fireflyImmune = true; fireDamageSeconds = 0 }\n'
    '                                UpgradeKind.BUG_UNLOCK -> {\n'
    '                                    if (pendingBugUnlockOrdinal >= 0) {\n'
    '                                        val unlockedType = BugType.entries[pendingBugUnlockOrdinal]\n'
    '                                        unlockedBugMask = unlockedBugMask or bugBit(unlockedType)\n'
    '                                        pendingBugUnlockOrdinal = -1\n'
    '                                    }\n'
    '                                }\n'
    '                                UpgradeKind.COIN_MULTIPLIER -> coinMultiplierLevel++',
    'challenge completion cases',
)
replace_once(
    '    UpgradeKind.POISON_IMMUNITY -> "Poison Immunity Trial"\n    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"',
    '    UpgradeKind.POISON_IMMUNITY -> "Poison Immunity Trial"\n'
    '    UpgradeKind.BEE_IMMUNITY -> "Bee Immunity Trial"\n'
    '    UpgradeKind.FIREFLY_IMMUNITY -> "Rain Cloud Trial"\n'
    '    UpgradeKind.BUG_UNLOCK -> "Random Bug Trial"\n'
    '    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"',
    'challenge title cases',
)

drawable_dir = project_dir / 'app' / 'src' / 'main' / 'res' / 'drawable-nodpi'
drawable_dir.mkdir(parents=True, exist_ok=True)
asset_names = [
    'bug_fly.webp','bug_mosquito.webp','bug_dragonfly.webp','bug_butterfly.webp','bug_bee.webp','bug_firefly.webp','bug_poison_fly.webp','frog_helmet.webp','rain_cloud_0.webp','rain_cloud_1.webp','rain_cloud_2.webp','rain_cloud_3.webp'
]
asset_zip = repo_root / 'ui_assets' / 'v6_assets.zip'
if not asset_zip.exists():
    raise SystemExit(f'missing v6 art archive: {asset_zip}')
with zipfile.ZipFile(asset_zip, 'r') as archive:
    names = set(archive.namelist())
    for name in asset_names:
        if name not in names:
            raise SystemExit(f'missing v6 art asset in archive: {name}')
        (drawable_dir / name).write_bytes(archive.read(name))

main_file.write_text(text)
print('patched v0.8.4 bug roster, art, random spawn unlocks, bee helmet, rain immunity, and timed fire/poison effects')
