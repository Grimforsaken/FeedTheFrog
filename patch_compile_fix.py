#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_compile_fix.py <MainActivity.kt>')

path = Path(sys.argv[1])
text = path.read_text()

call = '                    UpgradeChallengeOverlay(\n'
fixed_call = '                    UpgradeChallengeOverlayFixed(\n'
if fixed_call not in text:
    if call not in text:
        raise SystemExit('compile fix failed: challenge overlay call not found')
    text = text.replace(call, fixed_call, 1)

# Keep the legacy challengeTitle function deterministic for later generated
# patches. The actual overlay below derives its title from the enum name, but
# Kotlin still requires this old when-expression to remain exhaustive.
title_start_marker = 'private fun challengeTitle(kind: UpgradeKind): String = when (kind) {'
title_start = text.find(title_start_marker)
if title_start < 0:
    raise SystemExit('compile fix failed: challengeTitle function not found')
title_end = text.find('\n}', title_start)
if title_end < 0:
    raise SystemExit('compile fix failed: challengeTitle function end not found')
normalized_titles = '''private fun challengeTitle(kind: UpgradeKind): String = when (kind) {
    UpgradeKind.RANGE -> "Tongue Trial"
    UpgradeKind.CAPACITY -> "Catch Trial"
    UpgradeKind.AUTO_EAT -> "Auto-Eat Trial"
    UpgradeKind.POISON_IMMUNITY -> "Poison Immunity Trial"
    UpgradeKind.BEE_IMMUNITY -> "Bee Immunity Trial"
    UpgradeKind.FIREFLY_IMMUNITY -> "Rain Cloud Trial"
    UpgradeKind.BUG_UNLOCK -> "Random Bug Trial"
    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"
    UpgradeKind.DIE_ONE -> "Dice Trial"
    UpgradeKind.SECOND_DIE -> "Double-Dice Trial"
    UpgradeKind.DIE_TWO -> "Dice Trial II"
}'''
text = text[:title_start] + normalized_titles + text[title_end + 2:]

if 'private fun UpgradeChallengeOverlayFixed(' not in text:
    text += r'''

@Composable
private fun UpgradeChallengeOverlayFixed(kind: UpgradeKind, attempt: Int, onSolved: () -> Unit) {
    var step by remember(kind, attempt) { mutableIntStateOf(0) }
    var feedback by remember(kind, attempt) { mutableStateOf("Solve 3 puzzles to install your paid upgrade.") }

    val puzzle = remember(kind, attempt, step) {
        val seed = attempt * 31 + step * 11 + kind.ordinal * 7
        val left = 2 + (seed % 8)
        val right = 1 + ((seed / 3 + step * 2) % 9)
        val answer = left + right
        val options = listOf(answer, answer + 1, maxOf(1, answer - 1)).distinct().shuffled()
        Triple(left, right, options)
    }
    val answer = puzzle.first + puzzle.second
    val title = kind.name.replace("_", " ")

    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xDD17341F)) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Card(
                modifier = Modifier.fillMaxWidth().padding(22.dp),
                shape = RoundedCornerShape(26.dp),
                colors = CardDefaults.cardColors(containerColor = ShopPaper),
                elevation = CardDefaults.cardElevation(defaultElevation = 12.dp)
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text("$title TRIAL", color = WoodDark, fontWeight = FontWeight.Black, fontSize = 22.sp, textAlign = TextAlign.Center)
                    Text("PAID UPGRADE CHALLENGE", color = FrogDark, fontWeight = FontWeight.Black, fontSize = 11.sp)
                    Spacer(Modifier.height(10.dp))
                    Text("Puzzle ${step + 1} of 3", color = Color(0xFF9A6A00), fontWeight = FontWeight.Black, fontSize = 13.sp)
                    Spacer(Modifier.height(8.dp))
                    Surface(color = Cream, shape = RoundedCornerShape(18.dp)) {
                        Text(
                            "${puzzle.first} + ${puzzle.second} = ?",
                            modifier = Modifier.fillMaxWidth().padding(18.dp),
                            color = Ink,
                            fontWeight = FontWeight.Black,
                            fontSize = 22.sp,
                            textAlign = TextAlign.Center
                        )
                    }
                    Spacer(Modifier.height(10.dp))
                    puzzle.third.forEach { option ->
                        Button(
                            onClick = {
                                if (option == answer) {
                                    if (step >= 2) {
                                        onSolved()
                                    } else {
                                        step++
                                        feedback = "Correct! Next puzzle."
                                    }
                                } else {
                                    feedback = "Not quite. Try again — you do not pay twice."
                                }
                            },
                            modifier = Modifier.fillMaxWidth().height(48.dp).padding(vertical = 3.dp),
                            shape = RoundedCornerShape(15.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
                        ) {
                            Text(option.toString(), fontWeight = FontWeight.Black, fontSize = 15.sp)
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(feedback, color = WoodDark, fontWeight = FontWeight.Bold, fontSize = 10.sp, textAlign = TextAlign.Center)
                }
            }
        }
    }
}
'''

path.write_text(text)
print('normalized challenge titles and installed final UpgradeChallengeOverlayFixed compile repair')
