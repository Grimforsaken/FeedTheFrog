#!/usr/bin/env python3
from pathlib import Path
import base64
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_ui_art_costs.py <MainActivity.kt> <project_dir>")

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])
repo_root = Path(__file__).resolve().parent
text = main_file.read_text()

def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"ui/cost patch failed: {label}")
    text = text.replace(old, new, 1)

# Drastically steeper long-term economy.
replace_once("private const val SECOND_DIE_COST = 10_000", "private const val SECOND_DIE_COST = 12_000_000", "second die cost")
replace_once("private val DIE_UPGRADE_COSTS = intArrayOf(200, 500, 1_200, 3_000, 7_500)", "private val DIE_UPGRADE_COSTS = intArrayOf(5_000, 25_000, 125_000, 625_000, 3_000_000)", "die costs")
replace_once("private val RANGE_COSTS = intArrayOf(150, 350, 750, 1_500, 3_000, 6_000)", "private val RANGE_COSTS = intArrayOf(2_500, 10_000, 40_000, 150_000, 600_000, 2_500_000)", "range costs")
replace_once("private val CAPACITY_COSTS = intArrayOf(250, 600, 1_400, 3_000, 6_500, 13_000, 26_000)", "private val CAPACITY_COSTS = intArrayOf(7_500, 35_000, 175_000, 850_000, 4_000_000, 18_000_000, 75_000_000)", "capacity costs")

# Stronger illustrated palette.
for old, new in {
    "private val PondDark = Color(0xFF0B5960)": "private val PondDark = Color(0xFF063F45)",
    "private val PondLight = Color(0xFF48B9B4)": "private val PondLight = Color(0xFF2C9FA5)",
    "private val PondSky = Color(0xFF9DE4E0)": "private val PondSky = Color(0xFF8BDBD5)",
    "private val FrogGreen = Color(0xFF86C91D)": "private val FrogGreen = Color(0xFF72C900)",
    "private val FrogLight = Color(0xFFB6DF41)": "private val FrogLight = Color(0xFFA8E52B)",
    "private val FrogDark = Color(0xFF3A731B)": "private val FrogDark = Color(0xFF2E6515)",
    "private val Wood = Color(0xFF7A4A22)": "private val Wood = Color(0xFF6B3F1D)",
    "private val WoodDark = Color(0xFF4E2E17)": "private val WoodDark = Color(0xFF3D2412)",
    "private val Gold = Color(0xFFFFC94D)": "private val Gold = Color(0xFFFFC400)",
}.items():
    replace_once(old, new, old)

replace_once("import androidx.compose.foundation.Canvas", "import androidx.compose.foundation.Canvas\nimport androidx.compose.foundation.Image", "Image import")
replace_once("import androidx.compose.ui.platform.LocalDensity", "import androidx.compose.ui.platform.LocalDensity\nimport androidx.compose.ui.res.painterResource", "painterResource import")

old_play = '''                    Button(
                        onClick = onPlay,
                        modifier = Modifier.height(54.dp).weight(0.68f),
                        shape = RoundedCornerShape(18.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
                    ) {
                        Text("PLAY", fontSize = 20.sp, fontWeight = FontWeight.Black)
                    }'''
new_play = '''                    Button(
                        onClick = onPlay,
                        modifier = Modifier.height(92.dp).weight(0.68f),
                        shape = RoundedCornerShape(22.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent)
                    ) {
                        Image(
                            painter = painterResource(R.drawable.ftf_play),
                            contentDescription = "Play",
                            modifier = Modifier.fillMaxSize()
                        )
                    }'''
replace_once(old_play, new_play, "play button art")

old_upgrade = '''            Button(
                onClick = onShop,
                modifier = Modifier.height(42.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = FrogDark)
            ) {
                Text("UPGRADES", fontWeight = FontWeight.Black, fontSize = 11.sp)
            }'''
new_upgrade = '''            Button(
                onClick = onShop,
                modifier = Modifier.height(54.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent)
            ) {
                Image(
                    painter = painterResource(R.drawable.ftf_upgrades),
                    contentDescription = "Upgrades",
                    modifier = Modifier.width(94.dp).height(46.dp)
                )
            }'''
replace_once(old_upgrade, new_upgrade, "upgrade button art")

replace_once('Text("FROG SHOP", fontWeight = FontWeight.Black, color = Color.White, fontSize = 21.sp)', 'Text("FROG SHOP", fontWeight = FontWeight.Black, color = Gold, fontSize = 24.sp)', "shop title")

drawable_dir = project_dir / "app" / "src" / "main" / "res" / "drawable-nodpi"
drawable_dir.mkdir(parents=True, exist_ok=True)
for stem in ("play", "upgrades"):
    src = repo_root / "ui_assets" / f"ftf_{stem}.b64"
    if not src.exists():
        raise SystemExit(f"missing encoded UI asset: {src}")
    raw = base64.b64decode(src.read_text().strip())
    (drawable_dir / f"ftf_{stem}.webp").write_bytes(raw)

main_file.write_text(text)
print("updated FeedTheFrog art and drastically increased upgrade costs")
