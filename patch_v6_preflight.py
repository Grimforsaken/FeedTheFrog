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

# Some multiline string literals in patch_gameplay_v6.py were accidentally written
# using Python source line-continuations (backslash + physical newline). That removes
# the intended newline from the search/replacement strings and makes valid Kotlin
# blocks impossible to match. Convert those continuations to an explicit \n escape
# before executing the patch. The v6 script uses parenthesized expressions rather
# than intentional Python line-continuations, so this is safe for this generated file.
repo_root = Path(__file__).resolve().parent
v6_path = repo_root / 'patch_gameplay_v6.py'
v6 = v6_path.read_text()
continuations = v6.count('\\\n')
if continuations:
    v6 = v6.replace('\\\n', '\\n')
    v6_path.write_text(v6)

print(f'normalized v0.8.4 preflight; repaired {continuations} v6 multiline literals')
