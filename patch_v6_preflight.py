#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_v6_preflight.py <MainActivity.kt>')

path = Path(sys.argv[1])
text = path.read_text()

pattern = re.compile(r'(?m)^\s*BugGuideSection\([^\n)]*\)\s*$')
text, count = pattern.subn('                    BugGuideSection(totalCaught)', text, count=1)
if count != 1:
    raise SystemExit('v6 preflight failed: BugGuideSection call not found')

path.write_text(text)
print('normalized BugGuideSection call for v0.8.4 patch')
