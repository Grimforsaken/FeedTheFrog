#!/usr/bin/env python3
from pathlib import Path
import base64, io, zipfile

root = Path(__file__).resolve().parent
parts = sorted((root / 'binary_assets').glob('ftf_bundle_part_*.b64'))
if not parts:
    raise SystemExit('No v0.8.4 binary asset bundle parts found')
raw = base64.b64decode(''.join(p.read_text().strip() for p in parts))
with zipfile.ZipFile(io.BytesIO(raw), 'r') as bundle:
    ui = root / 'ui_assets'; tv = root / 'tv_assets'
    ui.mkdir(exist_ok=True); tv.mkdir(exist_ok=True)
    (ui / 'v6_assets.zip').write_bytes(bundle.read('v6_assets.zip'))
    (tv / 'subscription_2.mp4').write_bytes(bundle.read('subscription_2.mp4'))
    (tv / 'subscription_3.mp4').write_bytes(bundle.read('subscription_3.mp4'))
print('reconstructed v0.8.4 bug art and subscription videos 2/3')
