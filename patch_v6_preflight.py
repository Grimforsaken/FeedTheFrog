#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_v6_preflight.py <MainActivity.kt>')

path = Path(sys.argv[1])
text = path.read_text()

# Normalize the bug-guide invocation so the v6 patch can replace it reliably.
pattern = re.compile(r'(?m)^\s*BugGuideSection\([^\n)]*\)\s*$')
text, count = pattern.subn('                    BugGuideSection(totalCaught)', text, count=1)
if count != 1:
    raise SystemExit('v6 preflight failed: BugGuideSection call not found')

# Install the three new challenge titles before v6. This avoids a brittle exact
# source-text match in the generated v6 patch while preserving the same result.
old_titles = '''    UpgradeKind.POISON_IMMUNITY -> "Poison Immunity Trial"
    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"'''
new_titles = '''    UpgradeKind.POISON_IMMUNITY -> "Poison Immunity Trial"
    UpgradeKind.BEE_IMMUNITY -> "Bee Immunity Trial"
    UpgradeKind.FIREFLY_IMMUNITY -> "Rain Cloud Trial"
    UpgradeKind.BUG_UNLOCK -> "Random Bug Trial"
    UpgradeKind.COIN_MULTIPLIER -> "Coin Multiplier Trial"'''
if old_titles in text:
    text = text.replace(old_titles, new_titles, 1)
elif 'UpgradeKind.BEE_IMMUNITY -> "Bee Immunity Trial"' not in text:
    raise SystemExit('v6 preflight failed: challenge title source block not found')

# v0.8.3's generated patch chain can leave the call to UpgradeChallengeOverlay
# while dropping its composable definition. Restore a self-contained three-puzzle
# trial before v6 runs. It works for every current and future UpgradeKind because
# the display title is derived from the enum name rather than an exhaustive when.
if 'private fun UpgradeChallengeOverlay(' not in text:
    text += r'''

@Composable
private fun UpgradeChallengeOverlay(kind: UpgradeKind, attempt: Int, onSolved: () -> Unit) {
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
    val left = puzzle.first
    val right = puzzle.second
    val answer = left + right
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
                            "$left + $right = ?",
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

# v6 will no longer find its old title needle because that change is already done.
# Skip ONLY that labelled replacement; every other v6 replacement remains strict.
repo_root = Path(__file__).resolve().parent
v6_path = repo_root / 'patch_gameplay_v6.py'
v6 = v6_path.read_text()
needle = "    if old not in text:\n        raise SystemExit(f'v6 patch failed: {label}')"
replacement = "    if old not in text:\n        if label == 'challenge title cases':\n            return\n        raise SystemExit(f'v6 patch failed: {label}')"
if needle not in v6:
    raise SystemExit('v6 preflight failed: replace_once guard not found')
v6_path.write_text(v6.replace(needle, replacement, 1))

print('normalized v0.8.4 bug guide/challenge titles and restored UpgradeChallengeOverlay')
