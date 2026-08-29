#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_v093_coin_effects.py <MainActivity.kt> <project_dir>")

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
app_gradle = project_dir / "app/build.gradle.kts"

text = main_file.read_text(encoding="utf-8")
gradle = app_gradle.read_text(encoding="utf-8")


def replace_once(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} anchor, found {count}")
    return src.replace(old, new, 1)

# Exact configurable values for this quick balance patch.
text = replace_once(
    text,
    "private const val BEE_PENALTY = -40\n",
    "private const val BEE_PENALTY = -20\nprivate const val BEE_IMMUNITY_REWARD = 5\nprivate const val LIGHTNING_BUG_PENALTY = -25\nprivate const val LIGHTNING_IMMUNITY_REWARD = 5\n",
    "Bee penalty constant",
)

text = replace_once(
    text,
    'BEE("Bee", BEE_PENALTY, 1.0f, 10f, 1.15f, 3.1f, true, 0, "Bee -40; helmet gives immunity"),',
    'BEE("Bee", BEE_PENALTY, 1.0f, 10f, 1.15f, 3.1f, true, 0, "Bee -20; helmet turns it into +5"),',
    "Bee guide entry",
)

text = replace_once(
    text,
    'LIGHTNING_BUG("Lightning Bug", 5, 1.03f, 5f, LIGHTNING_BUG_SPEED_FACTOR, 4.9f, false, 0, "Lightning Bug +5 • shocks frog without rod")',
    'LIGHTNING_BUG("Lightning Bug", LIGHTNING_BUG_PENALTY, 1.03f, 5f, LIGHTNING_BUG_SPEED_FACTOR, 4.9f, true, 0, "Lightning Bug -25; rod turns it into +5")',
    "Lightning Bug guide entry",
)

old_bee = '''                            BugType.BEE -> {
                                if (beeImmune) {
                                    audio.playCatch()
                                    latestEvent = "Bee eaten safely! The knight helmet protected the frog."
                                } else {
                                    coins = maxOf(0, coins + liveFly.type.reward)
                                    audio.playBeeBad()
                                    latestEvent = "Ouch! The frog ate a bee. ${liveFly.type.reward} coins."
                                }
                            }
'''
new_bee = '''                            BugType.BEE -> {
                                if (beeImmune) {
                                    coins += BEE_IMMUNITY_REWARD
                                    audio.playCatch()
                                    latestEvent = "Bee eaten safely! The knight helmet protected the frog. +$BEE_IMMUNITY_REWARD coins."
                                } else {
                                    coins = maxOf(0, coins + BEE_PENALTY)
                                    audio.playBeeBad()
                                    latestEvent = "Ouch! The frog ate a bee. $BEE_PENALTY coins."
                                }
                            }
'''
text = replace_once(text, old_bee, new_bee, "Bee catch-resolution block")

old_lightning = '''                            BugType.LIGHTNING_BUG -> {
                                val earnedCoins = liveFly.type.reward * (coinMultiplierLevel + 1)
                                coins += earnedCoins
                                lightningShockSerial++
                                audio.playCatch()
                                latestEvent = if (lightningImmune) {
                                    "Lightning Bug eaten! +$earnedCoins coins. The lightning rod absorbed the shock."
                                } else {
                                    "Lightning Bug eaten! +$earnedCoins coins. ZAP!"
                                }
                            }
'''
new_lightning = '''                            BugType.LIGHTNING_BUG -> {
                                lightningShockSerial++
                                if (lightningImmune) {
                                    coins += LIGHTNING_IMMUNITY_REWARD
                                    audio.playCatch()
                                    latestEvent = "Lightning Bug eaten! The lightning rod absorbed the shock. +$LIGHTNING_IMMUNITY_REWARD coins."
                                } else {
                                    coins = maxOf(0, coins + LIGHTNING_BUG_PENALTY)
                                    audio.playBeeBad()
                                    latestEvent = "Lightning Bug eaten! $LIGHTNING_BUG_PENALTY coins. ZAP!"
                                }
                            }
'''
text = replace_once(text, old_lightning, new_lightning, "Lightning Bug catch-resolution block")

text = replace_once(
    text,
    'currentText = if (beeImmune) "Bees can be eaten without losing coins" else "Protects the frog from bees",',
    'currentText = if (beeImmune) "Bees award +5 coins instead of taking coins" else "Bee costs 20 coins; the helmet turns it into +5",',
    "Bee Immunity description",
)
text = replace_once(
    text,
    'nextText = if (beeImmune) "Helmet works on green and blue frog forms" else "Adds the separate knight helmet overlay",',
    'nextText = if (beeImmune) "Helmet works on green and blue frog forms • Bee +5" else "Adds the separate knight helmet overlay",',
    "Bee Immunity next text",
)
text = replace_once(
    text,
    'currentText = if (lightningImmune) "Lightning Bugs flash the rod instead of shocking the frog" else "Protects the frog from Lightning Bug shock",',
    'currentText = if (lightningImmune) "Lightning Bugs award +5 coins and flash the rod" else "Lightning Bug costs 25 coins and shocks the frog",',
    "Lightning Immunity description",
)
text = replace_once(
    text,
    'nextText = if (lightningImmune) "Rod remains beside either frog color" else "Adds the visible lightning rod beside the frog",',
    'nextText = if (lightningImmune) "Rod remains beside either frog color • Lightning Bug +5" else "Adds the visible lightning rod beside the frog",',
    "Lightning Immunity next text",
)

# Version the quick patch separately from the verified v0.9.2 baseline.
gradle = replace_once(gradle, "versionCode = 21", "versionCode = 22", "versionCode")
gradle = replace_once(
    gradle,
    'versionName = "0.9.2-bugs-tv-lightning"',
    'versionName = "0.9.3-coin-effects"',
    "versionName",
)

main_file.write_text(text, encoding="utf-8")
app_gradle.write_text(gradle, encoding="utf-8")

# Strict source checks: exact values, exact immunity rewards, no multiplier on either effect.
checks = {
    "Bee penalty -20": "private const val BEE_PENALTY = -20" in text,
    "Bee immunity +5": "private const val BEE_IMMUNITY_REWARD = 5" in text,
    "Lightning penalty -25": "private const val LIGHTNING_BUG_PENALTY = -25" in text,
    "Lightning immunity +5": "private const val LIGHTNING_IMMUNITY_REWARD = 5" in text,
    "Bee immune reward applied": "coins += BEE_IMMUNITY_REWARD" in text,
    "Bee penalty applied": "coins = maxOf(0, coins + BEE_PENALTY)" in text,
    "Lightning immune reward applied": "coins += LIGHTNING_IMMUNITY_REWARD" in text,
    "Lightning penalty applied": "coins = maxOf(0, coins + LIGHTNING_BUG_PENALTY)" in text,
    "v0.9.3 version code": "versionCode = 22" in gradle,
    "v0.9.3 version name": 'versionName = "0.9.3-coin-effects"' in gradle,
}
for label, ok in checks.items():
    print(f"  {'PASS' if ok else 'FAIL'} {label}")
    if not ok:
        raise SystemExit(f"v0.9.3 source check failed: {label}")

print("patched v0.9.3: Bee -20 / immune +5; Lightning Bug -25 / immune +5")
