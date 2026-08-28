#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_fake_commercials_v2.py <MainActivity.kt> <project_dir>')

# v1 contains the complete fake-commercial implementation. v2 updates only the
# fly-spawn anchor to match the current v0.8.9 gameplay code, then executes the
# same implementation. This keeps the existing center-of-TV spawn behavior while
# adding the protected top-left control exclusion.
core_path = Path(__file__).with_name('patch_fake_commercials_v1.py')
source = core_path.read_text()

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
    raise SystemExit('v2 adapter failed: could not replace v1 spawn anchor definition')

# Execute the adapted implementation with the original command-line arguments.
namespace = {
    '__name__': '__main__',
    '__file__': str(core_path),
    '__package__': None,
}
exec(compile(source, str(core_path), 'exec'), namespace, namespace)
