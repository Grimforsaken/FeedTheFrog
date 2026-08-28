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
# abstraction. Keeping this separate makes it removable/replaceable later.
billing_patch = Path(__file__).with_name('patch_fake_billing_v1.py')
if not billing_patch.exists():
    raise SystemExit(f'missing mock billing patch: {billing_patch}')
billing_source = billing_patch.read_text()

# Kotlin string templates require a literal dollar sign to be escaped. The
# development price must render as $0.00, while remaining compiler-safe.
billing_source = billing_source.replace('$0.00', r'\$0.00')

# This project does not generate BuildConfig, so gate all developer-only billing
# controls using the actual Android application debuggable flag instead. Debug
# APKs expose the controls; non-debuggable release APKs do not.
billing_source = billing_source.replace(
    'BuildConfig.DEBUG',
    '((LocalContext.current.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0)'
)

# Current Header layout no longer contains the old source-level "COINS" label
# that the first billing pass used as an insertion anchor. Insert the + COINS
# control into the first Row/Column body instead, which keeps the coin shop in
# the existing header without depending on the exact label implementation.
old_header_start = "if 'contentDescription = \"Open development coin shop\"' not in header:"
old_header_end = "    header = '\\n'.join(lines)"
header_start = billing_source.find(old_header_start)
header_end = billing_source.find(old_header_end, header_start)
if header_start < 0 or header_end < 0:
    raise SystemExit('could not locate mock billing Header insertion block')
header_end += len(old_header_end)
new_header_block = r'''if 'Text("+ COINS"' not in header:
    lines = header.splitlines()
    layout_line = next((i for i, line in enumerate(lines) if 'Row(' in line), None)
    if layout_line is None:
        layout_line = next((i for i, line in enumerate(lines) if 'Column(' in line), None)
    if layout_line is None:
        raise SystemExit('fake-billing patch failed: Header layout anchor')

    brace_line = None
    for i in range(layout_line, min(len(lines), layout_line + 24)):
        if '{' in lines[i]:
            brace_line = i
            break
    if brace_line is None:
        raise SystemExit('fake-billing patch failed: Header layout body')

    indent = re.match(r'\s*', lines[brace_line]).group(0) + '    '
    coin_button = [
        indent + 'Button(',
        indent + '    onClick = onCoinShop,',
        indent + '    modifier = Modifier.height(28.dp),',
        indent + '    shape = RoundedCornerShape(9.dp),',
        indent + '    colors = ButtonDefaults.buttonColors(containerColor = FrogDark)',
        indent + ') {',
        indent + '    Text("+ COINS", color = Color.White, fontWeight = FontWeight.Black, fontSize = 10.sp)',
        indent + '}',
    ]
    lines[brace_line + 1:brace_line + 1] = coin_button
    header = '\n'.join(lines)'''
billing_source = billing_source[:header_start] + new_header_block + billing_source[header_end:]

billing_namespace = {
    '__name__': '__main__',
    '__file__': str(billing_patch),
    '__package__': None,
}
exec(compile(billing_source, str(billing_patch), 'exec'), billing_namespace, billing_namespace)
