#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_gameplay_v2.py <MainActivity.kt>")

path = Path(sys.argv[1])
text = path.read_text()

def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"v2 patch failed: {label}")
    text = text.replace(old, new, 1)

replace_once(
    "private const val TAP_CATCH_RADIUS_DP = 54",
    "private const val TAP_CATCH_RADIUS_DP = 54\nprivate const val ROUND_TIME_SECONDS = 18\nprivate const val POISON_PERCENT = 12\nprivate const val POISON_MINIMUM_LOSS = 25\n\nprivate enum class UpgradeKind { RANGE, CAPACITY, DIE_ONE, SECOND_DIE, DIE_TWO }\n\nprivate data class ChallengeQuestion(val prompt: String, val options: List<Int>, val answer: Int)",
    "constants",
)

replace_once(
    '    BEE("Bee", BEE_PENALTY, 0.95f, 10f, 1.15f, 3.1f, true, 55, "Bee -40"),\n    GOLDEN_FLY("Golden Fly", 100, 1.08f, 9f, 1.18f, 4.4f, false, 80, "Golden Fly +100")',
    '    BEE("Bee", BEE_PENALTY, 0.95f, 10f, 1.15f, 3.1f, true, 55, "Bee -40"),\n    POISON_BUG("Poison Bug", 0, 1.02f, 8f, 0.92f, 2.4f, true, 12, "Poison Bug -12% coins"),\n    GOLDEN_FLY("Golden Fly", 100, 1.08f, 9f, 1.18f, 4.4f, false, 80, "Golden Fly +100")',
    "poison enum",
)

replace_once(
    '    var showShop by remember { mutableStateOf(false) }\n    var latestEvent by remember { mutableStateOf("Catch flies, unlock new bugs, and avoid bees!") }',
    '    var showShop by remember { mutableStateOf(false) }\n    var pendingUpgrade by remember { mutableStateOf<UpgradeKind?>(null) }\n    var challengeAttempt by remember { mutableIntStateOf(0) }\n    var latestEvent by remember { mutableStateOf("Catch flies, unlock new bugs, and avoid bees!") }',
    "challenge state",
)

replace_once(
    '    var lastDieTwo by remember { mutableIntStateOf(0) }\n\n    val flies = remember { mutableStateListOf<Fly>() }',
    '    var lastDieTwo by remember { mutableIntStateOf(0) }\n    var roundSecondsRemaining by remember { mutableIntStateOf(0) }\n    var roundSerial by remember { mutableIntStateOf(0) }\n\n    val flies = remember { mutableStateListOf<Fly>() }',
    "timer state",
)

old_audio = '''    LaunchedEffect(flies.size, soundOn) {
        audio.updateBuzz(flies)
    }
'''
new_audio = old_audio + '''
    LaunchedEffect(roundSerial) {
        if (roundSerial == 0) return@LaunchedEffect
        while (roundSecondsRemaining > 0 && flies.isNotEmpty()) {
            delay(1_000)
            if (showShop || pendingUpgrade != null) continue
            if (flies.isEmpty()) break
            roundSecondsRemaining--
        }
        if (roundSecondsRemaining <= 0 && flies.isNotEmpty()) {
            val escaped = flies.size
            flies.clear()
            latestEvent = "Time's up! $escaped ${if (escaped == 1) "bug flew" else "bugs flew"} away. Roll again!"
        }
    }
'''
replace_once(old_audio, new_audio, "timer effect")

old_resolution = '''                        if (fly.type.harmful) {
                            coins = maxOf(0, coins + fly.type.reward)
                            audio.playBeeBad()
                            latestEvent = "Ouch! The frog ate a bee. ${fly.type.reward} coins."
                        } else {'''
new_resolution = '''                        if (index < 0) return@GameBoard
                        if (fly.type == BugType.POISON_BUG) {
                            val loss = maxOf(POISON_MINIMUM_LOSS, (coins * POISON_PERCENT) / 100)
                            coins = maxOf(0, coins - loss)
                            audio.playBeeBad()
                            latestEvent = "Poison bug! The frog got sick. -$loss coins."
                        } else if (fly.type.harmful) {
                            coins = maxOf(0, coins + fly.type.reward)
                            audio.playBeeBad()
                            latestEvent = "Ouch! The frog ate a bee. ${fly.type.reward} coins."
                        } else {'''
replace_once(old_resolution, new_resolution, "poison resolution")

replace_once(
    '                    remainingFlies = flies.size,\n                    totalCaught = totalCaught,',
    '                    remainingFlies = flies.size,\n                    secondsRemaining = roundSecondsRemaining,\n                    totalCaught = totalCaught,',
    "timer arg",
)
replace_once(
    '                        lastRoll = total\n                        repeat(total) {',
    '                        lastRoll = total\n                        roundSecondsRemaining = ROUND_TIME_SECONDS\n                        roundSerial++\n                        repeat(total) {',
    "start timer",
)
replace_once(
    '    remainingFlies: Int,\n    totalCaught: Int,',
    '    remainingFlies: Int,\n    secondsRemaining: Int,\n    totalCaught: Int,',
    "timer signature",
)
replace_once(
    '                        if (enabled) "Ready to roll" else "Feed the whole swarm",',
    '                        if (enabled) "Ready to roll" else "⏱ ${secondsRemaining}s — catch what you can!",',
    "timer title",
)
replace_once(
    '                        "$remainingFlies ${if (remainingFlies == 1) "bug" else "bugs"} remaining"',
    '                        "$remainingFlies ${if (remainingFlies == 1) "bug" else "bugs"} remaining • then they fly away"',
    "timer helper",
)

old_range = '''                    onBuyRange = {
                        if (rangeLevel < RANGE_COSTS.size) {
                            val cost = RANGE_COSTS[rangeLevel]
                            if (coins >= cost) {
                                coins -= cost
                                rangeLevel++
                                audio.playUpgrade()
                            }
                        }
                    },'''
new_range = '''                    onBuyRange = {
                        if (rangeLevel < RANGE_COSTS.size) {
                            val cost = RANGE_COSTS[rangeLevel]
                            if (coins >= cost && pendingUpgrade == null) {
                                coins -= cost
                                pendingUpgrade = UpgradeKind.RANGE
                                challengeAttempt++
                                showShop = false
                                latestEvent = "Payment accepted. Complete the Tongue Trial to install it!"
                            }
                        }
                    },'''
replace_once(old_range, new_range, "range trial")

old_capacity = '''                    onBuyCapacity = {
                        if (capacityLevel < CAPACITY_COSTS.size) {
                            val cost = CAPACITY_COSTS[capacityLevel]
                            if (coins >= cost) {
                                coins -= cost
                                capacityLevel++
                                audio.playUpgrade()
                            }
                        }
                    },'''
new_capacity = '''                    onBuyCapacity = {
                        if (capacityLevel < CAPACITY_COSTS.size) {
                            val cost = CAPACITY_COSTS[capacityLevel]
                            if (coins >= cost && pendingUpgrade == null) {
                                coins -= cost
                                pendingUpgrade = UpgradeKind.CAPACITY
                                challengeAttempt++
                                showShop = false
                                latestEvent = "Payment accepted. Complete the Catch Trial to install it!"
                            }
                        }
                    },'''
replace_once(old_capacity, new_capacity, "capacity trial")

old_die1 = '''                    onBuyDie = {
                        if (dieIndex < DIE_SIDES.lastIndex) {
                            val cost = DIE_UPGRADE_COSTS[dieIndex]
                            if (coins >= cost) {
                                coins -= cost
                                dieIndex++
                                audio.playUpgrade()
                            }
                        }
                    },'''
new_die1 = '''                    onBuyDie = {
                        if (dieIndex < DIE_SIDES.lastIndex) {
                            val cost = DIE_UPGRADE_COSTS[dieIndex]
                            if (coins >= cost && pendingUpgrade == null) {
                                coins -= cost
                                pendingUpgrade = UpgradeKind.DIE_ONE
                                challengeAttempt++
                                showShop = false
                                latestEvent = "Payment accepted. Complete the Dice Trial to install it!"
                            }
                        }
                    },'''
replace_once(old_die1, new_die1, "die one trial")

old_second = '''                    onBuySecondDie = {
                        if (!secondDie && coins >= SECOND_DIE_COST) {
                            coins -= SECOND_DIE_COST
                            secondDie = true
                            secondDieIndex = 0
                            audio.playUpgrade()
                        }
                    },'''
new_second = '''                    onBuySecondDie = {
                        if (!secondDie && coins >= SECOND_DIE_COST && pendingUpgrade == null) {
                            coins -= SECOND_DIE_COST
                            pendingUpgrade = UpgradeKind.SECOND_DIE
                            challengeAttempt++
                            showShop = false
                            latestEvent = "Payment accepted. Complete the Double-Dice Trial to unlock die #2!"
                        }
                    },'''
replace_once(old_second, new_second, "second die trial")

old_die2 = '''                    onBuySecondDieUpgrade = {
                        if (secondDie && secondDieIndex < DIE_SIDES.lastIndex) {
                            val cost = DIE_UPGRADE_COSTS[secondDieIndex]
                            if (coins >= cost) {
                                coins -= cost
                                secondDieIndex++
                                audio.playUpgrade()
                            }
                        }
                    }'''
new_die2 = '''                    onBuySecondDieUpgrade = {
                        if (secondDie && secondDieIndex < DIE_SIDES.lastIndex) {
                            val cost = DIE_UPGRADE_COSTS[secondDieIndex]
                            if (coins >= cost && pendingUpgrade == null) {
                                coins -= cost
                                pendingUpgrade = UpgradeKind.DIE_TWO
                                challengeAttempt++
                                showShop = false
                                latestEvent = "Payment accepted. Complete the Dice Trial to improve die #2!"
                            }
                        }
                    }'''
replace_once(old_die2, new_die2, "die two trial")

needle = '''                )
            }
        }
    }
}

@Composable
private fun StartScreen('''
insert = '''                )
            }

            AnimatedVisibility(visible = pendingUpgrade != null, modifier = Modifier.fillMaxSize()) {
                val challengeKind = pendingUpgrade
                if (challengeKind != null) {
                    UpgradeChallengeOverlay(
                        kind = challengeKind,
                        attempt = challengeAttempt,
                        onSolved = {
                            when (challengeKind) {
                                UpgradeKind.RANGE -> rangeLevel++
                                UpgradeKind.CAPACITY -> capacityLevel++
                                UpgradeKind.DIE_ONE -> dieIndex++
                                UpgradeKind.SECOND_DIE -> { secondDie = true; secondDieIndex = 0 }
                                UpgradeKind.DIE_TWO -> secondDieIndex++
                            }
                            pendingUpgrade = null
                            audio.playUpgrade()
                            audio.playUnlock()
                            latestEvent = "Challenge cleared! Your paid upgrade is installed."
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun StartScreen('''
replace_once(needle, insert, "trial overlay")

replace_once(
    '                    Text("Spend coins to improve each upgrade track.", color = Cream, fontWeight = FontWeight.Bold, fontSize = 10.sp)',
    '                    Text("Pay first, then beat a 3-puzzle frog trial to install it.", color = Cream, fontWeight = FontWeight.Bold, fontSize = 10.sp)',
    "shop copy",
)

poison_visual = '''        BugType.POISON_BUG -> {
            val scale = 1.0f * boostScale
            drawOval(Color(0xFF5E2A78), Offset(center.x - 17f * scale, center.y - 11f * scale), Size(34f * scale, 24f * scale))
            drawCircle(Color(0xFF2E133A), 9f * scale, Offset(center.x + 14f * scale, center.y))
            drawCircle(Color(0xFFB7EF62), 4f * scale, Offset(center.x - 8f * scale, center.y - 3f * scale))
            drawCircle(Color(0xFFB7EF62), 3f * scale, Offset(center.x + 2f * scale, center.y + 5f * scale))
            drawOval(Color(0xFFD7F7B5).copy(alpha = 0.72f), Offset(center.x - 25f * scale, center.y - 20f * scale), Size(22f * scale, 12f * scale))
            drawOval(Color(0xFFD7F7B5).copy(alpha = 0.72f), Offset(center.x + 2f * scale, center.y - 20f * scale), Size(22f * scale, 12f * scale))
        }
'''
replace_once('        BugType.GOLDEN_FLY -> {\n', poison_visual + '        BugType.GOLDEN_FLY -> {\n', "poison drawing")
replace_once(
    '    BugGuideRow(BugType.BEE),\n    BugGuideRow(BugType.GOLDEN_FLY)',
    '    BugGuideRow(BugType.BEE),\n    BugGuideRow(BugType.POISON_BUG),\n    BugGuideRow(BugType.GOLDEN_FLY)',
    "poison guide",
)
replace_once(
    '''private fun randomBugType(totalCaught: Int): BugType {
    val roll = Random.nextInt(100)''',
    '''private fun randomBugType(totalCaught: Int): BugType {
    if (totalCaught >= 12 && Random.nextInt(100) < 6) return BugType.POISON_BUG
    val roll = Random.nextInt(100)''',
    "poison chance",
)

challenge_code = r'''

@Composable
private fun UpgradeChallengeOverlay(kind: UpgradeKind, attempt: Int, onSolved: () -> Unit) {
    var step by remember(kind, attempt) { mutableIntStateOf(0) }
    var feedback by remember(kind, attempt) { mutableStateOf("Solve 3 puzzles to install your paid upgrade.") }
    val question = remember(kind, attempt, step) { makeChallengeQuestion(kind, attempt * 31 + step * 7 + kind.ordinal * 13) }

    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xDD17341F)) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Card(
                modifier = Modifier.fillMaxWidth().padding(22.dp),
                shape = RoundedCornerShape(26.dp),
                colors = CardDefaults.cardColors(containerColor = ShopPaper),
                elevation = CardDefaults.cardElevation(defaultElevation = 12.dp)
            ) {
                Column(Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(challengeTitle(kind), color = WoodDark, fontWeight = FontWeight.Black, fontSize = 24.sp)
                    Text("PAID UPGRADE TRIAL", color = FrogDark, fontWeight = FontWeight.Black, fontSize = 11.sp)
                    Spacer(Modifier.height(10.dp))
                    Text("Puzzle ${step + 1} of 3", color = Color(0xFF9A6A00), fontWeight = FontWeight.Black, fontSize = 13.sp)
                    Spacer(Modifier.height(8.dp))
                    Surface(color = Cream, shape = RoundedCornerShape(18.dp)) {
                        Text(question.prompt, modifier = Modifier.fillMaxWidth().padding(18.dp), color = Ink, fontWeight = FontWeight.Black, fontSize = 19.sp, textAlign = TextAlign.Center)
                    }
                    Spacer(Modifier.height(10.dp))
                    question.options.forEach { option ->
                        Button(
                            onClick = {
                                if (option == question.answer) {
                                    if (step >= 2) onSolved() else { step++; feedback = "Correct! Next puzzle." }
                                } else feedback = "Not quite. Try again — you do not pay twice."
                            },
                            modifier = Modifier.fillMaxWidth().height(50.dp).padding(vertical = 3.dp),
                            shape = RoundedCornerShape(15.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
                        ) { Text(option.toString(), fontWeight = FontWeight.Black, fontSize = 17.sp) }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(feedback, color = Wood, fontWeight = FontWeight.Bold, fontSize = 11.sp, textAlign = TextAlign.Center)
                    Text("The swarm timer pauses during shops and trials.", color = FrogDark, fontSize = 9.sp, textAlign = TextAlign.Center)
                }
            }
        }
    }
}

private fun challengeTitle(kind: UpgradeKind): String = when (kind) {
    UpgradeKind.RANGE -> "Tongue Trial"
    UpgradeKind.CAPACITY -> "Catch Trial"
    UpgradeKind.DIE_ONE -> "Dice Trial"
    UpgradeKind.SECOND_DIE -> "Double-Dice Trial"
    UpgradeKind.DIE_TWO -> "Dice Trial II"
}

private fun makeChallengeQuestion(kind: UpgradeKind, seed: Int): ChallengeQuestion {
    val r = Random(seed)
    val mode = ((seed % 4) + 4) % 4
    val prompt: String
    val answer: Int
    when (mode) {
        0 -> {
            val start = r.nextInt(1, 7); val jump = r.nextInt(2, 5)
            answer = start + jump * 3
            prompt = "What comes next?  $start, ${start + jump}, ${start + jump * 2}, ?"
        }
        1 -> {
            val a = r.nextInt(2, 9); val b = r.nextInt(2, 9)
            answer = a + b
            prompt = "The frog catches $a bugs, then $b more. How many total?"
        }
        2 -> {
            val total = r.nextInt(7, 15); val escaped = r.nextInt(1, total - 2)
            answer = total - escaped
            prompt = "$total bugs appear and $escaped fly away. How many remain?"
        }
        else -> {
            val base = r.nextInt(2, 9); val add = if (kind == UpgradeKind.CAPACITY) 3 else 2
            answer = base + add
            prompt = "Which number is exactly $add more than $base?"
        }
    }
    val wrong1 = (answer - r.nextInt(1, 4)).coerceAtLeast(0)
    var wrong2 = answer + r.nextInt(1, 4)
    if (wrong2 == wrong1 || wrong2 == answer) wrong2 += 2
    val raw = listOf(answer, wrong1, wrong2).distinct()
    val options = if (raw.size == 3) raw.shuffled(r) else listOf(answer, answer + 1, answer + 3).shuffled(r)
    return ChallengeQuestion(prompt, options, answer)
}
'''
replace_once('\nprivate fun distance(a: Offset, b: Offset): Float {', challenge_code + '\nprivate fun distance(a: Offset, b: Offset): Float {', "challenge helpers")

path.write_text(text)
print(f"patched challenges, timer, and poison bug in {path}")
