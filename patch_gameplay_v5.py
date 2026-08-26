#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_gameplay_v5.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'v5 patch failed: {label}')
    text = text.replace(old, new, 1)


def regex_once(pattern: str, replacement: str, label: str) -> None:
    global text
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f'v5 patch failed: {label}')

# ---------------------------------------------------------------------------
# DEVELOPMENT ECONOMY: every upgrade costs exactly one coin.
# ---------------------------------------------------------------------------
regex_once(r'private const val SECOND_DIE_COST = [0-9_]+', 'private const val SECOND_DIE_COST = 1', 'second die dev cost')
regex_once(r'private val DIE_UPGRADE_COSTS = intArrayOf\([^\n]+\)', 'private val DIE_UPGRADE_COSTS = intArrayOf(1, 1, 1, 1, 1)', 'die dev costs')
regex_once(r'private val RANGE_COSTS = intArrayOf\([^\n]+\)', 'private val RANGE_COSTS = intArrayOf(1, 1, 1, 1, 1, 1)', 'range dev costs')
regex_once(r'private val CAPACITY_COSTS = intArrayOf\([^\n]+\)', 'private val CAPACITY_COSTS = intArrayOf(1, 1, 1, 1, 1, 1, 1)', 'capacity dev costs')
regex_once(r'private const val AUTO_EAT_COST = [0-9_]+', 'private const val AUTO_EAT_COST = 1', 'auto eat dev cost')

replace_once(
    'private const val AUTO_EAT_MIN_RANGE_LEVEL = 3',
    'private const val AUTO_EAT_MIN_RANGE_LEVEL = 3\n'
    'private const val POISON_IMMUNITY_COST = 1\n'
    'private val COIN_MULTIPLIER_COSTS = intArrayOf(1, 1, 1, 1)',
    'new upgrade constants',
)

# ---------------------------------------------------------------------------
# New paid upgrade types.
# ---------------------------------------------------------------------------
replace_once(
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'private enum class UpgradeKind { RANGE, CAPACITY, AUTO_EAT, POISON_IMMUNITY, COIN_MULTIPLIER, DIE_ONE, SECOND_DIE, DIE_TWO }',
    'upgrade kinds',
)

replace_once(
    '    var autoEatUnlocked by remember { mutableStateOf(prefs.getBoolean("autoEatUnlocked", false)) }',
    '    var autoEatUnlocked by remember { mutableStateOf(prefs.getBoolean("autoEatUnlocked", false)) }\n'
    '    var poisonImmune by remember { mutableStateOf(prefs.getBoolean("poisonImmune", false)) }\n'
    '    var coinMultiplierLevel by remember { mutableIntStateOf(prefs.getInt("coinMultiplierLevel", 0).coerceIn(0, COIN_MULTIPLIER_COSTS.size)) }',
    'new upgrade state',
)

replace_once(
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'LaunchedEffect(coins, dieIndex, rangeLevel, capacityLevel, autoEatUnlocked, poisonImmune, coinMultiplierLevel, secondDie, secondDieIndex, totalCaught, soundOn, subscriptionPurchased, tvMode)',
    'save effect keys',
)
replace_once(
    '            .putBoolean("autoEatUnlocked", autoEatUnlocked)',
    '            .putBoolean("autoEatUnlocked", autoEatUnlocked)\n'
    '            .putBoolean("poisonImmune", poisonImmune)\n'
    '            .putInt("coinMultiplierLevel", coinMultiplierLevel)',
    'persist new upgrades',
)

# ---------------------------------------------------------------------------
# Gameplay effects.
# ---------------------------------------------------------------------------
replace_once(
    '                    autoEatEnabled = autoEatUnlocked,\n                    subscriptionPurchased = subscriptionPurchased,',
    '                    autoEatEnabled = autoEatUnlocked,\n                    poisonImmune = poisonImmune,\n                    subscriptionPurchased = subscriptionPurchased,',
    'GameBoard poison state call',
)
replace_once(
    '    autoEatEnabled: Boolean,\n    subscriptionPurchased: Boolean,',
    '    autoEatEnabled: Boolean,\n    poisonImmune: Boolean,\n    subscriptionPurchased: Boolean,',
    'GameBoard poison state signature',
)

old_poison = '''                        if (fly.type == BugType.POISON_BUG) {
                            val loss = maxOf(POISON_MINIMUM_LOSS, (coins * POISON_PERCENT) / 100)
                            coins = maxOf(0, coins - loss)
                            audio.playBeeBad()
                            latestEvent = "Poison bug! The frog got sick. -$loss coins."
                        } else if (fly.type.harmful) {'''
new_poison = '''                        if (fly.type == BugType.POISON_BUG) {
                            if (poisonImmune) {
                                totalCaught++
                                audio.playCatch()
                                latestEvent = "Poison bug eaten safely! Poison immunity protected the frog."
                            } else {
                                val loss = maxOf(POISON_MINIMUM_LOSS, (coins * POISON_PERCENT) / 100)
                                coins = maxOf(0, coins - loss)
                                audio.playBeeBad()
                                latestEvent = "Poison bug! The frog got sick. -$loss coins."
                            }
                        } else if (fly.type.harmful) {'''
replace_once(old_poison, new_poison, 'poison immunity effect')

replace_once(
    '                            coins += fly.type.reward',
    '                            val earnedCoins = fly.type.reward * (coinMultiplierLevel + 1)\n'
    '                            coins += earnedCoins',
    'coin multiplier reward',
)
replace_once(
    '                            latestEvent = unlockMessage ?: "${fly.type.label} eaten! +${fly.type.reward} coins."',
    '                            latestEvent = unlockMessage ?: "${fly.type.label} eaten! +$earnedCoins coins. (x${coinMultiplierLevel + 1})"',
    'coin multiplier event text',
)

# Switch the visual frog as soon as poison immunity is installed.
replace_once(
    '            painter = painterResource(R.drawable.ftf_frog),',
    '            painter = painterResource(if (poisonImmune) R.drawable.ftf_poison_frog else R.drawable.ftf_frog),',
    'poison frog visual swap',
)

# ---------------------------------------------------------------------------
# Shop state and purchase callbacks.
# ---------------------------------------------------------------------------
replace_once(
    '                    autoEatUnlocked = autoEatUnlocked,\n                    secondDie = secondDie,',
    '                    autoEatUnlocked = autoEatUnlocked,\n                    poisonImmune = poisonImmune,\n                    coinMultiplierLevel = coinMultiplierLevel,\n                    secondDie = secondDie,',
    'shop state call',
)

# Insert the new pay-then-trial callbacks immediately before the die purchase callback.
replace_once(
    '                    onBuyDie = {',
    '''                    onBuyPoisonImmunity = {
                        if (!poisonImmune && coins >= POISON_IMMUNITY_COST && pendingUpgrade == null) {
                            coins -= POISON_IMMUNITY_COST
                            pendingUpgrade = UpgradeKind.POISON_IMMUNITY
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Poison Immunity Trial to install it!"
                        }
                    },
                    onBuyCoinMultiplier = {
                        if (coinMultiplierLevel < COIN_MULTIPLIER_COSTS.size && pendingUpgrade == null) {
                            val cost = COIN_MULTIPLIER_COSTS[coinMultiplierLevel]
                            if (coins >= cost) {
                                coins -= cost
                                pendingUpgrade = UpgradeKind.COIN_MULTIPLIER
                                challengeAttempt++
                                showShop = false
                                latestEvent = "Payment accepted. Complete the Coin Multiplier Trial to raise fly rewards!"
                            }
                        }
                    },
                    onBuyDie = {''',
    'new purchase callbacks',
)

replace_once(
    '    autoEatUnlocked: Boolean,\n    secondDie: Boolean,',
    '    autoEatUnlocked: Boolean,\n    poisonImmune: Boolean,\n    coinMultiplierLevel: Int,\n    secondDie: Boolean,',
    'shop signature states',
)
replace_once(
    '    onBuyAutoEat: () -> Unit,\n    onBuyDie: () -> Unit,',
    '    onBuyAutoEat: () -> Unit,\n    onBuyPoisonImmunity: () -> Unit,\n    onBuyCoinMultiplier: () -> Unit,\n    onBuyDie: () -> Unit,',
    'shop signature callbacks',
)

# Add the two new cards after Auto-Eat and before the die tracks.
needle = '''                    onClick = onBuyAutoEat
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
replacement = '''                    onClick = onBuyAutoEat
                )

                UpgradeRowCard(
                    icon = "☠️🛡️",
                    title = "Poison Immunity",
                    levelText = if (poisonImmune) "Immune" else "Not installed",
                    currentText = if (poisonImmune) "Poison bugs can no longer take coins" else "Protects the frog from poisonous bugs",
                    nextText = if (poisonImmune) "Blue poison-dart frog form active" else "Also changes the frog to its poison-dart form",
                    progress = if (poisonImmune) 1f else 0f,
                    cost = if (poisonImmune) null else POISON_IMMUNITY_COST,
                    affordable = !poisonImmune && coins >= POISON_IMMUNITY_COST,
                    buttonText = if (poisonImmune) "IMMUNE" else "BUY IMMUNITY",
                    onClick = onBuyPoisonImmunity
                )

                val multiplierMaxed = coinMultiplierLevel >= COIN_MULTIPLIER_COSTS.size
                UpgradeRowCard(
                    icon = "🪙×",
                    title = "Coin Multiplier",
                    levelText = "x${coinMultiplierLevel + 1} fly rewards",
                    currentText = "Every good bug pays ${coinMultiplierLevel + 1}x its normal coin reward",
                    nextText = if (multiplierMaxed) "Maximum x${coinMultiplierLevel + 1}" else "Next: x${coinMultiplierLevel + 2} rewards",
                    progress = coinMultiplierLevel.toFloat() / COIN_MULTIPLIER_COSTS.size.toFloat(),
                    cost = if (multiplierMaxed) null else COIN_MULTIPLIER_COSTS[coinMultiplierLevel],
                    affordable = !multiplierMaxed && coins >= COIN_MULTIPLIER_COSTS[coinMultiplierLevel],
                    buttonText = if (multiplierMaxed) "MAXED" else "MULTIPLY",
                    onClick = onBuyCoinMultiplier
                )

                val dieMaxed = dieIndex >= DIE_SIDES.lastIndex'''
replace_once(needle, replacement, 'new shop cards')

# ---------------------------------------------------------------------------
# Upgrade trials.
# ---------------------------------------------------------------------------
replace_once(
    '                                UpgradeKind.AUTO_EAT -> autoEatUnlocked = true\n                                UpgradeKind.DIE_ONE -> dieIndex++',
    '                                UpgradeKind.AUTO_EAT -> autoEatUnlocked = true\n'
    '                                UpgradeKind.POISON_IMMUNITY -> poisonImmune = true\n'
    '                                UpgradeKind.COIN_MULTIPLIER -> coinMultiplierLevel++\n'
    '                                UpgradeKind.DIE_ONE -> dieIndex++',
    'challenge completion',
)
replace_once(
    '    UpgradeKind.AUTO_EAT -> "Auto-Eat Trial"\n    UpgradeKind.DIE_ONE -> "Dice Trial"',
    '    UpgradeKind.AUTO_EAT -> "Auto-Eat Trial"\n'
    '    UpgradeKind.POISON_IMMUNITY -> "Poison Immunity Trial"\n'
    '    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"\n'
    '    UpgradeKind.DIE_ONE -> "Dice Trial"',
    'challenge titles',
)

# ---------------------------------------------------------------------------
# Poison-dart frog art supplied by the user.
# ---------------------------------------------------------------------------
poison_src = repo_root / 'ui_assets' / 'ftf_poison_frog.webp'
if not poison_src.exists():
    raise SystemExit('missing poison immunity frog art')
drawable_dir = project_dir / 'app' / 'src' / 'main' / 'res' / 'drawable-nodpi'
drawable_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(poison_src, drawable_dir / 'ftf_poison_frog.webp')

main_file.write_text(text)
print('patched one-coin development economy, poison immunity, poison frog form, and coin multiplier')
