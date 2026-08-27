#!/usr/bin/env python3
from pathlib import Path
import base64
import hashlib
import shutil
import struct
import subprocess

root = Path(__file__).resolve().parent
src = root / "binary_assets_v11"
out = root / "generated_assets_v11"
out.mkdir(exist_ok=True)

# v0.8.8's JPEG was structurally malformed and crashed Android when decoded.
# Reconstruct the approved 320x569 source only if every chunk and the complete
# WebP match the locally validated source exactly.
parts = sorted(src.glob("home_safe_*.b64"))
expected_sizes = [10500, 10500, 10500, 6550]
expected_sha256 = "35e88e34e2d0a31aa4bf40db1378ae9f12f2d65211f2371ff71a5cac1893a1c2"
if len(parts) != 4:
    raise SystemExit(f"expected 4 safe homepage chunks, found {len(parts)}")

decoded_parts = []
for index, (part, expected_size) in enumerate(zip(parts, expected_sizes), start=1):
    text = part.read_text().strip()
    if len(text) % 4:
        raise SystemExit(f"{part.name} base64 length {len(text)} is not divisible by 4")
    try:
        decoded = base64.b64decode(text, validate=True)
    except Exception as exc:
        raise SystemExit(f"safe homepage base64 decode failed in {part.name}: {exc}")
    if len(decoded) != expected_size:
        raise SystemExit(
            f"{part.name} decoded to {len(decoded)} bytes, expected {expected_size}"
        )
    decoded_parts.append(decoded)
    print(f"validated homepage chunk {index}: {len(text)} base64 chars -> {len(decoded)} bytes")

webp = b"".join(decoded_parts)
if len(webp) != 38050:
    raise SystemExit(f"safe homepage WebP should be 38050 bytes, got {len(webp)}")
if webp[:4] != b"RIFF" or webp[8:12] != b"WEBP":
    raise SystemExit("safe homepage source is not a complete WebP")
declared_size = struct.unpack("<I", webp[4:8])[0] + 8
if declared_size != len(webp):
    raise SystemExit(
        f"safe homepage WebP size mismatch: RIFF declares {declared_size}, got {len(webp)}"
    )
actual_sha256 = hashlib.sha256(webp).hexdigest()
if actual_sha256 != expected_sha256:
    raise SystemExit(
        f"safe homepage SHA-256 mismatch: {actual_sha256}; expected {expected_sha256}"
    )

ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    raise SystemExit("ffmpeg is required before prepare_v11_assets.py")

source = out / "ftf_home_screen_v2_source.webp"
destination = out / "ftf_home_screen_v2.png"
compat_jpeg = out / "ftf_home_screen_v2.jpg"
source.write_bytes(webp)
destination.unlink(missing_ok=True)
compat_jpeg.unlink(missing_ok=True)

# Force a real image decode into PNG. The JPEG is only a temporary compatibility
# input for the older v0.8.8 patch and is deleted before Android packaging.
subprocess.run(
    [ffmpeg, "-y", "-v", "error", "-i", str(source), "-frames:v", "1", "-pix_fmt", "rgb24", str(destination)],
    check=True,
)
subprocess.run(
    [ffmpeg, "-y", "-v", "error", "-i", str(source), "-frames:v", "1", "-q:v", "2", str(compat_jpeg)],
    check=True,
)

data = destination.read_bytes()
if len(data) < 33 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("decoded homepage is not a PNG")
if data[12:16] != b"IHDR":
    raise SystemExit("decoded homepage PNG has no IHDR")
width, height = struct.unpack(">II", data[16:24])
if (width, height) != (320, 569):
    raise SystemExit(f"unexpected safe homepage dimensions: {width}x{height}")

# Independent full decodes catch corruption that header/magic-byte checks miss.
for generated in (destination, compat_jpeg):
    subprocess.run([ffmpeg, "-v", "error", "-i", str(generated), "-f", "null", "-"], check=True)

source.unlink(missing_ok=True)
print(
    f"{destination.name}: {len(data)} bytes, {width}x{height}; "
    f"source SHA-256 {actual_sha256} verified"
)
