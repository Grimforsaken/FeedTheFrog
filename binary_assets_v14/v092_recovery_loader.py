from pathlib import Path
import base64
import sys
import zlib
import zipfile

ORIGINAL = Path("binary_assets_v14/patch_v092_full_update.original-corrupt.zlib.b64")
payload = base64.b64decode("".join(ORIGINAL.read_text().split()))
try:
    recovered = zlib.decompress(payload)
except zlib.error:
    recovered = zlib.decompress(payload[2:-4], -zlib.MAX_WBITS)

bad = b"\xb8\xe2\x8c\xa7\xef\xb8\x8f"
good = "🌧️".encode("utf-8")
if recovered.count(bad) != 1:
    raise SystemExit(f"Expected exactly one damaged Firefly icon sequence, found {recovered.count(bad)}")
recovered = recovered.replace(bad, good, 1)
text = recovered.decode("utf-8")
compile(text, "/tmp/patch_v092_full_update.recovered.py", "exec")

asset_zip = Path("/tmp/v092-assets.zip")
if not asset_zip.is_file():
    raise SystemExit("Missing verified /tmp/v092-assets.zip")
with zipfile.ZipFile(asset_zip, "r") as zf:
    bad_entry = zf.testzip()
    if bad_entry:
        raise SystemExit(f"Bad asset ZIP entry: {bad_entry}")
Path("/tmp/v092_assets.zip.b64").write_text(
    base64.b64encode(asset_zip.read_bytes()).decode("ascii"), encoding="ascii"
)

if len(sys.argv) < 3:
    raise SystemExit("usage: patch_v092_full_update.py <MainActivity.kt> <project_dir>")
sys.argv = sys.argv[:3]
exec(compile(text, "/tmp/patch_v092_full_update.recovered.py", "exec"), globals(), globals())

main_file = Path(sys.argv[1])
project_dir = Path(sys.argv[2])

# Compile repair: v0.9.2 adds three enum values with dedicated WebP rendering,
# but the older Canvas fallback drawBug() must still be exhaustive. Keep explicit
# species branches so future BugType additions continue to fail loudly.
main_text = main_file.read_text(encoding="utf-8")
anchor = "        BugType.COMMON_FLY -> drawStandardFly(center, 1.0f * boostScale, bodyColor = Color(0xFF48504B), headColor = Color(0xFF202520), wingColor = Color.White.copy(alpha = 0.82f))\n"
if main_text.count(anchor) != 1:
    raise SystemExit(f"Expected one drawBug COMMON_FLY anchor, found {main_text.count(anchor)}")
new_branches = (
    "        BugType.LADYBUG -> drawStandardFly(center, 0.9f * boostScale, bodyColor = Color(0xFFD83A35), headColor = Color(0xFF1C1C1C), wingColor = Color.White.copy(alpha = 0.82f))\n"
    "        BugType.JUNE_BUG -> drawStandardFly(center, 1.12f * boostScale, bodyColor = Color(0xFF556B3D), headColor = Color(0xFF303A28), wingColor = Color.White.copy(alpha = 0.72f))\n"
    "        BugType.LIGHTNING_BUG -> drawStandardFly(center, 1.0f * boostScale, bodyColor = Color(0xFF292A24), headColor = Color(0xFF171812), wingColor = Color(0xFFFFE66A).copy(alpha = 0.88f))\n"
)
main_text = main_text.replace(anchor, anchor + new_branches, 1)
main_file.write_text(main_text, encoding="utf-8")
print("repaired drawBug fallbacks for LADYBUG, JUNE_BUG, and LIGHTNING_BUG")

app_gradle = project_dir / "app/build.gradle.kts"
commercial_file = project_dir / "app/src/main/java/com/feedthefrog/game/CommercialSystem.kt"
billing_file = project_dir / "app/src/main/java/com/feedthefrog/game/BillingSystem.kt"
gradle_text = app_gradle.read_text(encoding="utf-8")
commercial_text = commercial_file.read_text(encoding="utf-8")
billing_text = billing_file.read_text(encoding="utf-8")
combined_commercial = main_text + "\n" + commercial_text

checks = [
    ("versionCode = 21", "versionCode = 21" in gradle_text),
    ('versionName = "0.9.2-bugs-tv-lightning"', 'versionName = "0.9.2-bugs-tv-lightning"' in gradle_text),
    ("LIGHTNING_BUG", "LIGHTNING_BUG" in main_text),
    ("LADYBUG", "LADYBUG" in main_text),
    ("JUNE_BUG", "JUNE_BUG" in main_text),
    ("lightningImmune", "lightningImmune" in main_text),
    ("luckyCloverActive", "luckyCloverActive" in main_text),
    ("armorHits", "armorHits" in main_text),
    ("selectedTvContentMask", "selectedTvContentMask" in main_text),
    ("Checkbox", "Checkbox" in main_text),
    ("ad_frog_cola wiring", "ad_frog_cola" in combined_commercial),
    ("ad_bug_burgers wiring", "ad_bug_burgers" in combined_commercial),
    ("ad_lily_pad_insurance wiring", "ad_lily_pad_insurance" in combined_commercial),
    ("class FakeBillingProvider", "class FakeBillingProvider" in billing_text),
    ("TIMER_SKIP_COST = 1", "TIMER_SKIP_COST = 1" in main_text),
    ("BEE_IMMUNITY_COST = 1", "BEE_IMMUNITY_COST = 1" in main_text),
    ("FIREFLY_IMMUNITY_COST = 1", "FIREFLY_IMMUNITY_COST = 1" in main_text),
    ("POISON_DAMAGE_PER_SECOND = 3", "POISON_DAMAGE_PER_SECOND = 3" in main_text),
    ("keepFlyOutsideProtectedControls", "keepFlyOutsideProtectedControls" in main_text),
    ("Test advertiser link", "Test advertiser link — no real website opened." in main_text),
    ("explicit LADYBUG draw fallback", "BugType.LADYBUG -> drawStandardFly" in main_text),
    ("explicit JUNE_BUG draw fallback", "BugType.JUNE_BUG -> drawStandardFly" in main_text),
    ("explicit LIGHTNING_BUG draw fallback", "BugType.LIGHTNING_BUG -> drawStandardFly" in main_text),
]
print("v0.9.2 post-patch marker diagnostics:")
for label, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'} {label}")
    if not ok:
        raise SystemExit(f"Missing required v0.9.2 marker: {label}")

draw = project_dir / "app/src/main/res/drawable-nodpi"
raw = project_dir / "app/src/main/res/raw"
for name in [
    "ladybug_lucky_clover_asset", "armored_june_bug_asset", "lightning_bug_asset",
    "lightning_rod_asset", "frog_shocked_asset", "ad_frog_cola",
    "ad_bug_burgers", "ad_lily_pad_insurance",
]:
    p = draw / f"{name}.webp"
    if not p.is_file() or not p.stat().st_size:
        raise SystemExit(f"Missing v0.9.2 asset: {p}")
video = raw / "ad_pond_cleanup.mp4"
if not video.is_file() or not video.stat().st_size:
    raise SystemExit("Missing v0.9.2 ad_pond_cleanup.mp4")
