#!/usr/bin/env python3
from pathlib import Path
import shutil
import struct
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch_home_png_resource.py <project_dir>')

project_dir = Path(sys.argv[1])
repo_root = Path(__file__).resolve().parent
source = repo_root / 'generated_assets_v11' / 'ftf_home_screen_v2.png'
drawable = project_dir / 'app' / 'src' / 'main' / 'res' / 'drawable-nodpi'
drawable.mkdir(parents=True, exist_ok=True)
destination = drawable / 'ftf_home_screen_v2.png'
old_jpeg = drawable / 'ftf_home_screen_v2.jpg'

if not source.exists():
    raise SystemExit('safe homepage PNG is missing')

shutil.copy2(source, destination)
old_jpeg.unlink(missing_ok=True)

data = destination.read_bytes()
if len(data) < 33 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
    raise SystemExit('installed homepage is not a valid PNG container')
if data[12:16] != b'IHDR':
    raise SystemExit('installed homepage PNG has no IHDR')
width, height = struct.unpack('>II', data[16:24])
if (width, height) != (320, 569):
    raise SystemExit(f'installed homepage has wrong size: {width}x{height}')

ffmpeg = shutil.which('ffmpeg')
if not ffmpeg:
    raise SystemExit('ffmpeg unavailable for final homepage validation')
subprocess.run(
    [ffmpeg, '-v', 'error', '-i', str(destination), '-f', 'null', '-'],
    check=True,
)

# Distinguish this real runtime crash repair from the two v0.8.8 builds that
# contained the broken JPEG. All gameplay remains the same; only the homepage
# resource path/validation changes here.
app_gradle = project_dir / 'app' / 'build.gradle.kts'
gradle = app_gradle.read_text()
if 'versionCode = 17' not in gradle or 'versionName = "0.8.8-home-motion-timer-skip"' not in gradle:
    raise SystemExit('expected v0.8.8 values before PNG startup repair')
gradle = gradle.replace('versionCode = 17', 'versionCode = 18', 1)
gradle = gradle.replace(
    'versionName = "0.8.8-home-motion-timer-skip"',
    'versionName = "0.8.9-valid-home-png"',
    1,
)
app_gradle.write_text(gradle)

print(f'installed validated homepage PNG: {len(data)} bytes, {width}x{height}; bumped app to v0.8.9')
