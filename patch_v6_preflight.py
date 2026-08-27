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

print('normalized v0.8.4 bug guide and challenge titles')
