#!/usr/bin/env python3
from pathlib import Path
import base64
import hashlib
import shutil
import struct
import subprocess

root = Path(__file__).resolve().parent
src = root / "binary_assets_v13"
out = root / "generated_assets_v11"
out.mkdir(exist_ok=True)

# The v0.8.8 JPEG was malformed and crashed Android when Compose decoded it.
# v0.8.9 reconstructs the user's approved homepage directly from a locally
# decoder-verified PNG. Each file is an independently encoded binary slice;
# decode each slice separately, concatenate the bytes, and verify the complete
# PNG against the exact SHA-256 of the validated local source.
parts = [src / f"home_png_{i:02d}.b64" for i in range(1, 6)]
expected_sizes = [6267, 6267, 6267, 6267, 6264]
expected_sha256 = "0126f640553280a64ed58a2f4f5ba0f49797cf22b3eac3b7402916b56ba497f6"

for p in parts:
    if not p.exists():
        raise SystemExit(f"missing homepage PNG chunk: {p.name}")

decoded_parts = []
for index, (part, expected_size) in enumerate(zip(parts, expected_sizes), start=1):
    text = part.read_text().strip()
    if len(text) % 4:
        raise SystemExit(f"{part.name} base64 length {len(text)} is not divisible by 4")
    try:
        decoded = base64.b64decode(text, validate=True)
    except Exception as exc:
        raise SystemExit(f"homepage PNG base64 decode failed in {part.name}: {exc}")
    if len(decoded) != expected_size:
        raise SystemExit(f"{part.name} decoded to {len(decoded)} bytes, expected {expected_size}")
    decoded_parts.append(decoded)
    print(f"validated homepage chunk {index}: {len(text)} chars -> {len(decoded)} bytes")

png = b"".join(decoded_parts)
actual_sha256 = hashlib.sha256(png).hexdigest()
if actual_sha256 != expected_sha256:
    raise SystemExit(f"homepage PNG SHA-256 mismatch: {actual_sha256}; expected {expected_sha256}")
if len(png) < 33 or not png.startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("homepage source is not a PNG")
if png[12:16] != b"IHDR":
    raise SystemExit("homepage PNG has no IHDR")
width, height = struct.unpack(">II", png[16:24])
if (width, height) != (320, 569):
    raise SystemExit(f"unexpected homepage dimensions: {width}x{height}")

destination = out / "ftf_home_screen_v2.png"
compat_jpeg = out / "ftf_home_screen_v2.jpg"
destination.write_bytes(png)
compat_jpeg.unlink(missing_ok=True)

ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    raise SystemExit("ffmpeg is required before prepare_v11_assets.py")

# Force a complete decoder pass over the PNG. This is the check the old JPEG
# pipeline was missing: magic bytes alone are not enough to prove an image can
# actually be decoded by Android.
subprocess.run([ffmpeg, "-v", "error", "-i", str(destination), "-f", "null", "-"], check=True)

# Temporary compatibility image for patch_gameplay_v8.py only. It is generated
# from the already validated PNG, then patch_home_png_resource.py removes it
# before Android packaging. The final APK contains only ftf_home_screen_v2.png.
subprocess.run(
    [ffmpeg, "-y", "-v", "error", "-i", str(destination), "-frames:v", "1", "-q:v", "2", str(compat_jpeg)],
    check=True,
)
subprocess.run([ffmpeg, "-v", "error", "-i", str(compat_jpeg), "-f", "null", "-"], check=True)

print(
    f"{destination.name}: {len(png)} bytes, {width}x{height}; "
    f"SHA-256 {actual_sha256} verified and fully decoded"
)
