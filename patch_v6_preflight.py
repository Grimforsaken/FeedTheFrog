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
path.write_text(text)

# Keep the generated patch script untouched unless it actually contains physical
# source line-continuations. This guard also makes the diagnosis visible in Actions.
repo_root = Path(__file__).resolve().parent
v6_path = repo_root / 'patch_gameplay_v6.py'
v6 = v6_path.read_text()
continuations = v6.count('\\\n')
if continuations:
    v6 = v6.replace('\\\n', '\\n')
    v6_path.write_text(v6)

# Print only the small challenge-title function so a mismatch can be corrected
# without dumping the full generated Kotlin file into the Actions log.
match = re.search(r'private fun challengeTitle\(kind: UpgradeKind\): String = when \(kind\) \{.*?^\}', text, re.S | re.M)
if match:
    print('--- challengeTitle before v6 ---')
    print(match.group(0))
    print('--- end challengeTitle ---')
else:
    print('challengeTitle function not found by preflight diagnostic')

print(f'normalized v0.8.4 preflight; repaired {continuations} v6 multiline literals')
