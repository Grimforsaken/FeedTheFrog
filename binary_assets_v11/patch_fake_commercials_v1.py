#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import urllib.request

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_fake_commercials_v1.py <MainActivity.kt> <project_dir>')

# The full implementation is pinned to the original reviewed fake-commercial
# patch commit. Adapt only its fly-spawn anchor to the current v0.8.9 gameplay
# layout, then execute it locally. This avoids touching any other gameplay code.
SOURCE_URL = (
    'https://raw.githubusercontent.com/Grimforsaken/FeedTheFrog/'
    '5077a399407b77b2d739ef273e1d5869b7ebc4b9/'
    'binary_assets_v11/patch_fake_commercials_v1.py'
)
try:
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
        source = response.read().decode('utf-8')
except Exception as exc:
    raise SystemExit(f'could not load pinned fake-commercial implementation: {exc}')

current_spawn = '''                val screenLeft = boardSize.width * 0.10f
                val screenRight = boardSize.width * 0.75f
                val screenTop = boardSize.height * 0.24f
                val screenBottom = boardSize.height * 0.54f
                val centerX = (screenLeft + screenRight) * 0.5f
                val centerY = (screenTop + screenBottom) * 0.5f
                val x = centerX + (Random.nextFloat() - 0.5f) * boardSize.width * 0.10f
                val y = centerY + (Random.nextFloat() - 0.5f) * boardSize.height * 0.06f
                onFlyMoved(
                    fly.id,
                    Offset(
                        x.coerceIn(screenLeft, screenRight),
                        y.coerceIn(screenTop, screenBottom)
                    )
                )'''

protected_spawn = '''                val screenLeft = boardSize.width * 0.10f
                val screenRight = boardSize.width * 0.75f
                val screenTop = boardSize.height * 0.24f
                val screenBottom = boardSize.height * 0.54f
                val centerX = (screenLeft + screenRight) * 0.5f
                val centerY = (screenTop + screenBottom) * 0.5f
                val x = centerX + (Random.nextFloat() - 0.5f) * boardSize.width * 0.10f
                val y = centerY + (Random.nextFloat() - 0.5f) * boardSize.height * 0.06f
                onFlyMoved(
                    fly.id,
                    keepFlyOutsideProtectedControls(
                        Offset(
                            x.coerceIn(screenLeft, screenRight),
                            y.coerceIn(screenTop, screenBottom)
                        ),
                        boardSize
                    )
                )'''

pattern = re.compile(
    r"spawn_old = '''.*?'''\nspawn_new = '''.*?'''\nreplace_once\(spawn_old, spawn_new, 'protected fly spawn'\)",
    re.S,
)
replacement = (
    "spawn_old = '''" + current_spawn + "'''\n"
    "spawn_new = '''" + protected_spawn + "'''\n"
    "replace_once(spawn_old, spawn_new, 'protected fly spawn')"
)
source, count = pattern.subn(lambda _: replacement, source, count=1)
if count != 1:
    raise SystemExit(f'could not adapt protected fly spawn anchor; matches={count}')

namespace = {
    '__name__': '__main__',
    '__file__': str(Path(__file__)),
    '__package__': None,
}
exec(compile(source, str(Path(__file__)), 'exec'), namespace, namespace)

# Extend the validated fake-commercial build with the development-only billing
# abstraction. Keeping this separate makes it removable/replacable later.
billing_patch = Path(__file__).with_name('patch_fake_billing_v1.py')
if not billing_patch.exists():
    raise SystemExit(f'missing mock billing patch: {billing_patch}')
billing_source = billing_patch.read_text()
billing_namespace = {
    '__name__': '__main__',
    '__file__': str(billing_patch),
    '__package__': None,
}
exec(compile(billing_source, str(billing_patch), 'exec'), billing_namespace, billing_namespace)
