#!/usr/bin/env python3
from pathlib import Path
import base64
import shutil
import struct
import subprocess

root = Path(__file__).resolve().parent
src = root / "binary_assets_v11"
out = root / "generated_assets_v11"
out.mkdir(exist_ok=True)

# The previous v0.8.8 JPEG reconstruction was structurally malformed even
# though it had JPEG start/end markers. Android crashed as soon as it decoded
# that resource. Reconstruct the exact approved homepage from validated WebP
# chunks, then force a real ffmpeg decode into a conservative PNG resource.
parts = sorted(src.glob("home_safe_*.b64"))
if not parts:
    raise SystemExit("missing safe homepage chunks")

# Each chunk is an independently padded Base64 fragment. Decode each fragment
# first, then concatenate the resulting bytes. Concatenating the Base64 text
# itself produces "Excess data after padding" and is intentionally rejected.
decoded_parts = []
for part in parts:
    try:
        decoded_parts.append(base64.b64decode(part.read_text().strip(), validate=True))
    except Exception as exc:
        raise SystemExit(f"safe homepage base64 decode failed in {part.name}: {exc}")
webp = b"".join(decoded_parts)

if len(webp) < 32 or webp[:4] != b"RIFF" or webp[8:12] != b"WEBP":
    raise SystemExit("safe homepage source is not a complete WebP")

# Validate RIFF's declared container size before asking ffmpeg to decode it.
declared_size = struct.unpack("<I", webp[4:8])[0] + 8
if declared_size != len(webp):
    raise SystemExit(
        f"safe homepage WebP size mismatch: RIFF declares {declared_size}, got {len(webp)}"
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

# Decode, do not stream-copy: this proves the source pixels are readable and
# creates an Android-friendly PNG rather than reusing the broken JPEG stream.
subprocess.run(
    [
        ffmpeg,
        "-y",
        "-v", "error",
        "-i", str(source),
        "-frames:v", "1",
        "-pix_fmt", "rgb24",
        str(destination),
    ],
    check=True,
)

# patch_gameplay_v8.py predates this recovery and still checks for a .jpg.
# Give it a freshly decoded/re-encoded JPEG only as a temporary compatibility
# input. A later final-resource patch deletes the JPEG from Android resources
# and installs the validated PNG instead.
subprocess.run(
    [
        ffmpeg,
        "-y",
        "-v", "error",
        "-i", str(source),
        "-frames:v", "1",
        "-q:v", "2",
        str(compat_jpeg),
    ],
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

# Force independent full decodes of both generated files. Marker-only checks
# are intentionally insufficient after the malformed-JPEG incident.
for generated in (destination, compat_jpeg):
    subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(generated), "-f", "null", "-"],
        check=True,
    )

source.unlink(missing_ok=True)
print(
    f"{destination.name}: {len(data)} bytes, {width}x{height}, "
    f"fully decoded from {len(parts)} safe chunks ({len(webp)} WebP bytes)"
)
