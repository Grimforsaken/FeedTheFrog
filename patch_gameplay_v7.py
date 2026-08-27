#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_gameplay_v7.py <MainActivity.kt> <project_dir>')

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f'v7 patch failed: {label}')
    text = text.replace(old, new, 1)


def regex_once(pattern: str, replacement: str, label: str, flags=0) -> None:
    global text
    text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'v7 patch failed: {label} (matches={count})')

# ---------------------------------------------------------------------------
# Replace the three v0.8.5 visual assets after every older patch has run.
# This deliberately overwrites the malformed v0.8.4 poison-frog WebP, which
# crashed Compose when poison immunity switched painterResource to it.
# ---------------------------------------------------------------------------
generated = repo_root / 'generated_assets_v9'
drawable = project_dir / 'app' / 'src' / 'main' / 'res' / 'drawable-nodpi'
drawable.mkdir(parents=True, exist_ok=True)

asset_map = {
    'frog_helmet_mask.webp': 'frog_helmet.webp',
    'ftf_home_frog.webp': 'ftf_home_frog.webp',
    'ftf_poison_frog_fixed.webp': 'ftf_poison_frog.webp',
}
for src_name, dst_name in asset_map.items():
    src = generated / src_name
    if not src.exists():
        raise SystemExit(f'v7 patch failed: missing generated asset {src_name}')
    data = src.read_bytes()
    if len(data) < 16 or data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        raise SystemExit(f'v7 patch failed: invalid WebP {src_name}')
    shutil.copy2(src, drawable / dst_name)

# ---------------------------------------------------------------------------
# Remove Auto-Eat from the game. Keep its old enum/callback scaffolding hidden
# so older patch scripts remain compatible, but saved installs can never turn
# the feature back on and the shop no longer offers it.
# ---------------------------------------------------------------------------
regex_once(
    r'var autoEatUnlocked by remember \{ mutableStateOf\(prefs\.getBoolean\("autoEatUnlocked", false\)\) \}',
    'var autoEatUnlocked by remember { mutableStateOf(false) }',
    'force Auto-Eat off',
)
text = text.replace('autoEatEnabled = autoEatUnlocked,', 'autoEatEnabled = false,')
text = text.replace('UpgradeKind.AUTO_EAT -> autoEatUnlocked = true', 'UpgradeKind.AUTO_EAT -> autoEatUnlocked = false')

auto_card_pattern = re.compile(
    r'\n\s*UpgradeRowCard\(\s*\n\s*icon = "🐸⚡",\s*\n\s*title = "Auto-Eat \(Mid Range\)",.*?\n\s*onClick = onBuyAutoEat\s*\n\s*\)\s*\n',
    re.S,
)
text, removed_cards = auto_card_pattern.subn('\n', text, count=1)
if removed_cards != 1:
    raise SystemExit(f'v7 patch failed: Auto-Eat shop card removal (matches={removed_cards})')

# ---------------------------------------------------------------------------
# New Bee Immunity mask. It remains a completely separate overlay so it works
# with both the green frog and the blue poison-immunity frog.
# ---------------------------------------------------------------------------
helmet_pattern = re.compile(
    r'\n\s*if \(beeImmune\) \{\s*\n\s*Image\(\s*\n\s*painter = painterResource\(R\.drawable\.frog_helmet\),.*?\n\s*\)\s*\n\s*\}',
    re.S,
)
helmet_replacement = '''
        if (beeImmune) {
            Image(
                painter = painterResource(R.drawable.frog_helmet),
                contentDescription = "Bee immunity face mask",
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .offset(y = maxHeight * 0.57f + frogBob - frogWidth * 0.22f)
                    .width(frogWidth * 0.84f)
            )
        }'''
text, helmet_matches = helmet_pattern.subn(helmet_replacement, text, count=1)
if helmet_matches != 1:
    raise SystemExit(f'v7 patch failed: bee helmet overlay replacement (matches={helmet_matches})')

# ---------------------------------------------------------------------------
# Replace the procedural frog on the HOME screen with the user's new glossy
# green frog. The gameplay frog stays unchanged unless poison immunity is on.
# ---------------------------------------------------------------------------
text = text.replace(
    '                drawFrog(Offset(size.width * 0.5f, size.height * 0.55f))\n',
    '                // Home frog is rendered as the supplied glossy sprite below.\n',
    1,
)

start_marker = '@Composable\nprivate fun StartScreen('
end_marker = '@Composable\nprivate fun ProgressChip'
start = text.find(start_marker)
end = text.find(end_marker, start + 1)
if start < 0 or end < 0:
    raise SystemExit('v7 patch failed: StartScreen bounds')
start_block = text[start:end]
column_needle = '''
            Column(
                modifier = Modifier
                    .fillMaxSize()'''
home_image = '''
            Image(
                painter = painterResource(R.drawable.ftf_home_frog),
                contentDescription = "Feed the Frog home frog",
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .align(Alignment.Center)
                    .fillMaxWidth(0.62f)
                    .offset(y = 24.dp)
            )

            Column(
                modifier = Modifier
                    .fillMaxSize()'''
if column_needle not in start_block:
    raise SystemExit('v7 patch failed: StartScreen main Column')
start_block = start_block.replace(column_needle, home_image, 1)
text = text[:start] + start_block + text[end:]

# ---------------------------------------------------------------------------
# Use that same green frog as the installed Android game/launcher logo.
# ---------------------------------------------------------------------------
manifest = project_dir / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
manifest_text = manifest.read_text()
manifest_text, icon_count = re.subn(
    r'android:icon="[^"]+"',
    'android:icon="@drawable/ftf_home_frog"',
    manifest_text,
    count=1,
)
if icon_count != 1:
    raise SystemExit(f'v7 patch failed: launcher icon replacement (matches={icon_count})')
if 'android:roundIcon=' in manifest_text:
    manifest_text = re.sub(
        r'android:roundIcon="[^"]+"',
        'android:roundIcon="@drawable/ftf_home_frog"',
        manifest_text,
        count=1,
    )
manifest.write_text(manifest_text)

main_file.write_text(text)
print('patched v0.8.5: new bee face mask, green home/logo frog, Auto-Eat removed, valid poison frog crash fix')
